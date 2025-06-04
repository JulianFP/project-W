<script lang="ts">
import { error } from "@sveltejs/kit";
import {
	Accordion,
	AccordionItem,
	Checkbox,
	Heading,
	Input,
	Label,
	P,
	Select,
	Textarea,
} from "flowbite-svelte";
import { RedoOutline } from "flowbite-svelte-icons";

import { BackendCommError, getLoggedIn } from "$lib/utils/httpRequests.svelte";
import {
	type components,
	interpolateMethodEnumValues,
	jobLangEnumValues,
	jobModelEnumValues,
} from "$lib/utils/schema.d";
import RangeWithField from "./rangeWithField.svelte";
import WaitingSubmitButton from "./waitingSubmitButton.svelte";

let {
	onsubmit,
	children,
	get_job_settings = $bindable(),
	re_query = $bindable(),
} = $props();

get_job_settings = () => {
	return job_settings;
};

re_query = async () => {
	await setToDefault(true);
};

let default_settings: components["schemas"]["JobSettings-Output"] | undefined =
	$state();
let wait_for_reset: boolean = $state(false);

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

async function setToDefault(requery = false) {
	wait_for_reset = true;
	if (default_settings === undefined || requery) {
		default_settings = await queryDefaultValues();
	}
	language =
		default_settings.language === null ||
		default_settings.language === undefined
			? "detect"
			: default_settings.language;
	translate = default_settings.task === "translate";
	model = default_settings.model;
	email_notification = default_settings.email_notification;
	alignment =
		default_settings.alignment !== undefined &&
		default_settings.alignment !== null;
	if (default_settings.alignment) {
		alignment_processing_highlight_words =
			default_settings.alignment.processing.highlight_words;
		alignment_processing_max_line_width =
			default_settings.alignment.processing.max_line_width === null
				? undefined
				: default_settings.alignment.processing.max_line_width;
		alignment_processing_max_line_count =
			default_settings.alignment.processing.max_line_count === null
				? undefined
				: default_settings.alignment.processing.max_line_count;
		alignment_return_char_alignments =
			default_settings.alignment.return_char_alignments;
		alignment_interpolate_method =
			default_settings.alignment.interpolate_method;
	}
	diarization =
		default_settings.diarization !== undefined &&
		default_settings.diarization !== null;
	if (default_settings.diarization) {
		diarization_min_speakers =
			default_settings.diarization.min_speakers === null
				? undefined
				: default_settings.diarization.min_speakers;
		diarization_max_speakers =
			default_settings.diarization.max_speakers === null
				? undefined
				: default_settings.diarization.max_speakers;
	}
	vad_onset = default_settings.vad_settings.vad_onset;
	vad_offset = default_settings.vad_settings.vad_offset;
	vad_chunk_size = default_settings.vad_settings.chunk_size;
	asr_beam_size = default_settings.asr_settings.beam_size;
	asr_patience = default_settings.asr_settings.patience;
	asr_length_penalty = default_settings.asr_settings.length_penalty;
	asr_temperature = default_settings.asr_settings.temperature;
	asr_temperature_increment_on_fallback =
		default_settings.asr_settings.temperature_increment_on_fallback;
	asr_compression_ratio_threshold =
		default_settings.asr_settings.compression_ratio_threshold;
	asr_log_prob_threshold = default_settings.asr_settings.log_prob_threshold;
	asr_no_speech_threshold = default_settings.asr_settings.no_speech_threshold;
	asr_initial_prompt =
		default_settings.asr_settings.initial_prompt === null ||
		default_settings.asr_settings.initial_prompt === undefined
			? ""
			: default_settings.asr_settings.initial_prompt;
	asr_suppressed_tokens =
		default_settings.asr_settings.suppress_tokens.join(",");
	asr_suppress_numerals = default_settings.asr_settings.suppress_numerals;

	wait_for_reset = false;
}
setToDefault();

