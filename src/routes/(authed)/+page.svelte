<script lang="ts">
import {
	A,
	Button,
	ButtonGroup,
	Checkbox,
	P,
	PaginationNav,
	Progressbar,
	Span,
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
	CloseOutline,
	EditSolid,
	PlusOutline,
	StopSolid,
	TrashBinSolid,
} from "flowbite-svelte-icons";

import CenterPage from "$lib/components/centerPage.svelte";
import ConfirmModal from "$lib/components/confirmModal.svelte";
import Waiting from "$lib/components/waiting.svelte";
import { alerts } from "$lib/utils/global_state.svelte";
import {
	BackendCommError,
	deletLoggedIn,
	getLoggedIn,
	postLoggedIn,
} from "$lib/utils/httpRequests.svelte";
import type { components } from "$lib/utils/schema";

type SortKey = components["schemas"]["JobSortKey"];
type Job = components["schemas"]["JobInfo"];

let fetchingJobs = $state(false);
let jobs: Job[] = $state([]);
let job_count: number = $state(0);

//table stuff
const jobs_per_page = 10;
let currentPage = $state(1);
let totalPages = $derived(Math.max(Math.ceil(job_count / jobs_per_page), 1));
let tableEditMode = $state(false);
let itemsSelected: Record<number, boolean> = $state({});
let selectedItems = $derived(
	Object.entries(itemsSelected)
		.filter(([_, v]) => v)
		.map(([k, _]) => Number.parseInt(k)),
);
let headerCheckboxSelected = $state(false);
let selectedAbortButtonDisabled = $state(true);
let selectedDeleteButtonDisabled = $state(true);
let openRow: number | null = $state(null);

$inspect(selectedAbortButtonDisabled);

//modal stuff
let submitModalOpen = $state(false);
let abortModalOpen = $state(false);
let abortModalJobs: number[] = $state([]);
let deleteModalOpen = $state(false);
let deleteModalJobs: number[] = $state([]);

//job query parameters
let sort_key: SortKey = $state("creation_time");
let descending: boolean = $state(true);
let exclude_finished = $state(false);
let exclude_downloaded = $state(true);

