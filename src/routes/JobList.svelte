<script lang="ts">
  import { P, Span, TableSearch, TableBody, TableBodyCell, TableBodyRow, TableHead, TableHeadCell, Pagination, Checkbox, Button, Spinner, Progressbar } from "flowbite-svelte";
  import type { LinkType} from "flowbite-svelte";
  import { CaretSortSolid, CaretUpSolid, CaretDownSolid, ChevronLeftOutline, ChevronRightOutline, PlusOutline, DownloadSolid } from "flowbite-svelte-icons";
  import { querystring, location } from "svelte-spa-router";

  import SubmitJobsModal from "../components/submitJobsModal.svelte";
  import CenterPage from "../components/centerPage.svelte";
  import Waiting from "../components/waiting.svelte";
  import ErrorMsg from "../components/errorMsg.svelte";
  import { alerts, loggedIn } from "../utils/stores";
  import { getLoggedIn } from "../utils/httpRequests";
  import { loginForward } from "../utils/navigation";
  import { setParams, paramsLoc } from "../utils/helperFunctions";

  $: if(!$loggedIn) loginForward();

  //gets list of all jobIds and call getJobInfo on them
  async function getJobs(): Promise<{msg: string, ok: boolean}> {
    const jobListResponse = await getLoggedIn("jobs/list");

    if(!jobListResponse.ok) return {msg: jobListResponse.msg, ok: false};
    if(jobListResponse.jobIds.length === 0) return {msg: "No jobs", ok: true};

    return getJobInfo(jobListResponse.jobIds);
  }

  //get info of all jobs in jobIds and update items object with them
  async function getJobInfo(jobIds: number[]): Promise<{msg: string, ok: boolean}> {
    updatingJobList = 1;

    const jobInfoResponse = await getLoggedIn("jobs/info", {"jobIds": jobIds.toString()});
    if(!jobInfoResponse.ok) {
      updatingJobList = 2;
      updatingJobListError = jobInfoResponse.msg;
      return {msg: jobInfoResponse.msg, ok: false};
    }

    //copy item array to operate on it and the update everything at once
    let tempItems: itemObj[] = items.slice();

    for(let job of jobInfoResponse.jobs){
      //insert default values for model and language
      if(job.model === null) job.model = "small";
      if(job.language === null) job.language = "Automatic";

      //for easier access in table (multiply by 100 to get it in percent)
      job.progress = 100 * job.status.progress;
      delete job.status.progress;

      //assign progress values to steps other than RUNNER_IN_PROGRESS so that a progress bar can always be displayed
      if(!job.progress){
        switch(job.status.step) {
          case "notQueued":
            job.progress = -3;
            break;
          case "pendingRunner":
            job.progress = -2;
            break;
          case "runnerAssigned":
            job.progress = -1;
            break;
          case "runnerInProgress":
          case "failed":
            job.progress = 0;
            break;
          case "success":
          case "downloaded":
            job.progress = 100;
            break;
        }
      }

      //shorten 'jobId' to 'ID'
      job.ID = job.jobId;
      delete job.jobId;

      //insert new job into tempItems
      //push if it is new, replace it if not
      let pos: number = -1;
      for(let i = 0; i < tempItems.length; i++){
        if(tempItems[i].ID === job.ID) pos = i;
      }
      if(pos === -1) tempItems.push(job);
      else tempItems[pos] = job;
    }

    items = tempItems;

    updatingJobList = 0;
    return {msg: jobInfoResponse.msg, ok: true};
  }

  async function downloadTranscript(item: itemObj): Promise<void> {
    jobDownloading[item.ID] = true;

    const downloadTranscriptResponse = await getLoggedIn("jobs/downloadTranscript", {jobId: item.ID.toString()});
    if(!downloadTranscriptResponse.ok){
      alerts.add("Could not download transcript of job with ID " + item.ID.toString() + ": " + downloadTranscriptResponse.msg, "red");
      return;
    }

    //convert transcript to Blob and generate url for it
    const blob = new Blob([downloadTranscriptResponse.transcript], { type: "text/plain"});
    const url = URL.createObjectURL(blob);

    //create document element with this url and 'click' it
    const element = document.createElement('a');
    element.href = url;
    element.download = item.fileName.replace(/\.[^/.]+$/, "") + "_transcribed.txt";
    element.click();

    jobDownloading[item.ID] = false;
  }

  type itemKey = 'ID'|'fileName'|'model'|'language'|'progress'|'status';
  let keys: itemKey[] = ['ID','fileName','progress'];
  type itemValue = string|number;
  type itemObj = {ID: number, fileName: string, model: string, language: string, progress: number, status: {step: string, runner: number}, downloadWaiting: boolean};
  let items: itemObj[] = [];
  let jobDownloading: {[key: number]: boolean} = {};

  let submitModalOpen: boolean = false;
  let updatingJobList: number = 0; //0: not updating, 1: updating, 2: error while updating
  let updatingJobListError: string = "";

  let searchTerm: string = "";
  let searchTermEdited: boolean = false;
  let sortKey: itemKey = 'ID'; // default sort key
  let sortDirection: number = -1; // default sort direction (descending)
  let hideOld: boolean = true;
  let sortItems: itemObj[] = items.slice(); // make a copy of the items array

  //Math.ceil rounds UP to nearest integer
  let pagesCount: number = Math.ceil(sortItems.length / 10);
  $: pagesCount = Math.ceil(sortItems.length / 10);

  let pages: LinkType[] = [];
  function calcPages(): void {
    pages = [];
    for(let i = 1; i <= pagesCount; i++){
      pages.push({name: i.toString(), href: "#" + paramsLoc({"page": i})});
    }
  }
  calcPages();
  let page: number = 1;

  let displayItems: itemObj[] = sortItems.slice((page-1)*10, page*10);

  let openRow: number|null = null;
  function toggleRow(i: number): void {
    openRow = (openRow === i) ? null : i;
  }

  //get values from querystring
  {
    const params: URLSearchParams = new URLSearchParams($querystring);

    if(params.has("sortkey")) sortKey = params.get("sortkey");
    if(params.has("sortdir")) sortDirection = params.get("sortdir");
    if(params.has("search")) searchTerm = params.get("search");
    if(params.has("hideold")) hideOld = Boolean(+params.get("hideold"));
    if(params.has("page")){
      const newPage = Math.min(+params.get("page"), pagesCount);
      page = newPage;
    }
  }

  // Define a function to sort the items
  function sortTable(key: itemKey): void {
    // If the same key is clicked, reverse the sort direction
    if (sortKey === key) {
      sortDirection = -sortDirection;
    } else {
      sortKey = key;
      sortDirection = -1; //default sort direction when clicking on table (ascending)
    }
    setParams({"sortkey": key, "sortdir": sortDirection});
  };

  function setPage(newNum: number): void {
    if(newNum <= pagesCount && newNum > 0){
      page = newNum;
      setParams({"page": newNum});
    }
  }

  function setHideOld(newVal: boolean): void {
    hideOld = newVal;
    if(newVal) setParams({"hideold": 1});
    else setParams({"hideold": 0});
  }

  //update currently displayed entries of table every 15 seconds (-> equal to heartbeat interval of runner)
  setInterval(() => {
    if(displayItems.length > 0 && updatingJobList !== 1){
      let jobIds: number[] = [];
      for(let job of displayItems){
        jobIds.push(job.ID);
      }
      getJobInfo(jobIds);
    }
  }, 15000);

  $: if(searchTerm || searchTermEdited){
    setParams({"search": searchTerm});
    searchTermEdited = true;
  }

  //keep hrefs up to date with querystring
  $: {
    pages = [];
    const params = new URLSearchParams($querystring);
    for(let i = 1; i <= pagesCount; i++){
      params.set("page", ""+i);
      params.sort();

      pages.push({name: i.toString(), href: "#" + $location + "?" + params.toString()});
    }
  }

  //keep local variable up to date after following href link
  $: {
    const params = new URLSearchParams($querystring);
    if(params.has("page")){
      const newPage = Math.min(+params.get("page"), pagesCount);
      page = newPage;
    }
  }

  $: {
    const key: itemKey = sortKey;
    const direction: number = sortDirection;
    const filteredItems = hideOld ? items.filter((item) => item.status.step !== "downloaded") : items.slice();
    const searchedItems = filteredItems.filter((item) => item.fileName.toLowerCase().indexOf(searchTerm.toLowerCase()) !== -1);
    const sorted = [...searchedItems].sort((a: itemObj, b: itemObj) => {
      const aVal: itemValue = a[key];
      const bVal: itemValue = b[key];
      if (aVal < bVal) {
        return -direction;
      } else if (aVal > bVal) {
        return direction;
      }
      return 0;
    });
    sortItems = sorted;
  }

  //update displayItems when sortItems or page gets updated
  $: displayItems = sortItems.slice((page-1)*10, page*10);
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
      <Button pill on:click={() => submitModalOpen = true}><PlusOutline class="mr-2"/>New Job</Button>
    </div>
      {#await getJobs()}
        <Waiting/>
      {:then response}
        {#if response.ok}
          <TableSearch shadow placeholder="Search by file name" hoverable={true} bind:inputValue={searchTerm}>
            <TableHead> 
              {#each keys as key}
                <TableHeadCell class="hover:dark:text-white hover:text-primary-600 hover:cursor-pointer" on:click={() => sortTable(key)}>
                  <div class="flex">
                    {#if sortKey === key}
                      {#if +sortDirection === 1}
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
              <TableHeadCell/>
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
                <TableBodyRow on:click={() => toggleRow(i)} class="cursor-pointer">
                  <TableBodyCell>{item.ID}</TableBodyCell>
                  <TableBodyCell>{(item.fileName.length <= 30) ? item.fileName : item.fileName.slice(0,30) + "..."}</TableBodyCell>
                  <TableBodyCell class="w-full">
                    {#if item.status.step === "runnerInProgress"}
                      <Progressbar precision={2} progress={(item.progress < 0) ? 0 : item.progress} size="h-4" labelInside animate/>
                    {:else if item.status.step === "success"}
                      <Progressbar color="green" precision={2} progress={(item.progress < 0) ? 0 : item.progress} size="h-4" labelInside/>
                    {:else if item.status.step === "failed"}
                      <Progressbar color="red" precision={2} progress={(item.progress < 0) ? 0 : item.progress} size="h-4" labelInside/>
                    {:else if item.status.step === "downloaded"}
                      <Progressbar color="indigo" precision={2} progress={(item.progress < 0) ? 0 : item.progress} size="h-4" labelInside/>
                    {:else}
                      <Progressbar color="gray" precision={2} progress={(item.progress < 0) ? 0 : item.progress} size="h-4" labelInside/>
                    {/if}
                  </TableBodyCell>
                  <TableBodyCell tdClass="pr-6 py-4 whitespace-nowrap font-medium">
                    <Button size="xs" color="alternative" 
                    disabled={!(item.status.step === "success" || item.status.step === "downloaded") || jobDownloading[item.ID]} 
                    on:click={() => downloadTranscript(item)}>
                      {#if jobDownloading[item.ID]}
                        <Spinner size="5"/>
                      {:else} 
                        <DownloadSolid/>
                      {/if}
                    </Button>
                  </TableBodyCell>
                </TableBodyRow>
                {#if openRow === i}
                  <TableBodyRow color="custom" class="bg-slate-100 dark:bg-slate-700">
                    <TableBodyCell colspan="4">
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
                        {#if item.status.runner}
                        <div>
                          <P class="inline" weight="extrabold" size="sm">ID of assigned runner: </P>
                          <P class="inline" size="sm">{item.status.runner}</P>
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
    <Pagination {pages} on:previous={() => setPage(+page-1)} on:next={() => setPage(+page+1)} icon>
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
