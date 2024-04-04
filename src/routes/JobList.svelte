<script lang="ts">
  import { P, TableSearch, TableBody, TableBodyCell, TableBodyRow, TableHead, TableHeadCell, Pagination, Checkbox, Button, Progressbar } from "flowbite-svelte";
  import type { LinkType} from "flowbite-svelte";
  import { CaretSortSolid, CaretUpSolid, CaretDownSolid, ChevronLeftOutline, ChevronRightOutline, PlusSolid } from "flowbite-svelte-icons";
  import { querystring, location } from "svelte-spa-router";

  import SubmitJobsModal from "../components/submitJobsModal.svelte";
  import CenterPage from "../components/centerPage.svelte";
  import { loggedIn } from "../utils/stores";
  import { getLoggedIn } from "../utils/httpRequests";
  import { loginForward } from "../utils/navigation";
  import { setParams, paramsLoc } from "../utils/helperFunctions";
    import Waiting from "../components/waiting.svelte";
    import ErrorMsg from "../components/errorMsg.svelte";

  $: if(!$loggedIn) loginForward();

  async function getJobs(): Promise<{msg: string, ok: boolean}> {
    const jobListResponse = await getLoggedIn("jobs/list");
    if(!jobListResponse.ok) return {msg: jobListResponse.msg, ok: false};

    const jobInfoResponse = await getLoggedIn("jobs/info", {"jobIds": jobListResponse.jobIds.toString()});
    if(!jobInfoResponse.ok) return {msg: jobInfoResponse.msg, ok: false};

    for(let job of jobInfoResponse.jobs){
      //insert default values for model and language
      if(job.model === null) job.model = "small";
      if(job.language === null) job.language = "Automatic";

      //for easier access in table
      job.progress = job.status.progress;
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
    }
    items = jobInfoResponse.jobs;

    return {msg: jobInfoResponse.msg, ok: true};
  }

  type itemKey = 'ID'|'fileName'|'model'|'language'|'progress'|'status';
  let keys: itemKey[] = ['ID','fileName','progress'];
  type itemValue = string|number;
  type itemObj = {ID: number, fileName: string, model: string, language: string, progress: number, status: {step: string, runner: number}};
  let items: itemObj[] = [];

  let submitModalOpen: boolean = false;

  let searchTerm: string = "";
  let searchTermEdited: boolean = false;
  let sortKey: itemKey = 'ID'; // default sort key
  let sortDirection: number = -1; // default sort direction (descending)
  let hideOld: boolean = true;
  let sortItems: itemObj[] = items.slice(); // make a copy of the items array

  let pagesCount: number = Math.round(sortItems.length / 10 + 0.5);
  $: pagesCount = Math.round(sortItems.length / 10 + 0.5);

  let pages: LinkType[] = [];
  function calcPages(): void {
    pages = [];
    for(let i = 1; i <= pagesCount; i++){
      pages.push({name: i.toString(), href: "#" + paramsLoc({"page": i})});
    }
  }
  calcPages();
  let page: number = 1;

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
      sortDirection = 1;
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
</script>

<CenterPage title="Your transcription jobs">
  <div>
    <div class="flex justify-between">
      <Checkbox id="hide_old_elements" bind:checked={hideOld} on:change={() => setHideOld(hideOld)}>Hide old jobs</Checkbox>
      <Button pill on:click={() => submitModalOpen = true}><PlusSolid class="mr-2"/>New Job</Button>
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
            </TableHead>
            <TableBody>
              {#each sortItems.slice((page-1)*10, page*10) as item, i}
                <TableBodyRow on:click={() => toggleRow(i)} class="cursor-pointer">
                  <TableBodyCell>{item.ID}</TableBodyCell>
                  <TableBodyCell>{item.fileName}</TableBodyCell>
                  <TableBodyCell class="w-full">
                    {#if item.status.step === "runnerInProgress"}
                      <Progressbar precision={2} progress={(item.progress < 0) ? 0 : item.progress} size="h-4" labelInside/>
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
                </TableBodyRow>
                {#if openRow === i}
                  <TableBodyRow color="custom" class="bg-slate-100 dark:bg-slate-700">
                    <TableBodyCell colspan="3">
                      <div class="grid grid-cols-2 gap-x-8 gap-y-2">
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

<SubmitJobsModal bind:open={submitModalOpen}/>
