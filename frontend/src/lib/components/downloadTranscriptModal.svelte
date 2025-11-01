<script lang="ts">
	import { ButtonGroup, Helper, Label, Modal, P } from "flowbite-svelte";

	import { BackendCommError } from "$lib/utils/httpRequests.svelte";
	import { getLoggedIn } from "$lib/utils/httpRequestsAuth.svelte";
	import type { components } from "$lib/utils/schema";
	import Button from "./button.svelte";
	import WaitingSubmitButton from "./waitingSubmitButton.svelte";

	interface Props {
		open?: boolean;
		post_action?: () => Promise<void>;
		job_id: number;
		job_file_name: string;
	}
	let {
		open = $bindable(false),
		post_action = async () => {},
		job_id,
		job_file_name,
	}: Props = $props();

	let waiting: boolean = $state(false);
	let error: boolean = $state(false);
	let errorMsg: string = $state("");

	let format: components["schemas"]["TranscriptTypeEnum"] = $state("as_txt");

	let format_ending = $derived(format.split("_")[1]);

	let format_preview = $derived.by(() => {
		switch (format) {
			case "as_txt":
				return "Space, the final frontier.<br>These are the voyages of the starship Enterprise.<br>Its five-year mission, to explore strange new worlds, ...";
			case "as_srt":
				return "1<br>00:00:06,089 --> 00:00:14,663<br>Space, the final frontier.<br><br>2<br>00:00:14,683 --> 00:00:17,588<br>These are the voyages of the starship Enterprise.<br><br>3<br>00:00:18,910 --> 00:00:29,447<br>Its five-year mission, to explore strange new worlds, ...";
			case "as_tsv":
				return "start\tend\ttext<br>6089\t14663\tSpace, the final frontier.<br>14683\t17588\tThese are the voyages of the starship Enterprise.<br>18910\t29447\tIts five-year mission, to explore strange new worlds, ...";
			case "as_vtt":
				return "WEBVTT<br><br>00:06.089 --> 00:14.663<br>Space, the final frontier.<br><br>00:14.683 --> 00:17.588<br>These are the voyages of the starship Enterprise.<br><br>00:18.910 --> 00:29.447<br>Its five-year mission, to explore strange new worlds, ...";
			case "as_json":
				return `{<br>  "language": "en",<br>  "segments": [<br>    {<br>      "end": 14.663,<br>      "text": " Space, the final frontier.",<br>      "start": 6.089,<br>      "words": [<br>        {<br>          "end": 6.59,<br>          "word": "Space,",<br>          "score": 0.94,<br>          "start": 6.089<br>        },<br>        {<br>          "end": 7.311,<br>          "word": "the",<br>          "score": 0.462,<br>          "start": 7.231<br>        },<br>        ...<br>      ]<br>    },<br>    ...<br>  ]<br>}`;
		}
	});

	function getMimeTypeOfFormat() {
		switch (format) {
			case "as_txt":
				return "text/plain";
			case "as_srt":
				return "application/x-subrip";
			case "as_tsv":
				return "text/tab-separated-values";
			case "as_vtt":
				return "text/vtt";
			case "as_json":
				return "application/json";
		}
	}

	async function downloadTranscript(): Promise<void> {
		waiting = true;
		error = false;

		try {
			let transcript: string;
			if (format === "as_json") {
				transcript = JSON.stringify(
					await getLoggedIn("jobs/download_transcript", {
						job_id: job_id.toString(),
						transcript_type: "as_json",
					}),
				);
			} else {
				transcript = await getLoggedIn<string>("jobs/download_transcript", {
					job_id: job_id.toString(),
					transcript_type: format,
				});
			}

			//convert transcript to Blob and generate url for it
			const blob = new Blob([transcript], {
				type: getMimeTypeOfFormat(),
			});
			const url = URL.createObjectURL(blob);

			//create document element with this url and 'click' it
			const element = document.createElement("a");
			element.href = url;
			element.download = `${job_file_name.replace(
				/\.[^/.]+$/,
				"",
			)}.${format_ending}`;
			element.click();
			open = false;
		} catch (err: unknown) {
			if (err instanceof BackendCommError) {
				errorMsg = err.message;
			} else {
				errorMsg = "Unknown error";
			}
			error = true;
		}

		waiting = false;
		await post_action();
	}

	function onAction(params: { action: string; data: FormData }): boolean {
		if (params.action === "submit") {
			downloadTranscript();
		}
		return false;
	}
</script>

<Modal form title={`Download transcript of job ${job_id}`} bodyClass="flex flex-col gap-4" bind:open={open} onaction={onAction}>
  <div>
    <Label class="mb-2">Format of the transcript</Label>
    <ButtonGroup class="w-full">
      <Button class="w-full" onclick={() => format = "as_txt"} color={format === "as_txt" ? "primary" : "alternative"}>.txt</Button>
      <Button class="w-full" onclick={() => format = "as_srt"} color={format === "as_srt" ? "primary" : "alternative"}>.srt</Button>
      <Button class="w-full" onclick={() => format = "as_tsv"} color={format === "as_tsv" ? "primary" : "alternative"}>.tsv</Button>
      <Button class="w-full" onclick={() => format = "as_vtt"} color={format === "as_vtt" ? "primary" : "alternative"}>.vtt</Button>
      <Button class="w-full" onclick={() => format = "as_json"} color={format === "as_json" ? "primary" : "alternative"}>.json</Button>
    </ButtonGroup>
  </div>

  <div>
    <Label class="mb-2">Preview of the format</Label>
    <P space="tighter" italic size="xs"><pre>{@html format_preview}</pre></P>
  </div>

  {#if error}
    <Helper color="red">{errorMsg}</Helper>
  {/if}

  <WaitingSubmitButton waiting={waiting} value="submit">Download as .{format_ending}</WaitingSubmitButton>
</Modal>
