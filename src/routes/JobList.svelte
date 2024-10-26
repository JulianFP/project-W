<script lang="ts">
import {
	Button,
	ButtonGroup,
	Checkbox,
	P,
	Pagination,
	Progressbar,
	Span,
	Spinner,
	TableBody,
	TableBodyCell,
	TableBodyRow,
	TableHead,
	TableHeadCell,
	TableSearch,
	Tooltip,
} from "flowbite-svelte";
import type { LinkType } from "flowbite-svelte";
import {
	CaretDownSolid,
	CaretSortSolid,
	CaretUpSolid,
	ChevronLeftOutline,
	ChevronRightOutline,
	CloseOutline,
	DownloadSolid,
	EditSolid,
	PlusOutline,
	StopSolid,
	TrashBinSolid,
} from "flowbite-svelte-icons";

import CenterPage from "../components/centerPage.svelte";
import ConfirmModal from "../components/confirmModal.svelte";
import ErrorMsg from "../components/errorMsg.svelte";
import SubmitJobsModal from "../components/submitJobsModal.svelte";
import Waiting from "../components/waiting.svelte";
import {
	type BackendResponse,
	type JobStatus,
	getLoggedIn,
	postLoggedIn,
} from "../utils/httpRequests";
import { loginForward } from "../utils/navigation";
import { alerts, loggedIn, routing } from "../utils/stores";

$: if (!$loggedIn) loginForward();

type itemValue = string | number | { step: string; runner: number };
type itemObj = {
	ID: number;
	fileName: string;
	model: string;
	language: string;
	progress: number;
	status: { step: string; runner: number };
	error_msg: string;
};
type itemKey = "ID" | "fileName" | "model" | "language" | "progress" | "status";
//type guard to check if an arbitrary string is an itemKey
function isItemKey(str: string): str is itemKey {
	return ["ID", "fileName", "model", "language", "progress", "status"].includes(
		str,
	);
}

let keys: itemKey[] = ["ID", "fileName", "progress"];

let items: itemObj[] = [];
let jobDownloading: Record<number, boolean> = {};

let submitModalOpen = false;
let abortModalOpen = false;
let abortModalJobs: number[] = [];
let deleteModalOpen = false;
let deleteModalJobs: number[] = [];
let updatingJobList = 0; //0: not updating, 1: updating, 2: error while updating
let updatingJobListError = "";
let fetchedJobs = false;

let tableEditMode = false;
let itemsSelected: Record<number, boolean> = {};
let headerCheckboxSelected = false;
let selectedAbortButtonDisabled = true;
let selectedDeleteButtonDisabled = true;

let searchTerm = "";
let searchTermEdited = false;
let sortKey: itemKey = "ID"; // default sort key
let sortDirection = -1; // default sort direction (descending)
let hideOld = true;
let sortItems: itemObj[] = items.slice(); // make a copy of the items array

let pages: LinkType[] = [];
let page = 1;

let paginationHandlerPlsUnsubsribeMe = false;
let paginationHandlerUnsubscribe = () => {};

let displayItems: itemObj[] = sortItems.slice((page - 1) * 10, page * 10);
let openRow: number | null = null;

let pagesCount = 1; //initialize with 1 since number of items isn't known at this stage anyway

//gets list of all jobIds and call getJobInfo on them
async function getJobs(): Promise<{ msg: string; ok: boolean }> {
	const jobListResponse: BackendResponse = await getLoggedIn("jobs/list");

	if (!jobListResponse.ok) return { msg: jobListResponse.msg, ok: false };
	if (jobListResponse.jobIds == null)
		return { msg: "Couldn't read server response", ok: false };
	if (jobListResponse.jobIds.length === 0) {
		routing.set({ params: {}, overwriteParams: true }); //if there are not jobs then it is just confusing to keep filter querystrings around
		return { msg: "No jobs", ok: true };
	}

	return getJobInfo(jobListResponse.jobIds);
}

