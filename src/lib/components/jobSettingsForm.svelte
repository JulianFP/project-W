<script lang="ts">
import { error } from "@sveltejs/kit";
import {
	Accordion,
	AccordionItem,
	Badge,
	Checkbox,
	Heading,
	Input,
	Label,
	Select,
	Textarea,
	Tooltip,
} from "flowbite-svelte";
import { QuestionCircleOutline, UndoOutline } from "flowbite-svelte-icons";

import { BackendCommError } from "$lib/utils/httpRequests.svelte";
import { getLoggedIn } from "$lib/utils/httpRequestsAuth.svelte";
import {
	type components,
	interpolateMethodEnumValues,
	jobLangEnumValues,
	jobModelEnumValues,
} from "$lib/utils/schema.d";
import RangeWithField from "./rangeWithField.svelte";
import WaitingSubmitButton from "./waitingSubmitButton.svelte";

type JobSettingsResp = components["schemas"]["JobSettings-Output"];
interface Props {
	get_job_settings?: () => object;
	re_query?: () => Promise<void>;
	pre_filled_in_settings?: JobSettingsResp;
}

let {
	get_job_settings = $bindable(),
	re_query = $bindable(),
	pre_filled_in_settings,
}: Props = $props();

get_job_settings = () => {
	return job_settings;
};

re_query = async () => {
	await setToDefault(true);
};
let default_settings: JobSettingsResp | undefined = $state();
let wait_for_set: boolean = $state(false);

let translate: boolean = $state(false);
let language: components["schemas"]["JobLangEnum"] | "detect" =
	$state("detect");
let model: components["schemas"]["JobModelEnum"] = $state("large");
let email_notification: boolean = $state(false);
let alignment: boolean = $state(true);
let alignment_processing_highlight_words: boolean = $state(false);
let alignment_processing_max_line_width: number | undefined = $state();
let alignment_processing_max_line_count: number | undefined = $state();
let alignment_return_char_alignments: boolean = $state(false);
let alignment_interpolate_method: components["schemas"]["InterpolateMethodEnum"] =
	$state("nearest");
let diarization: boolean = $state(false);
let diarization_min_speakers: number | undefined = $state();
let diarization_max_speakers: number | undefined = $state();
let vad_onset: number = $state(0.5);
let vad_offset: number = $state(0.363);
let vad_chunk_size: number = $state(30);
let asr_beam_size: number = $state(5);
let asr_patience: number = $state(1);
let asr_length_penalty: number = $state(1);
let asr_temperature: number = $state(0);
let asr_temperature_increment_on_fallback: number = $state(0.2);
let asr_compression_ratio_threshold: number = $state(2.4);
let asr_log_prob_threshold: number = $state(-1);
let asr_no_speech_threshold: number = $state(0.6);
let asr_initial_prompt: string = $state("");
let asr_suppressed_tokens: string = $state("-1");
let asr_suppress_numerals: boolean = $state(false);

//query default settings of account
async function queryDefaultValues(): Promise<
	components["schemas"]["JobSettings-Output"]
> {
	try {
		return await getLoggedIn<components["schemas"]["JobSettings-Output"]>(
			"jobs/default_settings",
		);
	} catch (err: unknown) {
		let errorMsg = "Error occured while fetching default account settings: ";
		let errorCode = 400;
		if (err instanceof BackendCommError) {
			errorMsg += err.message;
			errorCode = err.status;
		} else {
			errorMsg += "Unknown error";
		}
		error(errorCode, errorMsg);
	}
}

