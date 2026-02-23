from pydantic import BaseModel, SecretStr, Field, model_validator
from enum import Enum
from typing import Self

from .response_models import AlignmentProcessingSettings, AlignmentSettings, AsrSettings, DiarizationSettings, InterpolateMethodEnum, JobLangEnum, JobModelEnum, JobSettingsResponse, TaskEnum, VadSettings
from .base import EmailValidated, PasswordValidated


class JobSettingsRequest(JobSettingsResponse):
    #add default values
    email_notification: bool = False
    task: TaskEnum = TaskEnum.TRANSCRIBE
    model: JobModelEnum = JobModelEnum.LARGE
    language: JobLangEnum | None = None
    alignment: AlignmentSettings | None = AlignmentSettings(
        processing=AlignmentProcessingSettings(
            highlight_words=False,
            max_line_count=None,
            max_line_width=None,
        ),
        return_char_alignments=False,
        interpolate_method=InterpolateMethodEnum.NEAREST,
    )
    diarization: DiarizationSettings | None = None
    vad_settings: VadSettings = VadSettings(
        vad_onset=0.5,
        vad_offset=0.363,
        chunk_size=30,
    )
    asr_settings: AsrSettings = AsrSettings(
        beam_size=5,
        patience=1.0,
        length_penalty=1.0,
        temperature=0.0,
        temperature_increment_on_fallback=0.2,
        compression_ratio_threshold=2.4,
        log_prob_threshold=-1.0,
        no_speech_threshold=0.6,
        initial_prompt=None,
        suppress_tokens=[-1],
        suppress_numerals=False,
    )


class SignupRequest(BaseModel):
    email: EmailValidated
    password: PasswordValidated


class PasswordResetRequest(BaseModel):
    token: SecretStr
    new_password: PasswordValidated


class TranscriptTypeEnum(str, Enum):
    TXT = "as_txt"
    SRT = "as_srt"
    TSV = "as_tsv"
    VTT = "as_vtt"
    JSON = "as_json"

class Transcript(BaseModel):
    as_txt: str
    as_srt: str
    as_tsv: str
    as_vtt: str
    as_json: dict

class RunnerSubmitResultRequest(BaseModel):
    error_msg: str | None = None
    transcript: Transcript | None = None

    @model_validator(mode="after")
    def either_error_or_transcript(self) -> Self:
        if self.error_msg is None and self.transcript is None:
            raise ValueError(
                "Either `error_msg` or `transcript` must be set for job submission"
            )
        return self


class SiteBannerRequest(BaseModel):
    html: str
    urgency: int


class EmailToUsersRequest(BaseModel):
    subject: str
    body: str


class RunnerRegisterRequest(BaseModel):
    name: str = Field(max_length=40)
    version: str
    git_hash: str = Field(max_length=40)
    source_code_url: str
    priority: int = Field(gt=0)


class HeartbeatRequest(BaseModel):
    progress: float = Field(
        ge=0.0,
        le=100.0,
        default=0.0,
    )