//get info of all jobs in jobIds and update items object with them
async function getJobInfo(
	jobIds: number[],
): Promise<{ msg: string; ok: boolean }> {
	updatingJobList = 1;

	const jobInfoResponse: BackendResponse = await getLoggedIn("jobs/info", {
		jobIds: jobIds.toString(),
	});
	if (!jobInfoResponse.ok || jobInfoResponse.jobs == null) {
		updatingJobList = 2;
		updatingJobListError = jobInfoResponse.msg;
		return { msg: jobInfoResponse.msg, ok: false };
	}

	//copy item array to operate on it and the update everything at once
	let tempItems: itemObj[] = items.slice();

	for (const job of jobInfoResponse.jobs) {
		//skip job if it hasn't an id because then it must be invalid
		if (job.jobId == null) continue;

		//copy values from job into item and make sure that every value is defined in the process
		let jobStatus: JobStatus = job.status != null ? job.status : { runner: -1 };
		jobStatus.step = jobStatus.step != null ? jobStatus.step : "notReported";
		jobStatus.runner = jobStatus.runner != null ? jobStatus.runner : -1;

		//make sure that job status "aborted" stays the same until the backend updates it to "failed"
		for (const item of items) {
			if (item.ID === job.jobId) {
				if (
					item.status.step === "aborting" &&
					!["failed", "success", "downloaded"].includes(jobStatus.step)
				)
					jobStatus.step = "aborting";
				break;
			}
		}

		//assign progress values. This is dependent on RUNNER_IN_PROGRESS so that if the user sorts after progress if will also respect the current step
		if (jobStatus.progress == null) {
			switch (jobStatus.step) {
				case "failed":
					jobStatus.progress = -6;
					break;
				case "aborting":
					jobStatus.progress = -5;
					break;
				case "notQueued":
					jobStatus.progress = -3;
					break;
				case "pendingRunner":
					jobStatus.progress = -2;
					break;
				case "runnerAssigned":
					jobStatus.progress = -1;
					break;
				case "runnerInProgress":
					jobStatus.progress = 0;
					break;
				case "success":
				case "downloaded":
					jobStatus.progress = 100;
					break;
				default: //most notably also if step is notReported
					jobStatus.progress = -4;
			}
		} else {
			//multiply by 100 to get it in percent in the table
			jobStatus.progress *= 100;
		}

		const item: itemObj = {
			//insert default values for model and language if they are not present (some of them are already tested above)
			ID: job.jobId,
			fileName: job.fileName != null ? job.fileName : "",
			model: job.model != null ? job.model : "small",
			language: job.language != null ? job.language : "Automatic",
			progress: jobStatus.progress,
			status: {
				step: jobStatus.step,
				runner: jobStatus.runner,
			},
			error_msg: job.error_msg != null ? job.error_msg : "",
		};

		//insert new job into tempItems
		//push if it is new, replace it if not
		let pos = -1;
		for (let i = 0; i < tempItems.length; i++) {
			if (tempItems[i].ID === item.ID) pos = i;
		}
		if (pos === -1) tempItems.push(item);
		else tempItems[pos] = item;
	}

	items = tempItems;

	updatingJobList = 0;
	fetchedJobs = true;
	return { msg: jobInfoResponse.msg, ok: true };
}

async function downloadTranscript(item: itemObj): Promise<void> {
	jobDownloading[item.ID] = true;

	const downloadTranscriptResponse: BackendResponse = await getLoggedIn(
		"jobs/downloadTranscript",
		{ jobId: item.ID.toString() },
	);
	if (
		!downloadTranscriptResponse.ok ||
		downloadTranscriptResponse.transcript == null
	) {
		alerts.add(
			`Could not download transcript of job with ID ${item.ID.toString()}: ${
				downloadTranscriptResponse.msg
			}`,
			"red",
		);
		return;
	}

	//convert transcript to Blob and generate url for it
	const blob = new Blob([downloadTranscriptResponse.transcript], {
		type: "text/plain",
	});
	const url = URL.createObjectURL(blob);

	//create document element with this url and 'click' it
	const element = document.createElement("a");
	element.href = url;
	element.download = `${item.fileName.replace(
		/\.[^/.]+$/,
		"",
	)}_transcribed.txt`;
	element.click();

	jobDownloading[item.ID] = false;
}

