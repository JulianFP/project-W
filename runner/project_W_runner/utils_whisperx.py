import gc
from io import StringIO
from typing import Callable

import numpy as np
import torch
import whisperx
from whisperx import alignment, asr, diarize, utils
from whisperx.vads import pyannote

from .logger import get_logger
from .models.base import (
    AlignmentProcessingSettings,
    JobModelEnum,
    JobSettingsBase,
    supported_alignment_languages,
)
from .models.settings import ModelPrefetchingEnum, WhisperSettings

logger = get_logger("project-W-runner")


def model_cleanup(model):
    gc.collect()
    torch.cuda.empty_cache()
    del model


def prefetch_models_as_configured(whisper_settings: WhisperSettings):
    """
    Should be called at runner startup before runner registers to backend
    """
    # prefetch diarization model (and check access to it)
    # do this first because this is most likely to fail (because of the required hf token), and the other downloads take a while
    if (
        whisper_settings.model_prefetching == ModelPrefetchingEnum.ALL
        or whisper_settings.model_prefetching == ModelPrefetchingEnum.WITHOUT_ALIGNMENT
    ):
        logger.info("Starting prefetching of diarization models now. Please wait...")
        diarize_model = diarize.DiarizationPipeline(
            device=whisper_settings.torch_device,
            use_auth_token=whisper_settings.hf_token.get_secret_value(),
        )
        model_cleanup(diarize_model)
        logger.info("All diarization models fetched successfully")
    else:
        logger.warning(
            "Skipping prefetching of diarization models, this might lead to failing jobs due to not being able to fetch these models and significantly higher job processing times!"
        )

    # prefetch all whisper models
    if whisper_settings.model_prefetching != ModelPrefetchingEnum.NONE:
        logger.info("Starting prefetching of whisper and vad models now. Please wait...")
        for model in JobModelEnum:
            logger.info(f"Loading whisper's '{model}' model now...")
            loaded_model = whisperx.load_model(
                model,
                whisper_settings.torch_device,
                download_root=str(whisper_settings.model_cache_dir),
                compute_type=whisper_settings.compute_type,
            )
            model_cleanup(loaded_model)
            logger.info(f"Loading of whisper's '{model}' model was successful")
        logger.info("All whisper and vad models fetched successfully")
    else:
        logger.warning(
            "Skipping prefetching of whisper and vad models, this might lead to failing jobs due to not being able to fetch these models and significantly higher job processing times!"
        )

    # prefetch all alignment models
    if whisper_settings.model_prefetching == ModelPrefetchingEnum.ALL:
        logger.info("Starting prefetching of alignment models now. Please wait...")
        for language in supported_alignment_languages:
            logger.info(f"Loading the alignment model for the language '{language}' now...")
            loaded_model = whisperx.load_align_model(
                language_code=language,
                device=whisper_settings.torch_device,
                model_dir=str(whisper_settings.model_cache_dir),
            )
            model_cleanup(loaded_model)
            logger.info(
                f"Loading of the alignment model for the language '{language}' was successful"
            )
        logger.info("All alignment models fetched successfully")
    else:
        logger.warning(
            "Skipping prefetching of alignment models, this might lead to failing jobs due to not being able to fetch these models and significantly higher job processing times!"
        )


class ProgressCallbackClass:
    current_step: int
    steps: int
    __progress_callback: Callable[[float], None]

    def __init__(self, steps: int, progress_callback: Callable[[float], None]) -> None:
        self.current_step = 1
        self.steps = steps
        self.__progress_callback = progress_callback
        self.progress_callback(0.0)

    def progress_callback(self, progress: float):
        # we assume that preparations and output writing take 1 percent of the total time,
        # and that transcription, alignment and diarization each take the same amount of time
        if self.current_step < 2:
            progress *= 0.01
        elif self.current_step == self.steps:
            progress = 99.0 + 0.01 * progress
        else:
            progress = (
                1.0
                + ((self.current_step - 2) * 98.0) / (self.steps - 2)
                + 0.98 / (self.steps - 2) * progress
            )
        logger.info(f"Progress: {progress}")
        self.__progress_callback(progress)

    def step_increment(self):
        self.progress_callback(100.0)
        self.current_step += 1