function setStateFromJobSettingsResp(job_settings: JobSettingsResp) {
	wait_for_set = true;
	language =
		job_settings.language === null || job_settings.language === undefined
			? "detect"
			: job_settings.language;
	translate = job_settings.task === "translate";
	model = job_settings.model;
	email_notification = job_settings.email_notification;
	alignment =
		job_settings.alignment !== undefined && job_settings.alignment !== null;
	if (job_settings.alignment) {
		alignment_processing_highlight_words =
			job_settings.alignment.processing.highlight_words;
		alignment_processing_max_line_width =
			job_settings.alignment.processing.max_line_width === null
				? undefined
				: job_settings.alignment.processing.max_line_width;
		alignment_processing_max_line_count =
			job_settings.alignment.processing.max_line_count === null
				? undefined
				: job_settings.alignment.processing.max_line_count;
		alignment_return_char_alignments =
			job_settings.alignment.return_char_alignments;
		alignment_interpolate_method = job_settings.alignment.interpolate_method;
	}
	diarization =
		job_settings.diarization !== undefined && job_settings.diarization !== null;
	if (job_settings.diarization) {
		diarization_min_speakers =
			job_settings.diarization.min_speakers === null
				? undefined
				: job_settings.diarization.min_speakers;
		diarization_max_speakers =
			job_settings.diarization.max_speakers === null
				? undefined
				: job_settings.diarization.max_speakers;
	}
	vad_onset = job_settings.vad_settings.vad_onset;
	vad_offset = job_settings.vad_settings.vad_offset;
	vad_chunk_size = job_settings.vad_settings.chunk_size;
	asr_beam_size = job_settings.asr_settings.beam_size;
	asr_patience = job_settings.asr_settings.patience;
	asr_length_penalty = job_settings.asr_settings.length_penalty;
	asr_temperature = job_settings.asr_settings.temperature;
	asr_temperature_increment_on_fallback =
		job_settings.asr_settings.temperature_increment_on_fallback;
	asr_compression_ratio_threshold =
		job_settings.asr_settings.compression_ratio_threshold;
	asr_log_prob_threshold = job_settings.asr_settings.log_prob_threshold;
	asr_no_speech_threshold = job_settings.asr_settings.no_speech_threshold;
	asr_initial_prompt =
		job_settings.asr_settings.initial_prompt === null ||
		job_settings.asr_settings.initial_prompt === undefined
			? ""
			: job_settings.asr_settings.initial_prompt;
	asr_suppressed_tokens = job_settings.asr_settings.suppress_tokens.join(",");
	asr_suppress_numerals = job_settings.asr_settings.suppress_numerals;

	wait_for_set = false;
}

async function setToDefault(requery = false) {
	wait_for_set = true;
	if (default_settings === undefined || requery) {
		default_settings = await queryDefaultValues();
	}
	setStateFromJobSettingsResp(default_settings);
}

if (pre_filled_in_settings) {
	setStateFromJobSettingsResp(pre_filled_in_settings);
} else {
	setToDefault();
}

let job_settings: components["schemas"]["JobSettings-Input"] = $derived.by(
	() => {
		let asr_suppress_tokens: number[] = [];
		for (const token_id_string of asr_suppressed_tokens.split(",")) {
			const parsed_int = Number.parseInt(token_id_string.trim());
			if (!Number.isNaN(parsed_int)) {
				asr_suppress_tokens.push(parsed_int);
			}
		}
		return {
			language: language === "detect" ? null : language,
			task: translate ? "translate" : "transcribe",
			model: model,
			email_notification: email_notification,
			alignment: alignment
				? {
						processing: {
							highlight_words: alignment_processing_highlight_words,
							max_line_width: alignment_processing_max_line_width,
							max_line_count: alignment_processing_max_line_count,
						},
						return_char_alignments: alignment_return_char_alignments,
						interpolate_method: alignment_interpolate_method,
					}
				: null,
			diarization: diarization
				? {
						min_speakers:
							diarization_min_speakers !== undefined
								? diarization_min_speakers
								: null,
						max_speakers: diarization_max_speakers,
					}
				: null,
			vad_settings: {
				vad_onset: vad_onset,
				vad_offset: vad_offset,
				chunk_size: vad_chunk_size,
			},
			asr_settings: {
				beam_size: asr_beam_size,
				patience: asr_patience,
				length_penalty: asr_length_penalty,
				temperature: asr_temperature,
				temperature_increment_on_fallback:
					asr_temperature_increment_on_fallback,
				compression_ratio_threshold: asr_compression_ratio_threshold,
				log_prob_threshold: asr_log_prob_threshold,
				no_speech_threshold: asr_no_speech_threshold,
				initial_prompt: asr_initial_prompt ? asr_initial_prompt : null,
				suppress_tokens: asr_suppress_tokens,
				suppress_numerals: asr_suppress_numerals,
			},
		};
	},
);