async function abortJobs(jobIdsToAbort: number[]): Promise<BackendResponse> {
	//change step of these items to "aborting"
	let originalItems: [itemObj, number][] = [];
	for (let i = 0; i < items.length; i++) {
		if (jobIdsToAbort.includes(items[i].ID)) {
			originalItems.push([structuredClone(items[i]), i]);
			//set item to internal status "aborting", adjusting sorting and delete runner id from it
			items[i].status = {
				step: "aborting",
				runner: -1,
			};
			items[i].progress = -5;
		}
	}

	const jobIdsString = jobIdsToAbort.toString();
	const abortJobsResponse: BackendResponse = await postLoggedIn("jobs/abort", {
		jobIds: jobIdsString,
	});
	if (abortJobsResponse.ok) {
		//after successfully performing action on item exit edit mode
		tableEditMode = false;
	} else {
		alerts.add(
			`Could not abort the jobs with the following IDs: ${jobIdsString}: ${abortJobsResponse.msg}`,
			"red",
		);
		//reset state of items
		for (const tuple of originalItems) {
			items[tuple[1]] = tuple[0];
		}
	}

	return abortJobsResponse;
}

async function deleteJobs(jobIdsToDelete: number[]): Promise<BackendResponse> {
	const jobIdsString = jobIdsToDelete.toString();
	const deleteJobsResponse: BackendResponse = await postLoggedIn(
		"jobs/delete",
		{
			jobIds: jobIdsString,
		},
	);
	if (deleteJobsResponse.ok) {
		//if successful also update local items array
		items = items.filter((item) => {
			return !jobIdsToDelete.includes(item.ID);
		});
		//also deselect items (only if performed through button in header)
		tableEditMode = false;
	} else {
		alerts.add(
			`Could not delete the jobs with the following IDs: ${jobIdsString}: ${deleteJobsResponse.msg}`,
			"red",
		);
	}

	return deleteJobsResponse;
}

