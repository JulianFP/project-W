<script lang="ts">
import { EventSource } from "eventsource";
import {
	A,
	Alert,
	Banner,
	Checkbox,
	P,
	PaginationNav,
	Progressbar,
	Span,
	Spinner,
	Table,
	TableBody,
	TableBodyCell,
	TableBodyRow,
	TableHead,
	TableHeadCell,
	Tooltip,
} from "flowbite-svelte";
import {
	CaretDownSolid,
	CaretSortSolid,
	CaretUpSolid,
	ChevronLeftOutline,
	ChevronRightOutline,
	DownloadSolid,
	InfoCircleSolid,
	PlusOutline,
	RedoOutline,
	StopSolid,
	TrashBinSolid,
} from "flowbite-svelte-icons";
import { SvelteMap } from "svelte/reactivity";
import { slide } from "svelte/transition";

import { PUBLIC_BACKEND_BASE_URL } from "$env/static/public";
import Button from "$lib/components/button.svelte";
import CenterPage from "$lib/components/centerPage.svelte";
import CloseButton from "$lib/components/closeButton.svelte";
import ConfirmModal from "$lib/components/confirmModal.svelte";
import DownloadTranscriptModal from "$lib/components/downloadTranscriptModal.svelte";
import SubmitJobsModal from "$lib/components/submitJobsModal.svelte";
import { alerts, auth } from "$lib/utils/global_state.svelte";
import { BackendCommError } from "$lib/utils/httpRequests.svelte";
import {
	deletLoggedIn,
	getLoggedIn,
	postLoggedIn,
} from "$lib/utils/httpRequestsAuth.svelte";
import type { components } from "$lib/utils/schema";
import { autoupdate_date_since } from "$lib/utils/timestamp_handling.svelte";

type JobSettingsResp = components["schemas"]["JobSettings-Output"];
type Data = {
	about: components["schemas"]["AboutResponse"];
};
interface Props {
	data: Data;
}
let { data }: Props = $props();

type SortKey = components["schemas"]["JobSortKey"];
type Job = components["schemas"]["JobInfo"];
type ProcessedJob = Job & {
	creation_date: Date;
	finish_date: Date | null;
};

let fetchingJobs = $state(false);
let jobs_ordered_selected: SvelteMap<number, boolean> = $state(new SvelteMap());
let jobs_info: SvelteMap<number, ProcessedJob> = $state(new SvelteMap());
let job_creation_date_since: SvelteMap<number, string> = $state(
	new SvelteMap(),
);
let job_finish_date_since: SvelteMap<number, string> = $state(new SvelteMap());
let job_count: number = $state(0);
let job_count_total: number = $state(0);

//table stuff
const jobs_per_page = 10;
let currentPage = $state(1);
let totalPages = $derived(Math.max(Math.ceil(job_count / jobs_per_page), 1));
let selectedItems: number[] = $derived(
	Array.from(jobs_ordered_selected.entries())
		.filter(([, val]) => val)
		.map(([key]) => key),
);
let headerCheckboxSelected = $state(false);
let selectedAbortButtonDisabled = $state(true);
let selectedDeleteButtonDisabled = $state(true);
let openRow: number | null = $state(null);

//modal stuff
let pre_filled_job_settings: JobSettingsResp | undefined = $state();
let submitModalOpen = $state(false);
let downloadModalOpen = $state(false);
let downloadJobId: number = $state(-1);
let downloadFileName: string = $state("");
let abortModalOpen = $state(false);
let abortModalJobs: number[] = $state([]);
let deleteModalOpen = $state(false);
let deleteModalJobs: number[] = $state([]);

//job query parameters
let sort_key: SortKey = $state("creation_time");
let descending: boolean = $state(true);
let exclude_finished = $state(false);
let exclude_downloaded = $state(true);

function process_job(job: Job) {
	const creation_date_getter = () => {
		const date = jobs_info.get(job.id)?.creation_date;
		if (!date) throw new Error();
		return date;
	};
	const creation_date_since_setter = (date_since: string) => {
		job_creation_date_since.set(job.id, date_since);
	};
	const creation_date = new Date(job.creation_timestamp);
	const creation_date_since = autoupdate_date_since(
		creation_date_getter,
		creation_date_since_setter,
		creation_date,
	);
	job_creation_date_since.set(job.id, creation_date_since);
	let finish_date: Date | null = null;
	if (job.finish_timestamp) {
		const finish_date_getter = () => {
			const date = jobs_info.get(job.id)?.finish_date;
			if (!date) throw new Error();
			return date;
		};
		const finish_date_since_setter = (date_since: string) => {
			job_finish_date_since.set(job.id, date_since);
		};
		finish_date = new Date(job.finish_timestamp);
		const finish_date_since = autoupdate_date_since(
			finish_date_getter,
			finish_date_since_setter,
			finish_date,
		);
		job_finish_date_since.set(job.id, finish_date_since);
	}
	jobs_info.set(job.id, {
		...job,
		creation_date: creation_date,
		finish_date: finish_date,
	});
}

