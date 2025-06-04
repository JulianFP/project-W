<script lang="ts">
import { PUBLIC_BACKEND_BASE_URL } from "$env/static/public";
import { Checkbox, Dropzone, Heading, Label, Modal, P } from "flowbite-svelte";

import { alerts, auth } from "$lib/utils/global_state.svelte";
import { BackendCommError, postLoggedIn } from "$lib/utils/httpRequests.svelte";
import JobSettingsForm from "./jobSettingsForm.svelte";
import WaitingSubmitButton from "./waitingSubmitButton.svelte";

interface Props {
	open?: boolean;
	post_action: () => Promise<void>;
}
let { open = $bindable(false), post_action = async () => {} }: Props = $props();

let files: FileList | null = $state(null);
$inspect(files);

let makeNewDefaults: boolean = $state(false);
let get_job_settings = $state(() => {
	return {};
});

let waitingForPromise = $state(false);

function handleChange(event: Event): void {
	const target = event.target as HTMLInputElement;
	files = target.files;
}

function dropHandle(event: DragEvent): void {
	event.preventDefault();
	files = event.dataTransfer?.files ?? null;
}

function showFileNames(files: FileList): string {
	if (files.length === 1) return files[0].name;
	let concat = `${files.length.toString()} files: `;
	for (let file of files) {
		concat += `${file.name}, `;
	}

	if (concat.length > 50) {
		concat = `${concat.slice(0, 50)}...`;
	}
	if (concat[concat.length - 2] === ",")
		concat = concat.slice(0, concat.length - 2);
	return concat;
}

async function postJob(file: File, job_settings_id: number) {
	let form_data = new FormData();
	form_data.set("audio_file", file);
	return await fetch(
		`${PUBLIC_BACKEND_BASE_URL}/api/jobs/submit_job?job_settings_id=${job_settings_id.toString()}`,
		{
			method: "POST",
			headers: auth.getAuthHeader(),
			body: form_data,
		},
	);
}

async function submitAction(event: Event): Promise<void> {
	event.preventDefault();

	if (files !== null && files.length > 0) {
		waitingForPromise = true;

		//send job settings
		try {
			const settings_id = await postLoggedIn<number>(
				"jobs/submit_settings",
				get_job_settings(),
				false,
				{
					is_new_default: makeNewDefaults.toString(),
				},
			);

			//send all requests at ones and wait for promises in parallel with "allSettled" method
			//show results to user ones all promises have settled
			let promises: Promise<Response>[] = [];
			for (let file of files) {
				promises.push(postJob(file, settings_id));
			}
			let responses: PromiseSettledResult<Response>[] =
				await Promise.allSettled(promises);

			for (let i = 0; i < files.length; i++) {
				const response: PromiseSettledResult<Response> = responses[i];
				if (response.status === "fulfilled" && response.value.ok) {
					alerts.push({
						msg: `You successfully submitted job with filename '${
							files[i].name
						}'`,
						color: "green",
					});
				} else {
					alerts.push({
						msg: `Error occurred while submitting job with filename '${files[i].name}'`,
						color: "red",
					});
				}
			}
		} catch (err: unknown) {
			let errorMsg = "Error occured while trying to submit job settings: ";
			if (err instanceof BackendCommError) {
				errorMsg += err.message;
			} else {
				errorMsg += "Unknown error";
			}
			alerts.push({ msg: errorMsg, color: "red" });
		}

		open = false;
	}
	waitingForPromise = false;

	await post_action();
}
</script>

<Modal bind:open={open} autoclose={false}>
  <Heading tag="h3">{files !== null && files.length > 1 ? `Submit ${files.length.toString()} new transcription jobs` : "Submit a new transcription job"}</Heading>
  <JobSettingsForm onsubmit={submitAction} bind:get_job_settings={get_job_settings}>
    <Checkbox bind:checked={makeNewDefaults}><P>Make these job settings the new account defaults</P></Checkbox>
    <div>
      <Label class="mb-2" for="upload_files">Upload one or more audio files. A transcription job will be created for each of the uploaded files</Label>
      <Dropzone
        multiple
        id="upload_files"
        bind:files={files}
        ondrop={dropHandle}
        ondragover={(event) => {
          event.preventDefault();
        }}
        onchange={handleChange}>
        <svg aria-hidden="true" class="mb-3 w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
        {#if files === null || files.length === 0}
          <p class="mb-2 text-sm text-gray-500 dark:text-gray-400"><span class="font-semibold">Click to upload</span> or drag and drop</p>
          <p class="text-xs text-gray-500 dark:text-gray-400">Audio files (mp3, m4a, aac, ...)</p>
        {:else}
          <p>{showFileNames(files)}</p>
        {/if}
      </Dropzone>
    </div>
    <WaitingSubmitButton class="w-full1" waiting={waitingForPromise}>Submit</WaitingSubmitButton>
  </JobSettingsForm>
</Modal>