function openSubmitModal() {
	if (!submitModalOpen && !abortModalOpen && !deleteModalOpen) {
		submitModalOpen = true;
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

function calcPages(): void {
	pages = [];
	let params = new URLSearchParams($routing.querystring); //copy because it will be modified down below
	for (let i = 1; i <= pagesCount; i++) {
		params.set("page", i.toString());
		params.sort();

		pages.push({
			name: i.toString(),
			href: `#${$routing.location}?${params.toString()}`,
		});
	}
}

function toggleRow(i: number): void {
	openRow = openRow === i ? null : i;
}

// Define a function to sort the items
function sortTable(key: itemKey): void {
	// If the same key is clicked, reverse the sort direction
	if (sortKey === key) {
		sortDirection = -sortDirection;
	} else {
		sortKey = key;
		sortDirection = -1; //default sort direction when clicking on table (ascending)sosreport
	}
	routing.set({ params: { sortkey: key, sortdir: sortDirection.toString() } });
}

function setPage(newNum: number): void {
	if (newNum <= pagesCount && newNum > 0) {
		page = newNum;
		routing.set({ params: { page: newNum.toString() } });
	}
}

function setHideOld(newVal: boolean): void {
	hideOld = newVal;
	if (newVal) routing.set({ params: { hideold: "1" } });
	else routing.set({ params: { hideold: "0" } });
}

function updateHeaderCheckbox(item: itemObj | null = null) {
	//update headerCheckbox
	if (item == null || itemsSelected[item.ID]) {
		let allSelected = true;
		for (let item of displayItems) {
			if (!itemsSelected[item.ID]) {
				allSelected = false;
				break;
			}
		}
		headerCheckboxSelected = allSelected;
	} else {
		headerCheckboxSelected = false;
	}
}

function paginationClickedHandler(): void {
	paginationHandlerUnsubscribe = routing.subscribe((routingObject) => {
		const newPage: string | null = routingObject.querystring.get("page");
		if (newPage != null && newPage !== page.toString()) {
			//update hrefs
			calcPages();

			//update local page variable
			setPage(Number.parseInt(newPage)); //comes from our href, so parsing it as int always works

			paginationHandlerPlsUnsubsribeMe = true;
		}
	});
}

//get values from querystring
{
	const params: URLSearchParams = $routing.querystring;
	let newParams: Record<string, string> = {};

	const newSortKey: string | null = params.get("sortkey");
	if (newSortKey != null) {
		if (isItemKey(newSortKey)) {
			sortKey = newSortKey;
			newParams.sortkey = newSortKey;
		}
	}
	const newSortDir: string | null = params.get("sortdir");
	if (newSortDir != null) {
		const newSortDirInt: number = Number.parseInt(newSortDir);
		if (newSortDirInt === 1 || newSortDirInt === -1) {
			sortDirection = newSortDirInt; //NaN is also unequal to 1 and -1
			newParams.sortdir = newSortDir;
		}
	}
	const newSearch: string | null = params.get("search");
	if (newSearch != null) {
		if (newSearch !== "") {
			searchTerm = newSearch;
			newParams.search = newSearch;
		}
	}
	const newHideOld: string | null = params.get("hideold");
	if (newHideOld != null) {
		if (newHideOld === "0") {
			hideOld = false;
			newParams.hideold = newHideOld;
		} else if (newHideOld === "1") {
			hideOld = true;
			newParams.hideold = newHideOld;
		}
	}
	const newPage: string | null = params.get("page");
	if (newPage != null) {
		let newPageInt = Number.parseInt(newPage);
		if (!Number.isNaN(newPageInt)) {
			//cannot check yet if newPageInt is larger than pagesCount because pagesCount isn't known at this stage yet since getJobs hasn't run yet
			page = newPageInt;
			newParams.page = newPageInt.toString();
		}
	}

	routing.set({
		params: newParams,
		overwriteParams: true,
		ensureLoggedIn: true,
	}); //without ensureLoggedIn this might get called after loginForward resulting in a constant back and forth between Login  and JobList
	calcPages();
}

//update currently displayed entries of table every 15 seconds (-> equal to heartbeat interval of runner)
setInterval(() => {
	if (displayItems.length > 0 && updatingJobList !== 1) {
		let jobIds: number[] = [];
		for (let job of displayItems) {
			jobIds.push(job.ID);
		}
		getJobInfo(jobIds);
	}
}, 15000);

//update pagesCount due to change of amount of items
$: {
	//only do this if the items were already fetched at least once
	if (fetchedJobs) {
		//Math.ceil rounds UP to nearest integer. max ensures that there is always at least one page even though there are no items
		pagesCount = Math.max(Math.ceil(sortItems.length / 10), 1);
		if (page > pagesCount) setPage(pagesCount); //make sure page isn't larger than new pagesCount
		calcPages();
	}
}

$: if (searchTerm || searchTermEdited) {
	routing.set({ params: { search: searchTerm }, ensureLoggedIn: true });
	searchTermEdited = true;
}

$: {
	const key: itemKey = sortKey;
	const direction: number = sortDirection;
	const filteredItems = hideOld
		? items.filter((item) => item.status.step !== "downloaded")
		: items.slice();
	const searchedItems = filteredItems.filter(
		(item) =>
			item.fileName.toLowerCase().indexOf(searchTerm.toLowerCase()) !== -1,
	);
	const sorted = [...searchedItems].sort((a: itemObj, b: itemObj) => {
		const aVal: itemValue = a[key];
		const bVal: itemValue = b[key];
		if (aVal < bVal) {
			return -direction;
		}
		if (aVal > bVal) {
			return direction;
		}
		return 0;
	});
	sortItems = sorted;
}

//after the paginationHandlers subscription set the page variable it should be unsubscribed so that it doesn't get triggered constantly
$: {
	if (paginationHandlerPlsUnsubsribeMe) {
		paginationHandlerUnsubscribe();
		paginationHandlerPlsUnsubsribeMe = false;
	}
}

//update displayItems when sortItems or page gets updated
$: {
	displayItems = sortItems.slice((page - 1) * 10, page * 10);
	updateHeaderCheckbox();
}

$: selectedItems = Object.entries(itemsSelected)
	.filter(([_, v]) => v)
	.map(([k, _]) => Number.parseInt(k));

$: {
	if (selectedItems.length === 0) {
		selectedAbortButtonDisabled = true;
		selectedDeleteButtonDisabled = true;
	} else {
		let includesNotRunning = false;
		let includesNotDone = false;
		for (const item of items) {
			if (selectedItems.includes(item.ID)) {
				if (
					![
						"notQueued",
						"pendingRunner",
						"runnerAssigned",
						"runnerInProgress",
					].includes(item.status.step)
				)
					includesNotRunning = true;
				if (!["success", "downloaded", "failed"].includes(item.status.step))
					includesNotDone = true;
			}
			if (includesNotRunning && includesNotDone) break;
		}
		selectedAbortButtonDisabled = includesNotRunning;
		selectedDeleteButtonDisabled = includesNotDone;
	}
}
</script>

<CenterPage title="Your transcription jobs">
  <div>
    <div class="flex justify-between items-center">
      <Checkbox id="hide_old_elements" bind:checked={hideOld} on:change={() => setHideOld(hideOld)}>Hide old jobs</Checkbox>
      {#if updatingJobList == 1}
        <div>
          <Spinner class="me-3" size="6"/>
          <P class="inline text-gray-900 dark:text-gray-300" size="sm" weight="medium">Updating entries ...</P>
        </div>
      {:else if updatingJobList == 2}
        <P class="inline text-red-700 dark:text-red-500" size="sm" weight="medium">Error during update: {updatingJobListError}</P>
      {/if}
      <Button pill on:click={() => openSubmitModal()}><PlusOutline class="mr-2"/>New Job</Button>
    </div>
      {#await getJobs()}
        <Waiting/>
      {:then response}
        {#if response.ok}
          <TableSearch shadow placeholder="Search by file name" hoverable={true} bind:inputValue={searchTerm}>
            <TableHead>
              {#if tableEditMode}
                <TableHeadCell class="!p-4">
                  <Checkbox class="hover:cursor-pointer" bind:checked={headerCheckboxSelected} on:change={() => {displayItems.forEach((item) => itemsSelected[item.ID] = headerCheckboxSelected)}}/>
                </TableHeadCell>
              {/if}
              {#each keys as key}
                <TableHeadCell class="hover:dark:text-white hover:text-primary-600 hover:cursor-pointer" on:click={() => sortTable(key)}>
                  <div class="flex">
                    {#if sortKey === key}
                      {#if sortDirection === 1}
                        <CaretUpSolid class="inline mr-2"/>
                      {:else}
                        <CaretDownSolid class="inline mr-2"/>
                      {/if}
                    {:else}
                      <CaretSortSolid class="inline mr-2"/>
                    {/if}
                    {key}
                  </div>
                </TableHeadCell>
              {/each}
              <TableHeadCell class="text-center" padding="py-1 pr-4">
                <ButtonGroup class="normal-case">
                  {#if tableEditMode}
                    <Button pill outline class="!p-2" size="xs" color="alternative" on:click={() => openAbortModal(selectedItems)} disabled={selectedAbortButtonDisabled}>
                      <StopSolid class="inline mr-1" color="red"/> {selectedItems.length}
                    </Button>
                    <Tooltip color="red">Abort selected jobs</Tooltip>
                    <Button pill outline class="!p-2" size="xs" color="alternative" on:click={() => openDeleteModal(selectedItems)} disabled={selectedDeleteButtonDisabled}>
                      <TrashBinSolid class="inline mr-1" color="red"/> {selectedItems.length}
                    </Button>
                    <Tooltip color="red">Delete selected jobs</Tooltip>
                    <Button pill outline class="!p-2" size="xs" color="alternative" on:click={() => tableEditMode = false}>
                      <CloseOutline/>
                    </Button>
                  {:else}
                    <Button pill outline class="!p-2" size="xs" color="alternative" on:click={() => {itemsSelected = {}; updateHeaderCheckbox(); tableEditMode = true;}}>
                      <EditSolid/>
                    </Button>
                  {/if}
                </ButtonGroup>
              </TableHeadCell>
            </TableHead>
            <TableBody>
              {#if items.length === 0}
                <TableBodyRow>
                  <TableBodyCell colspan="4">You don't have any jobs yet. <Span underline>Create your first job</Span> by clicking on the <P color="text-primary-600 dark:text-primary-500" weight="bold" size="sm" class="inline">New Job</P> button.</TableBodyCell>
                </TableBodyRow>
              {:else if sortItems.length === 0}
                <TableBodyRow>
                  <TableBodyCell colspan="4">You don't have any current jobs. Deselect <P color="text-primary-600 dark:text-primary-500" weight="bold" size="sm" class="inline">Hide old jobs</P> or <Span underline>create a new job</Span> by clicking on the <P color="text-primary-600 dark:text-primary-500" weight="bold" size="sm" class="inline">New Job</P> button.</TableBodyCell>
                </TableBodyRow>
              {/if}
              {#each displayItems as item, i}
                <TableBodyRow on:click={() => toggleRow(i)}>
                  {#if tableEditMode}
                    <TableBodyCell class="!p-4">
                      <Checkbox class="hover:cursor-pointer" bind:checked={itemsSelected[item.ID]} on:change={() => updateHeaderCheckbox(item)} on:click={(e) => e.stopPropagation()}/>
                    </TableBodyCell>
                  {/if}
                  <TableBodyCell>{item.ID}</TableBodyCell>
                  <TableBodyCell>{(item.fileName.length <= 30) ? item.fileName : `${item.fileName.slice(0,30)}...`}</TableBodyCell>
                  <TableBodyCell tdClass="pl-6 pr-4 py-4 whitespace-nowrap font-medium" class="w-full">
                    {#if (["runnerAssigned", "runnerInProgress"].includes(item.status.step))}
                      <Progressbar precision={2} progress={(item.progress < 0) ? 0 : item.progress} size="h-4" labelInside animate/>
                    {:else if item.status.step === "success"}
                      <Progressbar color="green" precision={2} progress={(item.progress < 0) ? 0 : item.progress} size="h-4" labelInside/>
                    {:else if item.status.step === "failed"}
                      <P class="text-red-700 dark:text-red-500" size="sm">failed - {(item.error_msg.length <= 21) ? item.error_msg : `${item.error_msg.slice(0,21)}...`}</P>
                      <Progressbar color="red" progress={100} size="h-4"/>
                    {:else if item.status.step === "downloaded"}
                      <Progressbar color="indigo" precision={2} progress={(item.progress < 0) ? 0 : item.progress} size="h-4" labelInside/>
                    {:else if item.status.step === "aborting"}
                      <P class="text-red-700 dark:text-red-500" size="sm">aborting...</P>
                      <Progressbar color="yellow" progress={100} size="h-4"/>
                    {:else}
                      <Progressbar color="gray" precision={2} progress={(item.progress < 0) ? 0 : item.progress} size="h-4" labelInside/>
                    {/if}
                  </TableBodyCell>
                  <TableBodyCell tdClass="pr-4 py-4 whitespace-nowrap font-medium text-center">
                    <ButtonGroup>
                      {#if (["notQueued", "pendingRunner", "runnerAssigned", "runnerInProgress"].includes(item.status.step))}
                        <Button pill outline class="!p-2" size="xs" color="alternative" on:click={(e) => {e.stopPropagation(); openAbortModal([item.ID]);}}>

                          <StopSolid color="red"/>
                        </Button>
                        <Tooltip color="red">Abort this job</Tooltip>
                      {:else if (["success", "downloaded", "failed"].includes(item.status.step))}
                        <Button pill outline class="!p-2" size="xs" color="alternative" on:click={(e) => {e.stopPropagation(); openDeleteModal([item.ID]);}}>

                          <TrashBinSolid color="red"/>
                        </Button>
                        <Tooltip color="red">Delete this job</Tooltip>
                      {/if}
                      {#if (["success", "downloaded"].includes(item.status.step))}
                        <Button pill outline class="!p-2" size="xs" color="alternative" on:click={(e) => {e.stopPropagation(); downloadTranscript(item);}} disabled={jobDownloading[item.ID]}>
                          {#if jobDownloading[item.ID]}
                            <Spinner size="5"/>
                          {:else}
                            <DownloadSolid/>
                          {/if}
                        </Button>
                        <Tooltip color="green">Download finished transcript</Tooltip>
                      {/if}
                    </ButtonGroup>
                  </TableBodyCell>
                </TableBodyRow>
                {#if openRow === i}
                  <TableBodyRow color="custom" class="bg-slate-100 dark:bg-slate-700">
                    <TableBodyCell colspan={tableEditMode ? "5" : "4"}>
                      <div class="grid grid-cols-2 gap-x-8 gap-y-2">
                        <div class="col-span-full">
                          <P class="inline" weight="extrabold" size="sm">Filename: </P>
                          <P class="inline" size="sm">{item.fileName}</P>
                        </div>
                        <div>
                          <P class="inline" weight="extrabold" size="sm">Language: </P>
                          <P class="inline" size="sm">{item.language}</P>
                        </div>
                        <div>
                          <P class="inline" weight="extrabold" size="sm">Model: </P>
                          <P class="inline" size="sm">{item.model}</P>
                        </div>
                        <div>
                          <P class="inline" weight="extrabold" size="sm">Current processing step: </P>
                          <P class="inline" size="sm">{item.status.step}</P>
                        </div>
                        {#if (["runnerAssigned", "runnerInProgress"].includes(item.status.step))}
                          <div>
                            <P class="inline" weight="extrabold" size="sm">ID of assigned runner: </P>
                            <P class="inline" size="sm">{item.status.runner}</P>
                          </div>
                        {:else if (item.status.step === "failed")}
                          <div>
                            <P class="inline" weight="extrabold" size="sm">Error message: </P>
                            <P class="inline" size="sm">{item.error_msg}</P>
                          </div>
                        {/if}
                      </div>
                    </TableBodyCell>
                  </TableBodyRow>
                {/if}
              {/each}
            </TableBody>
          </TableSearch>
        {:else}
          <ErrorMsg>{response.msg}</ErrorMsg>
        {/if}
      {/await}
  </div>

  <div class="flex flex-col items-center justify-center gap-2">
    <div class="text-sm text-gray-700 dark:text-gray-400">
      Showing <span class="font-semibold text-gray-900 dark:text-white">{(page-1)*10+1}</span>
      to
      <span class="font-semibold text-gray-900 dark:text-white">{Math.min(page*10, sortItems.length)}</span>
      of
      <span class="font-semibold text-gray-900 dark:text-white">{sortItems.length}</span>
      Entries
    </div>
    <Pagination {pages} on:previous={() => setPage(page-1)} on:next={() => setPage(page+1)} on:click={paginationClickedHandler} icon>
      <svelte:fragment slot="prev">
        <span class="sr-only">Previous</span>
        <ChevronLeftOutline/>
      </svelte:fragment>
      <svelte:fragment slot="next">
        <span class="sr-only">Next</span>
        <ChevronRightOutline/>
      </svelte:fragment>
    </Pagination>
  </div>
</CenterPage>

<SubmitJobsModal bind:open={submitModalOpen} on:afterSubmit={(event) => {getJobInfo(event.detail.jobIds);}}/>

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