async function fetch_jobs() {
	fetchingJobs = true;
	try {
		job_count = await getLoggedIn<number>("jobs/count", {
			exclude_finished: exclude_finished.toString(),
			exclude_downloaded: exclude_downloaded.toString(),
		});
		job_count_total = await getLoggedIn<number>("jobs/count", {
			exclude_finished: "false",
			exclude_downloaded: "false",
		});
		if (job_count > 0) {
			const job_ids = await getLoggedIn<number[]>("jobs/get", {
				start_index: (jobs_per_page * (currentPage - 1)).toString(),
				end_index: (jobs_per_page * currentPage - 1).toString(),
				sort_key: sort_key,
				descending: descending.toString(),
				exclude_finished: exclude_finished.toString(),
				exclude_downloaded: exclude_downloaded.toString(),
			});
			let jobs_ordered_selected_loc = new Map<number, boolean>();
			for (const job_id of job_ids) {
				//to preserve the ordering of the jobs
				jobs_ordered_selected_loc.set(job_id, false);
			}
			if (jobs_ordered_selected_loc.size === 0) {
				jobs_ordered_selected.clear();
				jobs_info.clear();
			} else {
				jobs_ordered_selected = new SvelteMap(jobs_ordered_selected_loc);
				let args_formatted: string[][] = [];
				for (const job_id of jobs_ordered_selected_loc.keys()) {
					let job = jobs_info.get(job_id);
					if (!job) {
						args_formatted.push(["job_ids", job_id.toString()]);
					} else {
						process_job(job);
					}
				}
				if (args_formatted.length > 0) {
					const jobs_unsorted = await getLoggedIn<Job[]>(
						"jobs/info",
						args_formatted,
					);
					for (const job of jobs_unsorted) {
						process_job(job);
					}
					for (const job_id of jobs_info.keys()) {
						if (!jobs_ordered_selected_loc.has(job_id))
							jobs_info.delete(job_id);
					}
				}
			}
		} else {
			jobs_ordered_selected.clear();
			jobs_info.clear();
		}
		updateHeaderCheckbox();
	} catch (err: unknown) {
		let errorMsg = "Error occurred while fetching jobs from backend: ";
		if (err instanceof BackendCommError) {
			errorMsg += err.message;
		} else {
			errorMsg += "Unknown error";
		}
		alerts.push({ msg: errorMsg, color: "red" });
	}
	fetchingJobs = false;
}
fetch_jobs();

async function update_jobs(job_ids: number[]) {
	let args_formatted: string[][] = [];
	for (const job_id of job_ids) {
		args_formatted.push(["job_ids", job_id.toString()]);
	}
	try {
		const jobs_unsorted = await getLoggedIn<Job[]>("jobs/info", args_formatted);
		for (const job of jobs_unsorted) {
			process_job(job);
		}
	} catch (err: unknown) {
		let errorMsg = "Error occurred while updating job: ";
		if (err instanceof BackendCommError) {
			errorMsg += err.message;
		} else {
			errorMsg += "Unknown error";
		}
		alerts.push({ msg: errorMsg, color: "red" });
	}
}

function deselect_all_jobs() {
	for (let id of jobs_ordered_selected.keys()) {
		jobs_ordered_selected.set(id, false);
	}
	updateHeaderCheckbox();
}

function sortClickHandler(key: SortKey) {
	if (sort_key === key) descending = !descending;
	else sort_key = key;
	fetch_jobs();
}

async function abortJobs(jobIdsToAbort: number[]): Promise<void> {
	try {
		await postLoggedIn("jobs/abort", jobIdsToAbort);
	} catch (err: unknown) {
		let errorMsg = `Error occurred while trying to abort the jobs with ids ${jobIdsToAbort.toString()}: `;
		if (err instanceof BackendCommError) errorMsg += err.message;
		else errorMsg += "Unknown error";
		alerts.push({ msg: errorMsg, color: "red" });
	}
}
async function postAbortJobs(abortedJobIds: number[]): Promise<void> {
	for (const job_id of abortedJobIds) {
		jobs_info.delete(job_id);
	}
	await update_jobs(abortedJobIds);
	updateHeaderCheckbox();
}