async function fetch_jobs() {
	fetchingJobs = true;
	try {
		job_count = await getLoggedIn<number>("jobs/count", {
			exclude_finished: exclude_finished.toString(),
			exclude_downloaded: exclude_downloaded.toString(),
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
			let job_map: Map<number, Job | null> = new Map();
			let args_formatted: string[][] = [];
			for (const job_id of job_ids) {
				job_map.set(job_id, null); //to preserve the ordering of the array
				args_formatted.push(["job_ids", job_id.toString()]);
			}
			const jobs_unsorted = await getLoggedIn<Job[]>(
				"jobs/info",
				args_formatted,
			);
			for (const job of jobs_unsorted) {
				job_map.set(job.id, job);
			}
			jobs = Array.from(job_map.values().filter((job) => job !== null));
		} else {
			jobs = [];
		}
	} catch (err: unknown) {
		let errorMsg = "Error occured while fetching jobs from backend: ";
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

function sortClickHandler(key: SortKey) {
	if (sort_key === key) descending = !descending;
	else sort_key = key;
	fetch_jobs();
}

async function abortJobs(jobIdsToAbort: number[]): Promise<void> {
	try {
		await postLoggedIn("jobs/abort", jobIdsToAbort);
		await fetch_jobs();
		updateHeaderCheckbox();
	} catch (err: unknown) {
		let errorMsg = `Error occured while trying to abort the jobs with ids ${jobIdsToAbort.toString()}: `;
		if (err instanceof BackendCommError) errorMsg += err.message;
		else errorMsg += "Unknown error";
		alerts.push({ msg: errorMsg, color: "red" });
	}
}
async function deleteJobs(jobIdsToAbort: number[]): Promise<void> {
	try {
		await deletLoggedIn("jobs/delete", jobIdsToAbort);
		await fetch_jobs();
		if (jobs.length > 0) {
			updateHeaderCheckbox();
		} else {
			tableEditMode = false;
		}
	} catch (err: unknown) {
		let errorMsg = `Error occured while trying to delete the jobs with ids ${jobIdsToAbort.toString()}: `;
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
		!submitModalOpen
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
		!submitModalOpen
	) {
		deleteModalJobs = jobIds;
		deleteModalOpen = true;
	}
}

function updateHeaderCheckbox(job: Job | null = null) {
	//update headerCheckbox
	if (job == null || itemsSelected[job.id]) {
		let allSelected = true;
		for (let job of jobs) {
			if (!itemsSelected[job.id]) {
				allSelected = false;
				itemsSelected[job.id] = false;
			}
		}
		headerCheckboxSelected = allSelected;
	} else {
		headerCheckboxSelected = false;
	}

	//update disabled states
	if (selectedItems.length === 0) {
		selectedAbortButtonDisabled = true;
		selectedDeleteButtonDisabled = true;
	} else {
		let includesNotRunning = false;
		let includesNotDone = false;
		for (const job of jobs) {
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

function timeAgo(date: Date): string {
	const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);

	let interval = Math.floor(seconds / 31536000);
	if (interval > 1) {
		return `${interval.toString()} years ago`;
	}

	interval = Math.floor(seconds / 2592000);
	if (interval > 1) {
		return `${interval.toString()} months ago`;
	}

	interval = Math.floor(seconds / 86400);
	if (interval > 1) {
		return `${interval.toString()} days ago`;
	}

	interval = Math.floor(seconds / 3600);
	if (interval > 1) {
		return `${interval.toString()} hours ago`;
	}

	interval = Math.floor(seconds / 60);
	if (interval > 1) {
		return `${interval.toString()} minutes ago`;
	}

	if (seconds < 10) return "just now";

	return `${Math.floor(seconds)} seconds ago`;
}
</script>

<CenterPage title="Your transcription jobs">
  <div class="flex flex-col gap-4">
    <div class="flex justify-between items-center">
      <Checkbox id="hide_finished_jobs" bind:checked={exclude_finished} onchange={fetch_jobs}><P>Hide finished jobs</P></Checkbox>
      <Checkbox id="hide_downloaded_jobs" bind:checked={exclude_downloaded} disabled={exclude_finished} onchange={fetch_jobs}><P>Hide downloaded jobs</P></Checkbox>
      <Button pill onclick={() => openSubmitModal()}><PlusOutline class="mr-2"/>New Job</Button>
    </div>
    {#if fetchingJobs}
      <Waiting/>
    {:else}
      <Table shadow hoverable={true}>
        <TableHead>
          {#if tableEditMode}
            <TableHeadCell class="!p-4">
              <Checkbox id="select_all_visible_elements" class="hover:cursor-pointer" bind:checked={headerCheckboxSelected} onchange={() => {jobs.forEach((job) => itemsSelected[job.id] = headerCheckboxSelected); updateHeaderCheckbox();}}/>
            </TableHeadCell>
          {/if}
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
            <ButtonGroup class="normal-case">
              {#if tableEditMode}
                <Button pill outline class="!p-2" size="xs" color="alternative" onclick={() => openAbortModal(selectedItems)} disabled={selectedAbortButtonDisabled}>
                  <StopSolid class="inline mr-1" color="red"/> {selectedItems.length}
                </Button>
                <Button pill outline class="!p-2" size="xs" color="alternative" onclick={() => openDeleteModal(selectedItems)} disabled={selectedDeleteButtonDisabled}>
                  <TrashBinSolid class="inline mr-1" color="red"/> {selectedItems.length}
                </Button>
                <Button pill outline class="!p-2" size="xs" color="alternative" onclick={() => tableEditMode = false}>
                  <CloseOutline/>
                </Button>
              {:else if jobs.length > 0}
                <Button pill outline class="!p-2" size="xs" color="alternative" onclick={() => {tableEditMode = true; itemsSelected = {}; updateHeaderCheckbox();}}>
                  <EditSolid/>
                </Button>
              {/if}
            </ButtonGroup>
          </TableHeadCell>
        </TableHead>
        <TableBody>
          {#if job_count === 0}
            <TableBodyRow>
              <TableBodyCell colspan={tableEditMode ? 5 : 4}>You don't have any jobs yet. <Span underline>Create your first job</Span> by clicking on the <P color="text-primary-600 dark:text-primary-500" weight="bold" size="sm" class="inline">New Job</P> button.</TableBodyCell>
            </TableBodyRow>
          {:else if jobs.length === 0}
            <TableBodyRow>
              <TableBodyCell colspan={tableEditMode ? 5 : 4}>You don't have any current jobs. Deselect <P color="text-primary-600 dark:text-primary-500" weight="bold" size="sm" class="inline">Hide finished jobs</P> or <P color="text-primary-600 dark:text-primary-500" weight="bold" size="sm" class="inline">Hide downloaded jobs</P>, or <Span underline>create a new job</Span> by clicking on the <P color="text-primary-600 dark:text-primary-500" weight="bold" size="sm" class="inline">New Job</P> button.</TableBodyCell>
            </TableBodyRow>
          {/if}
          {#each jobs as job, i}
            <TableBodyRow onclick={() => openRow = openRow === i ? null : i}>
              {#if tableEditMode}
                <TableBodyCell class="!p-4">
                  <Checkbox id="select_job_{job.id}" class="hover:cursor-pointer" bind:checked={itemsSelected[job.id]} onchange={() => updateHeaderCheckbox(job)} onclick={(e) => e.stopPropagation()}/>
                </TableBodyCell>
              {/if}
              <TableBodyCell>
                <P size="sm">{timeAgo(new Date(job.creation_timestamp))}</P>
                <Tooltip type="auto">{job.creation_timestamp}</Tooltip>
              </TableBodyCell>
              <TableBodyCell>
                {#if job.file_name.length > 28}
                  <P size="sm">{`${job.file_name.slice(0,28)}...`}</P>
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
                {:else}
                  <Progressbar color="gray" precision={2} progress={(job.progress < 0) ? 0 : job.progress} size="h-4" labelInside/>
                {/if}
              </TableBodyCell>
              <TableBodyCell class="pr-4 py-4 whitespace-nowrap font-medium text-center">
                <ButtonGroup>
                  {#if (["not_queued", "pending_runner", "runner_assigned", "runner_in_progress"].includes(job.step))}
                    <Button pill outline class="!p-2" size="xs" color="alternative" onclick={(e) => {e.stopPropagation(); openAbortModal([job.id]);}}>

                      <StopSolid color="red"/>
                    </Button>
                  {:else if (["success", "downloaded", "failed"].includes(job.step))}
                    <Button pill outline class="!p-2" size="xs" color="alternative" onclick={(e) => {e.stopPropagation(); openDeleteModal([job.id]);}}>

                      <TrashBinSolid color="red"/>
                    </Button>
                  {/if}
                  {#if (["success", "downloaded"].includes(job.step))}
                    <Button pill outline class="!p-2" size="xs" color="alternative" onclick={(e) => {e.stopPropagation(); downloadTranscript(job);}} disabled={jobDownloading[job.id]}>
                      {#if jobDownloading[job.id]}
                        <Spinner size="5"/>
                      {:else}
                        <DownloadSolid/>
                      {/if}
                    </Button>
                  {/if}
                </ButtonGroup>
              </TableBodyCell>
            </TableBodyRow>
            {#if openRow === i}
              <TableBodyRow color="custom" class="bg-slate-100 dark:bg-slate-700">
                <TableBodyCell colspan={tableEditMode ? 5 : 4}>
                  <div class="grid grid-cols-2 gap-x-8 gap-y-2">
                    <div class="col-span-full">
                      <P class="inline" weight="extrabold" size="sm">Job ID: </P>
                      <P class="inline" size="sm">{job.id}</P>
                    </div>
                    <div>
                      <P class="inline" weight="extrabold" size="sm">Current processing step: </P>
                      <P class="inline" size="sm">{job.step}</P>
                    </div>
                    {#if job.finish_timestamp}
                      <div>
                        <P class="inline" weight="extrabold" size="sm">Finish time: </P>
                        <P class="inline" size="sm">{timeAgo(new Date(job.finish_timestamp))}</P>
                        <Tooltip type="auto">{job.finish_timestamp}</Tooltip>
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
                        <A href={job.runner_source_code_url} target="_blank" rel="noopener noreferrer">Runner source code</A>
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
          {/each}
        </TableBody>
      </Table>
    {/if}
  </div>

  <div class="flex flex-col items-center justify-center gap-2">
    <div class="text-sm text-gray-700 dark:text-gray-400">
      Showing <span class="font-semibold text-gray-900 dark:text-white">{(currentPage-1)*jobs_per_page+(jobs.length === 0 ? 0 : 1)}</span>
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
</CenterPage>

<ConfirmModal bind:open={abortModalOpen} action={() => abortJobs(abortModalJobs)}>
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