def transcribe(
    audio_file: str,
    job_settings: JobSettingsBase,
    whisper_settings: WhisperSettings,
    progress_callback: Callable[[float], None],
) -> dict[str, StringIO]:
    """
    Transcribe the given audio using the given model and language. Returns the dictionary of all the
    information returned by the Whisper invocation. The progress_callback is called periodically with
    the progress of the transcription, as a float between 0 and 1. If device is not None, it will be
    used as the device for the model.
    """

    # calculate amount of step for logging and progress reporting
    steps = 3  # preparation, transcription and output writing is always done
    if job_settings.alignment is not None:
        steps += 1
    if job_settings.diarization is not None:
        steps += 1

    pc = ProgressCallbackClass(steps, progress_callback)
    logger.info(f"Running job processing step {pc.current_step}/{steps}: Preparations...")

    # overwrite the print method inside the asr and alignment modules of whisperx which contain progress printing and detected language
    def intercept_stdout(out: str):
        if out.startswith("Progress: ") and out.endswith("%..."):
            progress = out.removeprefix("Progress: ").removesuffix("%...").strip()
            # we start with 10% of this step since we assume that model loading took up the first 10% of the time
            pc.progress_callback(10.0 + 0.9 * float(progress))
        elif out.startswith("Detected language: ") and out.endswith(" in first 30s of audio..."):
            detected_language = out.removeprefix("Detected language: ").split(" ")[0].strip()
            if job_settings.language is None and job_settings.alignment is not None:
                if detected_language is None:
                    raise Exception(
                        "Automatic language detection failed: alignment not possible without knowing the language of the transcription. Either select a language explicitly or disable alignment!"
                    )
                if detected_language not in supported_alignment_languages:
                    raise Exception(
                        f"The detected language '{detected_language}' is not supported for alignment. Either select a different language explicitly or disable alignment!"
                    )
            logger.info(f"WhisperX: {out}")

    setattr(asr, "print", intercept_stdout)
    setattr(alignment, "print", intercept_stdout)
    setattr(pyannote, "print", intercept_stdout)

    # overwrite the ResultWriter class in the utils module to be able to use StringIO instead of actual files for output
    in_memory_files = {}

    def new_result_writer_call(self, result: dict, audio_path: str, options: dict):
        self.in_memory_file = StringIO()
        in_memory_files[self.extension] = self.in_memory_file
        self.write_result(result, file=self.in_memory_file, options=options)

    utils.ResultWriter.__call__ = new_result_writer_call

    if (increment := job_settings.asr_settings.temperature_increment_on_fallback) is not None:
        temperatures = tuple(
            np.arange(job_settings.asr_settings.temperature, 1.0 + 1e-6, increment)
        )
    else:
        temperatures = [job_settings.asr_settings.temperature]
    vad_options = job_settings.vad_settings.model_dump()
    vad_options.pop("chunk_size")

    # transcription
    pc.step_increment()
    logger.info(f"Running job processing step {pc.current_step}/{steps}: Whisper Transcription...")
    whisperx_model = whisperx.load_model(
        job_settings.model,
        whisper_settings.torch_device,
        download_root=str(whisper_settings.model_cache_dir),
        compute_type=whisper_settings.compute_type,
        task=job_settings.task,
        language=job_settings.language,
        asr_options={
            "beam_size": job_settings.asr_settings.beam_size,
            "patience": job_settings.asr_settings.patience,
            "length_penalty": job_settings.asr_settings.length_penalty,
            "temperatures": temperatures,
            "compression_ratio_threshold": job_settings.asr_settings.compression_ratio_threshold,
            "log_prob_threshold": job_settings.asr_settings.log_prob_threshold,
            "no_speech_threshold": job_settings.asr_settings.no_speech_threshold,
            "condition_on_previous_text": False,
            "initial_prompt": job_settings.asr_settings.initial_prompt,
            "suppress_tokens": job_settings.asr_settings.suppress_tokens,
            "suppress_numerals": job_settings.asr_settings.suppress_numerals,
        },
        vad_options=vad_options,
    )
    pc.progress_callback(5.0)  # model loading complete
    audio = whisperx.load_audio(audio_file)
    pc.progress_callback(10.0)  # audio loading complete
    result = whisperx_model.transcribe(
        audio,
        batch_size=whisper_settings.batch_size,
        chunk_size=job_settings.vad_settings.chunk_size,
        print_progress=True,
    )
    model_cleanup(whisperx_model)
    # new_detect_language should already handle problems with language detection before transcription. This just ensures that the language is definitely not None
    used_language = job_settings.language or result.get("language") or "en"

    # alignment
    if job_settings.alignment is not None:
        pc.step_increment()
        logger.info(f"Running job processing step {pc.current_step}/{steps}: Alignment...")
        align_model, align_metadata = whisperx.load_align_model(
            language_code=used_language,
            device=whisper_settings.torch_device,
            model_dir=str(whisper_settings.model_cache_dir),
        )
        pc.progress_callback(10.0)  # model loading complete
        result = whisperx.align(
            result["segments"],
            align_model,
            align_metadata,
            audio,
            whisper_settings.torch_device,
            return_char_alignments=job_settings.alignment.return_char_alignments,
            interpolate_method=job_settings.alignment.interpolate_method,
            # alignment progress reporting in whisperx currently seems broken, it just immediately jumps to 100%
            # print_progress=True,
        )
        model_cleanup(align_model)

    # diarization
    if job_settings.diarization is not None:
        pc.step_increment()
        logger.info(f"Running job processing step {pc.current_step}/{steps}: Diarization...")
        diarize_model = diarize.DiarizationPipeline(
            device=whisper_settings.torch_device,
            use_auth_token=whisper_settings.hf_token.get_secret_value(),
        )
        pc.progress_callback(10.0)  # model loading complete
        diarize_segments = diarize_model(
            audio,
            min_speakers=job_settings.diarization.min_speakers,
            max_speakers=job_settings.diarization.max_speakers,
        )
        result = whisperx.assign_word_speakers(diarize_segments, result)
        model_cleanup(diarize_model)

    # output writing
    pc.step_increment()
    logger.info(f"Running job processing step {pc.current_step}/{steps}: Output writing...")
    result = dict(result)
    result["language"] = used_language
    writer = utils.get_writer("all", ".")
    # this function is actually supposed to take a str instead of a TextIO. The error is due to an incorrect type annotation in whisperx upstream, see https://github.com/m-bain/whisperX/pull/1144 for the pending fix
    options = (
        job_settings.alignment.processing.model_dump()
        if job_settings.alignment is not None
        else AlignmentProcessingSettings().model_dump()
    )
    writer(result, "file", options)

    # Just in case the progress_callback was not called with 100.0, do that now.
    pc.progress_callback(100.0)
    logger.info("Job processing finished")

    return in_memory_files