async function deleteJobs(jobIdsToAbort: number[]): Promise<void> {
	try {
		await deletLoggedIn("jobs/delete", jobIdsToAbort);
	} catch (err: unknown) {
		let errorMsg = `Error occurred while trying to delete the jobs with ids ${jobIdsToAbort.toString()}: `;
		if (err instanceof BackendCommError) errorMsg += err.message;
		else errorMsg += "Unknown error";
		alerts.push({ msg: errorMsg, color: "red" });
	}
}

function openAbortModal(jobIds: number[]) {
	if (
		!abortModalOpen &&
		jobIds.length > 0 &&
		!deleteModalOpen &&
		!submitModalOpen &&
		!downloadModalOpen
	) {
		abortModalJobs = jobIds;
		abortModalOpen = true;
	}
}

function openDeleteModal(jobIds: number[]) {
	if (
		!deleteModalOpen &&
		jobIds.length > 0 &&
		!abortModalOpen &&
		!submitModalOpen &&
		!downloadModalOpen
	) {
		deleteModalJobs = jobIds;
		deleteModalOpen = true;
	}
}

function openSubmitModal(pre_fill_with_settings_of_job: number | null = null) {
	if (pre_fill_with_settings_of_job != null) {
		pre_filled_job_settings = jobs_info.get(
			pre_fill_with_settings_of_job,
		)?.settings;
	} else {
		pre_filled_job_settings = undefined;
	}
	if (
		!submitModalOpen &&
		!abortModalOpen &&
		!deleteModalOpen &&
		!downloadModalOpen
	) {
		submitModalOpen = true;
	}
}

function openDownloadModal(job_id: number, file_name: string) {
	if (
		!submitModalOpen &&
		!abortModalOpen &&
		!deleteModalOpen &&
		!downloadModalOpen
	) {
		downloadJobId = job_id;
		downloadFileName = file_name;
		downloadModalOpen = true;
	}
}

function updateHeaderCheckbox(job: Job | null = null) {
	//update headerCheckbox
	if (
		jobs_ordered_selected.size === 0 ||
		(job != null && !jobs_ordered_selected.get(job.id))
	) {
		headerCheckboxSelected = false;
	} else {
		let allSelected = true;
		for (let [job_id, selected] of jobs_ordered_selected.entries()) {
			if (!selected) {
				allSelected = false;
				jobs_ordered_selected.set(job_id, false);
			}
		}
		headerCheckboxSelected = allSelected;
	}

	//update disabled states
	if (selectedItems.length === 0) {
		selectedAbortButtonDisabled = true;
		selectedDeleteButtonDisabled = true;
	} else {
		let includesNotRunning = false;
		let includesNotDone = false;
		for (const job of jobs_info.values()) {
			if (selectedItems.includes(job.id)) {
				if (
					![
						"not_queued",
						"pending_runner",
						"runner_assigned",
						"runner_in_progress",
					].includes(job.step)
				)
					includesNotRunning = true;
				if (!["success", "downloaded", "failed"].includes(job.step))
					includesNotDone = true;
			}
			if (includesNotRunning && includesNotDone) break;
		}
		selectedAbortButtonDisabled = includesNotRunning;
		selectedDeleteButtonDisabled = includesNotDone;
	}
}

// update jobs using SSE (Server-Sent Events)
function updateJobOnSSEEvent(event: MessageEvent) {
	const job_id: number = Number.parseInt(event.data);
	if (auth.loggedIn && jobs_info.has(job_id)) {
		update_jobs([job_id]);
	}
}
function reloadSSEListeners() {
	const evtSource = new EventSource(
		`${PUBLIC_BACKEND_BASE_URL}/api/jobs/events`,
		{
			withCredentials: true,
			fetch: (input, init) =>
				fetch(input, {
					...init,
					headers: {
						...init.headers,
					},
				}),
		},
	);
	evtSource.removeEventListener("job_deleted", fetch_jobs);
	evtSource.removeEventListener("job_created", fetch_jobs);
	evtSource.removeEventListener("job_updated", updateJobOnSSEEvent);
	evtSource.addEventListener("job_deleted", fetch_jobs);
	evtSource.addEventListener("job_created", fetch_jobs);
	evtSource.addEventListener("job_updated", updateJobOnSSEEvent);
}
reloadSSEListeners();
if (window.cookieStore !== undefined) {
	cookieStore.addEventListener("change", (event: CookieChangeEvent) => {
		for (const { name, value } of event.changed) {
			if (name === "token" && value) {
				reloadSSEListeners();
			}
		}
	});
} else {
	console.warn(
		"Your browser doesn't seem to support the Cookie Store API. Automatic updates of the jobs table may be impacted by this. Consider updating your browser!",
	);
}
</script>

