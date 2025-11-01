<script lang="ts">
	import {
		Badge,
		Checkbox,
		Dropzone,
		Label,
		Modal,
		Tooltip,
	} from "flowbite-svelte";
	import { FileMusicSolid, QuestionCircleOutline } from "flowbite-svelte-icons";
	import { SvelteMap } from "svelte/reactivity";
	import { PUBLIC_BACKEND_BASE_URL } from "$env/static/public";

	import { alerts } from "$lib/utils/global_state.svelte";
	import { BackendCommError } from "$lib/utils/httpRequests.svelte";
	import { postLoggedIn } from "$lib/utils/httpRequestsAuth.svelte";
	import { type components } from "$lib/utils/schema";
	import CloseButton from "./closeButton.svelte";
	import JobSettingsForm from "./jobSettingsForm.svelte";
	import WaitingSubmitButton from "./waitingSubmitButton.svelte";

	type JobSettingsResp = components["schemas"]["JobSettings-Output"];
	interface Props {
		open?: boolean;
		pre_action?: () => Promise<void>;
		post_action?: () => Promise<void>;
		pre_filled_in_settings?: JobSettingsResp;
	}
	let {
		open = $bindable(false),
		pre_action = async () => {},
		post_action = async () => {},
		pre_filled_in_settings,
	}: Props = $props();

	let files: FileList | null = $state(null);
	let all_files: SvelteMap<string, File> = $state(
		new SvelteMap<string, File>(),
	);
	$effect(() => {
		if (files) {
			for (let i = 0; i < files.length; i++) {
				const file = files.item(i);
				if (file && !all_files.has(file.name)) {
					all_files.set(file.name, file);
				}
			}
			files = null;
		}
	});

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

	async function postJob(file: File, job_settings_id: number) {
		let form_data = new FormData();
		form_data.set("audio_file", file);
		return await fetch(
			`${PUBLIC_BACKEND_BASE_URL}/api/jobs/submit_job?job_settings_id=${job_settings_id.toString()}`,
			{
				method: "POST",
				credentials: "include",
				body: form_data,
			},
		);
	}

	async function submitJob(): Promise<void> {
		if (all_files.size > 0) {
			await pre_action();
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
				for (let file of all_files.values()) {
					promises.push(postJob(file, settings_id));
				}
				let responses: PromiseSettledResult<Response>[] =
					await Promise.allSettled(promises);

				for (const [i, file] of Array.from(all_files.values()).entries()) {
					const response: PromiseSettledResult<Response> = responses[i];
					if (response.status !== "fulfilled" || !response.value.ok) {
						alerts.push({
							msg: `Error occurred while submitting job with filename '${file.name}'`,
							color: "red",
						});
					}
				}
			} catch (err: unknown) {
				let errorMsg = "Error occurred while trying to submit job settings: ";
				if (err instanceof BackendCommError) {
					errorMsg += err.message;
				} else {
					errorMsg += "Unknown error";
				}
				alerts.push({ msg: errorMsg, color: "red" });
			}

			open = false;
			waitingForPromise = false;
			await post_action();
		}
	}

	function onAction(params: { action: string; data: FormData }): boolean {
		if (params.action === "submit") {
			submitJob();
		}
		return false;
	}
</script>

<Modal form title={all_files.size > 1 ? `Submit ${all_files.size.toString()} new transcription jobs` : "Submit a new transcription job"} bind:open={open} onaction={onAction} onclose={() => all_files.clear()}>
  <JobSettingsForm bind:get_job_settings={get_job_settings} pre_filled_in_settings={pre_filled_in_settings}/>
  <div class="flex gap-2 items-center">
    <Checkbox id="make_new_account_defaults" bind:checked={makeNewDefaults}>Make these job settings the new account defaults</Checkbox>
    <Badge rounded large class="p-1! font-semibold!" color="gray"><QuestionCircleOutline class="w-4 h-4"/></Badge>
    <Tooltip placement="bottom" class="max-w-lg">The current job settings will become the new account-wide default. Every job you create in the future will have these settings set by default. You can view, change and reset the defaults in the account settings at any time.</Tooltip>
  </div>
  <div>
    <Label for="staging_files" class="mb-1.5">Upload staging area. A transcription job will be created for each of the listed files.</Label>
    <div id="staging_files" class="max-h-64 overflow-y-auto overflow-x-hidden p-2 flex flex-col items-center gap-2 bg-gray-200 dark:bg-gray-700 rounded-lg">
      {#if all_files.size === 0}
        <p class="text-gray-500 dark:text-gray-400">No files staged for upload</p>
      {/if}
      {#each all_files as [file_name, _]}
        <div class="w-full px-2 flex gap-2 justify-between items-center bg-white dark:bg-gray-800 rounded-lg">
          <div class="flex gap-2 items-center min-w-0">
            <FileMusicSolid/>
            <p class="text-gray-500 dark:text-gray-400 truncate">{file_name}</p>
          </div>
          <CloseButton id="remove_job_from_staging" type="button" onclick={() => all_files.delete(file_name)}/>
        </div>
      {/each}
    </div>
  </div>
  <div>
    <Label for="upload_files" class="mb-1.5">Add files to the staging area</Label>
    <Dropzone
      multiple
      id="upload_files"
      class="h-48"
      bind:files={files}
      ondrop={dropHandle}
      ondragover={(event) => {
        event.preventDefault();
      }}
      onchange={handleChange}>
      <svg aria-hidden="true" class="mb-3 w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
      {#if all_files.size === 0}
        <p class="mb-2 text-sm text-gray-500 dark:text-gray-400"><span class="font-semibold">Click</span> or <span class="font-semibold">drag and drop</span> to add files to the upload</p>
      {:else}
        {#if all_files.size === 1}
          <p class="mb-2 text-sm text-gray-500 dark:text-gray-400">1 file is staged for upload</p>
        {:else}
          <p class="mb-2 text-sm text-gray-500 dark:text-gray-400">{all_files.size} files are staged for upload</p>
        {/if}
        <p class="mb-2 text-sm text-gray-500 dark:text-gray-400"><span class="font-semibold">Click</span> or <span class="font-semibold">drag and drop</span> to add more files</p>
      {/if}
      <p class="text-xs text-gray-500 dark:text-gray-400">Audio files (mp3, m4a, aac, ...)</p>
    </Dropzone>
  </div>
  <WaitingSubmitButton class="w-full" waiting={waitingForPromise} value="submit">Submit</WaitingSubmitButton>
</Modal>