const supportedAlignmentLangs = [
	"en",
	"fr",
	"de",
	"es",
	"it",
	"ja",
	"zh",
	"nl",
	"uk",
	"pt",
	"ar",
	"cs",
	"ru",
	"pl",
	"hu",
	"fi",
	"fa",
	"el",
	"tr",
	"da",
	"he",
	"vi",
	"ko",
	"ur",
	"te",
	"hi",
	"ca",
	"ml",
	"no",
	"nn",
	"sk",
	"sl",
	"hr",
	"ro",
	"eu",
	"gl",
	"ka",
	"lv",
	"tl",
];

let languageNames = new Intl.DisplayNames(["en"], { type: "language" });

function onLanguageSelect() {
	if (language === "en") {
		translate = false;
	}
	if (!supportedAlignmentLangs.includes(language)) {
		alignment = false;
	}
}

function onTranslationChange() {
	if (translate) {
		alignment = false;
	}
}
</script>

<div class="flex flex-col gap-4">
  <div class="flex gap-2 items-center">
    <Checkbox id="email_notification" bind:checked={email_notification}>
      Receive an email notification upon job completion
    </Checkbox>
    <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
    <Tooltip placement="bottom" class="max-w-lg">You will receive an email once the job has finished or failed.</Tooltip>
  </div>

  <div>
    <div class="flex gap-2 items-center mb-1.5">
      <Label for="language">Language</Label>
      <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
      <Tooltip placement="bottom" class="max-w-lg">Set the language that is spoken in your audio file. Automatic language detection only works well for audio longer than 30 seconds and might lead to errors if improved timestamp alignment is enabled and it detects a language incompatible with it.</Tooltip>
    </div>
    <Select id="language" bind:value={language} onchange={onLanguageSelect}>
      <option value="detect">Automatic language detection</option>
      {#each jobLangEnumValues as value}
        <option value={value}>{languageNames.of(value)}</option>
      {/each}
    </Select>
  </div>

  <div class="flex gap-2 items-center">
    <Checkbox id="translate" bind:checked={translate} disabled={language === "en"} onchange={onTranslationChange}>
      Translate into English
    </Checkbox>
    <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
    <Tooltip placement="bottom" class="max-w-lg">Translate the transcript into English (starting from any other language). Currently English is the only supported target language.</Tooltip>
  </div>

  <div class="flex gap-2 items-center">
    <Checkbox id="alignment-enabled" bind:checked={alignment} disabled={(language !== "detect" && !supportedAlignmentLangs.includes(language)) || translate}>
      Enable improved timestamp alignment
    </Checkbox>
    <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
    <Tooltip placement="bottom" class="max-w-lg">This will align each part of the transcript with timestamps at which it was being spoken. Only supported for some languages.</Tooltip>
  </div>

  <div class="flex gap-2 items-center">
    <Checkbox id="diarization-enable" bind:checked={diarization}>
      Enable speaker diarization
    </Checkbox>
    <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
    <Tooltip placement="bottom" class="max-w-lg">Adds speaker labels to the transcript that will indicate who was speaking at any given part.</Tooltip>
  </div>

  {#if diarization}
    <div class="flex gap-4 items-end">
      <div class="w-full">
        <div class="flex gap-2 items-center mb-1.5">
          <Label for="diarization_min_speakers">Min speakers</Label>
          <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
          <Tooltip placement="bottom" class="max-w-lg">In the audio are at least this many different people speaking. Set this to the same as 'Max speakers' if you are exactly sure about the amount of people speaking, or leave it empty if you are very unsure.</Tooltip>
        </div>
        <Input id="diarization_min_speakers" type="number" min="0" step="1" placeholder="Leave empty if unsure" bind:value={diarization_min_speakers}/>
      </div>
      <div class="w-full">
        <div class="flex gap-2 items-center mb-1.5">
          <Label for="diarization_max_speakers">Max speakers</Label>
          <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
          <Tooltip placement="bottom" class="max-w-lg">In the audio are at most this many different people speaking. Set this to the same as 'Min speakers' if you are exactly sure about the amount of people speaking, or leave it empty if you are very unsure.</Tooltip>
        </div>
        <Input id="diarization_max_speakers" type="number" min="0" step="1" placeholder="Leave empty if unsure" bind:value={diarization_max_speakers}/>
      </div>
    </div>
  {/if}

  <Accordion>
    <AccordionItem contentClass="flex flex-col gap-8">
      {#snippet header()}Advanced settings{/snippet}
      <div>
        <div class="flex gap-2 items-center mb-1.5">
          <Label for="models">Select a model</Label>
          <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
          <Tooltip placement="bottom" class="max-w-lg">Select the Whisper model to use for transcription. Larger models will be more accurate but will also take longer. Diarization requires a larger model for useful results. The models ending with '.en' only support the English language, to use them please explicitly set the language to 'English'. The 'turbo' model is a more efficient version of the 'large' model with only small decreases in transcription quality.</Tooltip>
        </div>
        <Select id="models" required bind:value={model}>
          {#each jobModelEnumValues as value}
            <option value={value} disabled={value.indexOf("en") != -1 && language != "en"}>{value}</option>
          {/each}
        </Select>
      </div>

      {#if alignment}
        <div class="flex flex-col gap-4">
          <Heading tag="h6">Advanced alignment settings</Heading>
          <div class="flex gap-4 items-end">
            <div class="w-full flex gap-2 items-center">
              <Checkbox id="alignment_processing_highlight_words" bind:checked={alignment_processing_highlight_words}>
                Highlight words
              </Checkbox>
              <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
              <Tooltip placement="bottom" class="max-w-lg">Underline each word as it is spoken in the .srt and .vtt outputs. For example if used for subtitles this would mean that the word that is currently being spoken in the movie is underlined in the subtitle.</Tooltip>
            </div>
            <div class="w-full flex gap-2 items-center">
              <Checkbox id="alignment_return_char_alignments" bind:checked={alignment_return_char_alignments}>
                Return character alignments
              </Checkbox>
              <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
              <Tooltip placement="bottom" class="max-w-lg">Whether the .json output should contain timestamps for each character of the transcript, not only for each word, i.e. you will know when each letter was spoken.</Tooltip>
            </div>
          </div>
          <div class="flex gap-4 items-end">
            <div class="w-full">
              <div class="flex gap-2 items-center mb-1.5">
                <Label for="alignment_processing_max_line_width">Max line width</Label>
                <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
                <Tooltip placement="bottom" class="max-w-lg">The maximum number of characters in a line before breaking the line.</Tooltip>
              </div>
              <Input id="alignment_processing_max_line_width" type="number" min="1" step="1" bind:value={alignment_processing_max_line_width} placeholder="Leave empty for no limit"/>
            </div>
            <div class="w-full">
              <div class="flex gap-2 items-center mb-1.5">
                <Label for="alignment_processing_max_line_count">Max line count</Label>
                <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
                <Tooltip placement="bottom" class="max-w-lg">The maximum number of lines in a segment (can only be set if 'Max line width' is also set).</Tooltip>
              </div>
              <Input id="alignment_processing_max_line_count" type="number" min="1" step="1" bind:value={alignment_processing_max_line_count} placeholder="Leave empty for no limit"/>
            </div>
          </div>
          <div>
            <div class="flex gap-2 items-center mb-1.5">
              <Label for="models">Interpolate method</Label>
              <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
              <Tooltip placement="bottom" class="max-w-lg">Method to assign timestamps to non-aligned words. Words are not able to be aligned when none of the characters occur in the align model dictionary. "nearest" copies timestamp of the nearest word within the segment. "linear" is linear interpolation. "ignore" removes that word from output.</Tooltip>
            </div>
            <Select id="alignment_interpolate_method" required bind:value={alignment_interpolate_method}>
              {#each interpolateMethodEnumValues as value}
                <option value={value}>{value}</option>
              {/each}
            </Select>
          </div>
        </div>
      {/if}

      <div class="flex flex-col gap-4">
        <Heading tag="h6">Advanced Voice Activation Detection (VAD) settings</Heading>
        <div>
          <div class="flex gap-2 items-center mb-1.5">
            <Label for="vad_onset">VAD onset</Label>
            <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
            <Tooltip placement="bottom" class="max-w-lg">Onset threshold for VAD (see pyannote.audio), reduce this if speech is not being detected.</Tooltip>
          </div>
          <RangeWithField id="vad_onset" required min="0.001" max="0.999" step="0.001" bind:value={vad_onset}/>
        </div>
        <div>
          <div class="flex gap-2 items-center mb-1.5">
            <Label for="vad_offset">VAD offset</Label>
            <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
            <Tooltip placement="bottom" class="max-w-lg">Offset threshold for VAD (see pyannote.audio), reduce this if speech is not being detected.</Tooltip>
          </div>
          <RangeWithField id="vad_offset" required min="0.001" max="0.999" step="0.001" bind:value={vad_offset}/>
        </div>
        <div>
          <div class="flex gap-2 items-center mb-1.5">
            <Label for="vad_chunk_size">Chunk size</Label>
            <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
            <Tooltip placement="bottom" class="max-w-lg">Chunk size for merging VAD segments. Default is 30, reduce this if the chunk is too long.</Tooltip>
          </div>
          <RangeWithField id="vad_chunk_size" required min="1" max="30" step="1" bind:value={vad_chunk_size}/>
        </div>
      </div>

      <div class="flex flex-col gap-4">
        <Heading tag="h6">Advanced Automatic Speech Recognition (ASR) settings</Heading>
        <div>
          <div class="flex gap-2 items-center mb-1.5">
            <Label for="asr_initial_prompt">Initial prompt</Label>
            <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
            <Tooltip placement="bottom" class="max-w-lg">Optional text to provide as a prompt for the first window.</Tooltip>
          </div>
          <Textarea id="asr_initial_prompt" bind:value={asr_initial_prompt} placeholder="Enter prompt here"/>
        </div>
        <div>
          <div class="flex gap-2 items-center mb-1.5">
            <Label for="asr_beam_size">Beam size</Label>
            <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
            <Tooltip placement="bottom" class="max-w-lg">Number of beams in beam search, only applicable when temperature is zero.</Tooltip>
          </div>
          <Input id="asr_beam_size" type="number" required min="1" step="1" bind:value={asr_beam_size}/>
        </div>
        <div>
          <div class="flex gap-2 items-center mb-1.5">
            <Label for="asr_patience">Patience</Label>
            <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
            <Tooltip placement="bottom" class="max-w-lg">Optional patience value to use in beam decoding, the default (1.0) is equivalent to conventional beam search.</Tooltip>
          </div>
          <Input id="asr_patience" type="number" required min="0.0" step="0.001" bind:value={asr_patience}/>
        </div>
        <div>
          <div class="flex gap-2 items-center mb-1.5">
            <Label for="asr_length_penalty">Length penalty</Label>
            <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
            <Tooltip placement="bottom" class="max-w-lg">Optional token length penalty coefficient (alpha), uses simple length normalization by default.</Tooltip>
          </div>
          <RangeWithField id="asr_length_penalty" required min="0.0" max="1.0" step="0.001" bind:value={asr_length_penalty}/>
        </div>
        <div class="flex gap-4 items-end">
          <div class="w-full">
            <div class="flex gap-2 items-center mb-1.5">
              <Label for="asr_temperature">Temperature</Label>
              <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
              <Tooltip placement="bottom" class="max-w-lg">Temperature to use for sampling.</Tooltip>
            </div>
            <Input id="asr_temperature" type="number" required min="0.0" step="0.001" bind:value={asr_temperature}/>
          </div>
          <div class="w-full">
            <div class="flex gap-2 items-center mb-1.5">
              <Label for="asr_temperature_increment_on_fallback">Temperature increment on fallback</Label>
              <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
              <Tooltip placement="bottom" class="max-w-lg">Temperature to increase when falling back when the decoding fails to meet either of the thresholds below.</Tooltip>
            </div>
            <Input id="asr_temperature_increment_on_fallback" type="number" required min="0.0" step="0.001" bind:value={asr_temperature_increment_on_fallback}/>
          </div>
        </div>
        <div>
          <div class="flex gap-2 items-center mb-1.5">
            <Label for="asr_compression_ratio_threshold">Compression ratio threshold</Label>
              <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
              <Tooltip placement="bottom" class="max-w-lg">If the gzip compression ratio is higher than this value, treat the decoding as failed.</Tooltip>
          </div>
          <Input id="asr_compression_ratio_threshold" type="number" required min="0.0" step="0.001" bind:value={asr_compression_ratio_threshold}/>
        </div>
        <div>
          <div class="flex gap-2 items-center mb-1.5">
            <Label for="asr_log_prob_threshold">Log prob threshold</Label>
            <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
            <Tooltip placement="bottom" class="max-w-lg">If the average log probability is lower than this value, treat the decoding as failed.</Tooltip>
          </div>
          <Input id="asr_log_prob_threshold" type="number" required bind:value={asr_log_prob_threshold}/>
        </div>
        <div>
          <div class="flex gap-2 items-center mb-1.5">
            <Label for="asr_no_speech_threshold">No speech threshold</Label>
            <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
            <Tooltip placement="bottom" class="max-w-lg">If the probability of the &lt;&#124;nospeech&#124;&gt; token is higher than this value AND the decoding has failed due to 'Log prob threshold', consider the segment as silence.</Tooltip>
          </div>
          <Input id="asr_no_speech_threshold" type="number" step="0.001" required bind:value={asr_no_speech_threshold}/>
        </div>
        <div>
          <div class="flex gap-2 items-center mb-1.5">
            <Label for="asr_suppressed_tokens">Suppressed tokens</Label>
            <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
            <Tooltip placement="bottom" class="max-w-lg">Comma-separated list of token ids to suppress during sampling; '-1' will suppress most special characters except common punctuations.</Tooltip>
          </div>
          <Input id="asr_suppressed_tokens" type="text" bind:value={asr_suppressed_tokens}/>
        </div>
        <div class="flex gap-2 items-center">
          <Checkbox id="asr_suppress_numerals" bind:checked={asr_suppress_numerals}>
            Suppress numerals
          </Checkbox>
          <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
          <Tooltip placement="bottom" class="max-w-lg">Whether to suppress numeric symbols and currency symbols during sampling, since wav2vec2 cannot align them correctly.</Tooltip>
        </div>
      </div>
    </AccordionItem>
  </Accordion>
  <WaitingSubmitButton type="button" color="alternative" onclick={setToDefault} waiting={wait_for_set}><UndoOutline class="mr-2"/>Reset values to account defaults</WaitingSubmitButton>
</div>