let job_settings: components["schemas"]["JobSettings-Input"] = $derived.by(
	() => {
		let asr_suppress_tokens: number[] = [];
		for (const token_id_string of asr_suppressed_tokens.split(",")) {
			asr_suppress_tokens.push(Number.parseInt(token_id_string.trim()));
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

<form class="flex flex-col gap-4" {onsubmit}>
  <div>
    <Checkbox id="email_notification" bind:checked={email_notification}>
      <P>Receive an email notification upon job completion</P>
    </Checkbox>
  </div>

  <div>
    <Label class="mb-2" for="language">Language</Label>
    <Select id="language" bind:value={language} onchange={onLanguageSelect}>
      <option value="detect">Automatic language detection</option>
      {#each jobLangEnumValues as value}
        <option value={value}>{languageNames.of(value)}</option>
      {/each}
    </Select>
  </div>

  <Checkbox id="translate" bind:checked={translate} disabled={language === "en"} onchange={onTranslationChange}>
    <P>Translate into English</P>
  </Checkbox>

  <Checkbox id="alignment-enabled" bind:checked={alignment} disabled={(language !== "detect" && !supportedAlignmentLangs.includes(language)) || translate}>
    <P>Enable improved timestamp alignment</P>
  </Checkbox>

  <div>
    <Checkbox id="diarization-enable" bind:checked={diarization}>
      <P>Enable speaker diarization</P>
    </Checkbox>
  </div>

  {#if diarization}
    <div class="flex gap-4">
      <div class="w-full">
        <Label class="mb-2" for="diarization_min_speakers">Min speakers</Label>
        <Input type="number" min="0" step="1" id="diarization_min_speakers" bind:value={diarization_min_speakers}/>
      </div>
      <div class="w-full">
        <Label class="mb-2" for="diarization_max_speakers">Max speakers</Label>
        <Input type="number" min="0" step="1" id="diarization_max_speakers" bind:value={diarization_max_speakers}/>
      </div>
    </div>
  {/if}

  <Accordion>
    <AccordionItem contentClass="flex flex-col gap-8">
      {#snippet header()}Advanced settings{/snippet}
      <div>
        <Label class="mb-2" for="models">Select a model</Label>
        <Select id="models" bind:value={model}>
          {#each jobModelEnumValues as value}
            <option value={value} disabled={value.indexOf("en") != -1 && language != "en"}>{value}</option>
          {/each}
        </Select>
      </div>

      {#if alignment}
        <div class="flex flex-col gap-4">
          <Heading tag="h6">Advanced alignment settings</Heading>
          <div class="flex gap-4">
            <div class="w-full"><Checkbox id="alignment_processing_highlight_words" bind:checked={alignment_processing_highlight_words}>
              <P>Highlight words</P>
            </Checkbox></div>
            <div class="w-full"><Checkbox id="alignment_return_char_alignments" bind:checked={alignment_return_char_alignments}>
              <P>Return character alignments</P>
            </Checkbox></div>
          </div>
          <div class="flex gap-4">
            <div class="w-full">
              <Label class="mb-2" for="aligment_processing_max_line_width">Max line width</Label>
              <Input type="number" min="1" step="1" id="alignment_processing_max_line_width" bind:value={alignment_processing_max_line_width} placeholder="Leave empty for no limit"/>
            </div>
            <div class="w-full">
              <Label class="mb-2" for="alignment_processing_max_line_count">Max line count</Label>
              <Input type="number" min="1" step="1" id="alignment_processing_max_line_count" bind:value={alignment_processing_max_line_count} placeholder="Leave empty for no limit"/>
            </div>
          </div>
          <div>
            <Label class="mb-2" for="models">Interpolate method</Label>
            <Select id="alignment_interpolate_method" bind:value={alignment_interpolate_method}>
              {#each interpolateMethodEnumValues as value}
                <option value={value}>{value}</option>
              {/each}
            </Select>
          </div>
        </div>
      {/if}

      <div class="flex flex-col gap-4">
        <Heading tag="h6">Advanced VAD settings</Heading>
        <div>
          <Label class="mb-2" for="vad_onset">VAD onset</Label>
          <RangeWithField min="0.0" max="1.0" step="0.001" id="vad_onset" bind:value={vad_onset}/>
        </div>
        <div>
          <Label class="mb-2" for="vad_offset">VAD offset</Label>
          <RangeWithField min="0.0" max="1.0" step="0.001" id="vad_offset" bind:value={vad_offset}/>
        </div>
        <div>
          <Label class="mb-2" for="vad_chunk_size">Chunk size</Label>
          <RangeWithField min="1" max="30" step="1" id="vad_chunk_size" bind:value={vad_chunk_size}/>
        </div>
      </div>

      <div class="flex flex-col gap-4">
        <Heading tag="h6">Advanced ASR settings</Heading>
        <div>
          <Label class="mb-2" for="asr_initial_prompt">Initial prompt</Label>
          <Textarea id="asr_initial_prompt" bind:value={asr_initial_prompt} placeholder="Enter prompt here"/>
        </div>
        <div>
          <Label class="mb-2" for="asr_beam_size">Beam size</Label>
          <Input type="number" min="1" step="1" id="asr_beam_size" bind:value={asr_beam_size}/>
        </div>
        <div>
          <Label class="mb-2" for="asr_patience">Patience</Label>
          <Input type="number" min="0.0" step="0.001" id="asr_patience" bind:value={asr_patience}/>
        </div>
        <div>
          <Label class="mb-2" for="asr_length_penalty">Length penalty</Label>
          <RangeWithField min="0.0" max="1.0" step="0.001" id="asr_length_penalty" bind:value={asr_length_penalty}/>
        </div>
        <div class="flex gap-4">
          <div class="w-full">
            <Label class="mb-2" for="asr_temperature">Temperature</Label>
            <Input type="number" min="0.0" step="0.001" id="asr_temperature" bind:value={asr_temperature}/>
          </div>
          <div class="w-full">
            <Label class="mb-2" for="asr_temperature_increment_on_fallback">Temperature increment on fallback</Label>
            <Input type="number" min="0.0" step="0.001" id="asr_temperature_increment_on_fallback" bind:value={asr_temperature_increment_on_fallback}/>
          </div>
        </div>
        <div>
          <Label class="mb-2" for="asr_compression_ratio_threshold">Compression ratio threshold</Label>
          <Input type="number" min="0.0" step="0.001" id="asr_compression_ratio_threshold" bind:value={asr_compression_ratio_threshold}/>
        </div>
        <div>
          <Label class="mb-2" for="asr_log_prob_threshold">Log prob threshold</Label>
          <Input type="number" id="asr_log_prob_threshold" bind:value={asr_log_prob_threshold}/>
        </div>
        <div>
          <Label class="mb-2" for="asr_no_speech_threshold">No speech threshold</Label>
          <Input type="number" step="0.001" id="asr_no_speech_threshold" bind:value={asr_no_speech_threshold}/>
        </div>
        <div>
          <Label class="mb-2" for="asr_suppressed_tokens">Suppressed tokens</Label>
          <Input type="text" id="asr_suppressed_tokens" bind:value={asr_suppressed_tokens}/>
        </div>
        <Checkbox id="asr_suppress_numerals" bind:checked={asr_suppress_numerals}>
          <P>Suppress numerals</P>
        </Checkbox>
      </div>
    </AccordionItem>
  </Accordion>
  <WaitingSubmitButton type="button" color="alternative" onclick={setToDefault} waiting={wait_for_reset}><RedoOutline class="mr-2"/>Reset selected values to account defaults</WaitingSubmitButton>

  {@render children?.()}
</form>