<CenterPage title="Your transcription jobs">
  <div class="flex flex-col gap-4">
    {#if data.about.job_retention_in_days !== null}
      <Alert>
        {#snippet icon()}<InfoCircleSolid class="h-5 w-5" />{/snippet}
        After a job has finished you have {data.about.job_retention_in_days} days to download the transcript before it gets deleted
      </Alert>
    {/if}

    <div class="flex justify-between items-center gap-8">
      <div class="flex items-center gap-x-8 gap-y-1.5 flex-wrap">
        <Checkbox id="hide_finished_jobs" bind:checked={exclude_finished} onchange={fetch_jobs}>Hide finished jobs</Checkbox>
        <Checkbox id="hide_downloaded_jobs" bind:checked={exclude_downloaded} disabled={exclude_finished} onchange={fetch_jobs}>Hide downloaded jobs</Checkbox>
      </div>
      <Button pill onclick={() => openSubmitModal()} class="shrink-0"><PlusOutline class="mr-2"/>New Job</Button>
    </div>
    <Table shadow hoverable={true} border={false}>
      <TableHead>
        <TableHeadCell class="!p-4">
          <Checkbox id="select_all_visible_elements" class="hover:cursor-pointer" bind:checked={headerCheckboxSelected} disabled={jobs_ordered_selected.size === 0} onchange={() => {jobs_ordered_selected.forEach((_,job_id) => jobs_ordered_selected.set(job_id, headerCheckboxSelected)); updateHeaderCheckbox();}}/>
        </TableHeadCell>
        <TableHeadCell class="hover:dark:text-white hover:text-primary-600 hover:cursor-pointer" onclick={() => sortClickHandler("creation_time")}>
          <div class="flex">
            {#if sort_key === "creation_time"}
              {#if descending}
                <CaretDownSolid class="inline mr-2"/>
              {:else}
                <CaretUpSolid class="inline mr-2"/>
              {/if}
            {:else}
              <CaretSortSolid class="inline mr-2"/>
            {/if}
            creation time
          </div>
        </TableHeadCell>
        <TableHeadCell class="hover:dark:text-white hover:text-primary-600 hover:cursor-pointer" onclick={() => sortClickHandler("filename")}>
          <div class="flex">
            {#if sort_key === "filename"}
              {#if descending}
                <CaretDownSolid class="inline mr-2"/>
              {:else}
                <CaretUpSolid class="inline mr-2"/>
              {/if}
            {:else}
              <CaretSortSolid class="inline mr-2"/>
            {/if}
            filename
          </div>
        </TableHeadCell>
        <TableHeadCell>progress</TableHeadCell>
        <TableHeadCell class="text-center" padding="py-1 pr-4">
        </TableHeadCell>
      </TableHead>
      <TableBody>
        {#each jobs_ordered_selected.entries() as [job_id,selected] (job_id)}
          {@const job = jobs_info.get(job_id)}
          {#if job}
            <TableBodyRow onclick={() => openRow = openRow === job.id ? null : job.id} color={selected ? "primary" : "default"} class={selected ? "border-l-5 bg-primary-200 dark:bg-primary-1000 border-primary-500 dark:border-primary-800 hover:bg-primary-300 dark:hover:bg-primary-950" : ""}>
              <TableBodyCell class="!p-4">
                <Checkbox id="select_job_{job}" class="hover:cursor-pointer" bind:checked={() => selected, (c: boolean) => jobs_ordered_selected.set(job.id, c)} onchange={() => updateHeaderCheckbox(job)} onclick={(e) => e.stopPropagation()}/>
              </TableBodyCell>
              <TableBodyCell>
                <P size="sm">{job_creation_date_since.get(job_id)}</P>
                <Tooltip type="auto">{job.creation_date.toLocaleString()}</Tooltip>
              </TableBodyCell>
              <TableBodyCell>
                {#if job.file_name.length > 32}
                  <P size="sm" class="break-all">{`${job.file_name.slice(0,32)}...`}</P>
                  <Tooltip type="auto">{job.file_name}</Tooltip>
                {:else}
                  <P size="sm">{job.file_name}</P>
                {/if}
              </TableBodyCell>
              <TableBodyCell class="pl-6 pr-4 py-4 whitespace-nowrap font-medium w-full">
                {#if (["runner_assigned", "runner_in_progress"].includes(job.step))}
                  <Progressbar precision={2} progress={(job.progress < 0) ? 0 : job.progress} size="h-4" labelInside animate/>
                {:else if job.step === "success"}
                  <Progressbar color="green" precision={2} progress={(job.progress < 0) ? 0 : job.progress} size="h-4" labelInside/>
                {:else if job.step === "failed" && job.error_msg}
                  <P class="text-red-700 dark:text-red-500" size="sm">failed - {(job.error_msg.length <= 21) ? job.error_msg : `${job.error_msg.slice(0,21)}...`}</P>
                  <Progressbar color="red" progress={100} size="h-4"/>
                {:else if job.step === "downloaded"}
                  <Progressbar color="indigo" precision={2} progress={(job.progress < 0) ? 0 : job.progress} size="h-4" labelInside/>
                {:else if job.step === "aborting"}
                  <P class="text-orange-700 dark:text-orange-500" size="sm">aborting...</P>
                  <Progressbar progress={100} size="h-4"/>
                {:else}
                  <Progressbar color="gray" precision={2} progress={(job.progress < 0) ? 0 : job.progress} size="h-4" labelInside/>
                {/if}
              </TableBodyCell>
              <TableBodyCell class="pr-4 py-4 whitespace-nowrap font-medium text-center">
                {#if (["success", "downloaded"].includes(job.step))}
                  <Button class="!p-2 flex flex-col" size="xs" color={job.step === "success" ? "primary" : "alternative"}  onclick={(e: MouseEvent) => {e.stopPropagation(); openDownloadModal(job_id, job.file_name);}}>
                    <DownloadSolid/>
                    Download
                  </Button>
                {/if}
              </TableBodyCell>
            </TableBodyRow>
            {#if openRow === job.id}
              <TableBodyRow color={selected ? "primary" : "default"} class={selected ? "bg-primary-300 dark:bg-primary-950 hover:bg-primary-400 dark:hover:bg-primary-900" : "bg-slate-100 dark:bg-slate-700 hover:bg-slate-100 hover:dark:bg-slate-700"}>
                <TableBodyCell colspan={5}>
                  <div class="grid grid-cols-2 gap-x-8 gap-y-2">
                    <div>
                      <P class="inline" weight="extrabold" size="sm">Job ID: </P>
                      <P class="inline" size="sm">{job.id}</P>
                    </div>
                    <div>
                      <A class="font-semibold" onclick={() => openSubmitModal(job_id)}>Job settings <RedoOutline size="md" class="ml-1.5"/></A>
                    </div>
                    <div>
                      <P class="inline" weight="extrabold" size="sm">Current processing step: </P>
                      <P class="inline" size="sm">{job.step}</P>
                    </div>
                    {#if job.finish_date}
                      <div>
                        <P class="inline" weight="extrabold" size="sm">Finish time: </P>
                        <P class="inline" size="sm">{job_finish_date_since.get(job_id)}</P>
                        <Tooltip type="auto">{job.finish_date.toLocaleString()}</Tooltip>
                      </div>
                    {/if}
                    {#if job.runner_id}
                      <div>
                        <P class="inline" weight="extrabold" size="sm">Runner ID: </P>
                        <P class="inline" size="sm">{job.runner_id}</P>
                      </div>
                    {/if}
                    {#if job.runner_name}
                      <div>
                        <P class="inline" weight="extrabold" size="sm">Runner name: </P>
                        <P class="inline" size="sm">{job.runner_name}</P>
                      </div>
                    {/if}
                    {#if job.runner_version}
                      <div>
                        <P class="inline" weight="extrabold" size="sm">Runner version: </P>
                        <P class="inline" size="sm">{job.runner_version}</P>
                      </div>
                    {/if}
                    {#if job.runner_git_hash && job.runner_source_code_url}
                      <div>
                        <A class="font-semibold" href={job.runner_source_code_url} target="_blank" rel="noopener noreferrer">Runner source code</A>
                        <P class="inline" size="sm">checked out at git hash {job.runner_git_hash}</P>
                      </div>
                    {/if}
                    {#if job.step === "failed" && job.error_msg}
                      <div>
                        <P class="inline" weight="extrabold" size="sm">Error message: </P>
                        <P class="inline" size="sm">{job.error_msg}</P>
                      </div>
                    {/if}
                  </div>
                </TableBodyCell>
              </TableBodyRow>
            {/if}
          {:else}
            <TableBodyRow>
              <TableBodyCell colspan={5}>
                <div class="flex items-center justify-center">
                  <Spinner/>
                </div>
              </TableBodyCell>
            </TableBodyRow>
        {/if}
        {:else}
          {#if job_count_total === 0}
            <TableBodyRow>
              <TableBodyCell colspan={5}>You don't have any jobs yet. <Span underline>Create your first job</Span> by clicking on the <P color="text-primary-600 dark:text-primary-500" weight="bold" size="sm" class="inline">New Job</P> button.</TableBodyCell>
            </TableBodyRow>
          {:else}
            <TableBodyRow>
              <TableBodyCell colspan={5}>You don't have any current jobs. Deselect <P color="text-primary-600 dark:text-primary-500" weight="bold" size="sm" class="inline">Hide finished jobs</P> or <P color="text-primary-600 dark:text-primary-500" weight="bold" size="sm" class="inline">Hide downloaded jobs</P>, or <Span underline>create a new job</Span> by clicking on the <P color="text-primary-600 dark:text-primary-500" weight="bold" size="sm" class="inline">New Job</P> button.</TableBodyCell>
            </TableBodyRow>
          {/if}
        {/each}
      </TableBody>
    </Table>
  </div>

  <div class="flex flex-col items-center justify-center gap-2">
    <div class="text-sm text-gray-700 dark:text-gray-400">
      Showing <span class="font-semibold text-gray-900 dark:text-white">{(currentPage-1)*jobs_per_page+(jobs_ordered_selected.size === 0 ? 0 : 1)}</span>
      to
      <span class="font-semibold text-gray-900 dark:text-white">{Math.min(currentPage*jobs_per_page, job_count)}</span>
      of
      <span class="font-semibold text-gray-900 dark:text-white">{job_count}</span>
      Entries
    </div>
    <PaginationNav {currentPage} {totalPages} onPageChange={(page: number) => {currentPage = page; fetch_jobs();}}>
      {#snippet prevContent()}
	        <span class="sr-only">Previous</span>
	        <ChevronLeftOutline/>
			{/snippet}
      {#snippet nextContent()}
	        <span class="sr-only">Next</span>
	        <ChevronRightOutline/>
			{/snippet}
    </PaginationNav>
  </div>

  <Banner open={selectedItems.length > 0} innerClass="w-full max-w-screen-md flex flex-row justify-between items-center" type="bottom" transition={slide} dismissable={false}>
    <P>{selectedItems.length} selected</P>
    <div class="flex items-center gap-2">
      <Button class="!p-2" size="xs" color="red" onclick={() => openAbortModal(selectedItems)} disabled={selectedAbortButtonDisabled}>
        <StopSolid class="inline mr-1"/>
        Abort
      </Button>
      <Button class="!p-2" size="xs" color="red" onclick={() => openDeleteModal(selectedItems)} disabled={selectedDeleteButtonDisabled}>
        <TrashBinSolid class="inline mr-1"/>
        Delete
      </Button>
      <CloseButton onclick={deselect_all_jobs}/>
    </div>
  </Banner>
</CenterPage>

<ConfirmModal bind:open={abortModalOpen} action={() => abortJobs(abortModalJobs)} post_action={() => postAbortJobs(abortModalJobs)}>
  {#if abortModalJobs.length === 1}
    Job {abortModalJobs[0].toString()} will be aborted and its current transcription progress will be lost.
  {:else}
    The jobs {abortModalJobs.join(", ")} will be aborted and their current transcription progress will be lost.
  {/if}
</ConfirmModal>

<ConfirmModal bind:open={deleteModalOpen} action={() => deleteJobs(deleteModalJobs)}>
  {#if deleteModalJobs.length === 1}
    Job {deleteModalJobs[0].toString()} including its audio file and transcription file will be deleted.
  {:else}
    The jobs {deleteModalJobs.join(", ")} including their audio files and transcription files will be deleted.
  {/if}
</ConfirmModal>

<SubmitJobsModal bind:open={submitModalOpen} pre_filled_in_settings={pre_filled_job_settings} pre_action={async () => reloadSSEListeners()}/>

<DownloadTranscriptModal bind:open={downloadModalOpen} job_id={downloadJobId} job_file_name={downloadFileName} post_action={async () => await update_jobs([downloadJobId])}/>
