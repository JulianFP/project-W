<script lang="ts">
  import { TableSearch, TableBody, TableBodyCell, TableBodyRow, TableHead, TableHeadCell, Pagination, Checkbox, Button } from "flowbite-svelte";
  import { CaretSortSolid, CaretUpSolid, CaretDownSolid, ChevronLeftOutline, ChevronRightOutline, PlusSolid } from "flowbite-svelte-icons";
  import { querystring, location } from "svelte-spa-router";

  import CenterPage from "../components/centerPage.svelte";
  import { loggedIn } from "../utils/stores";
  import { loginForward } from "../utils/navigation";
  import { setParams, paramsLoc } from "../utils/helperFunctions";

  $: if(!$loggedIn) loginForward();

  type itemKey = 'id'|'fileName'|'model'|'language'|'status';
  let keys: itemKey[] = ['id','fileName','model','language','status'];
  type itemValue = string|number;
  type itemObj = {id: number, fileName: string, model: string, language: string, status: string};
  let items: itemObj[] = [
    { id: 1, fileName: 'lecture.mp3', model: 'base', language: 'German', status: 'pending_runner' },
    { id: 2, fileName: 'interview.mp3', model: 'medium.en', language: 'English', status: 'runner_in_progress' },
    { id: 3, fileName: 'lightning_talk.m4a', model: 'tiny.en', language: 'English', status: 'success' },
    { id: 4, fileName: 'random_noise.aac', model: 'large', language: 'Finnish', status: 'failed' },
    { id: 5, fileName: 'lecture.mp3', model: 'base', language: 'German', status: 'pending_runner' },
    { id: 6, fileName: 'interview.mp3', model: 'medium.en', language: 'English', status: 'runner_in_progress' },
    { id: 7, fileName: 'lightning_talk.m4a', model: 'tiny.en', language: 'English', status: 'success' },
    { id: 8, fileName: 'random_noise.aac', model: 'large', language: 'Finnish', status: 'failed' },
    { id: 9, fileName: 'lecture.mp3', model: 'base', language: 'German', status: 'pending_runner' },
    { id: 10, fileName: 'interview.mp3', model: 'medium.en', language: 'English', status: 'runner_in_progress' },
    { id: 11, fileName: 'lightning_talk.m4a', model: 'tiny.en', language: 'English', status: 'success' },
    { id: 12, fileName: 'random_noise.aac', model: 'large', language: 'Finnish', status: 'failed' },
    { id: 13, fileName: 'lecture.mp3', model: 'base', language: 'German', status: 'pending_runner' },
    { id: 14, fileName: 'interview.mp3', model: 'medium.en', language: 'English', status: 'runner_in_progress' },
    { id: 15, fileName: 'lightning_talk.m4a', model: 'tiny.en', language: 'English', status: 'success' },
    { id: 16, fileName: 'random_noise.aac', model: 'large', language: 'Finnish', status: 'failed' },
    { id: 17, fileName: 'old_file.mp3', model: 'large', language: 'English', status: 'downloaded' },
    { id: 18, fileName: 'last_christmas.aac', model: 'large', language: 'German', status: 'downloaded' },
    { id: 19, fileName: 'holiday.m4a', model: 'large', language: 'German', status: 'downloaded' },
    { id: 20, fileName: 'holiday2.m4a', model: 'large', language: 'German', status: 'downloaded' },
    { id: 21, fileName: 'birthdayParty.m4a', model: 'large', language: 'German', status: 'downloaded' }
  ];

  let searchTerm: string = "";
  let sortKey: itemKey = 'id'; // default sort key
  let sortDirection: number = 1; // default sort direction (ascending)
  let hideOld: boolean = true;
  let sortItems: itemObj[] = items.slice(); // make a copy of the items array

  let pagesCount: number = Math.round(sortItems.length / 10 + 0.5);
  $: pagesCount = Math.round(sortItems.length / 10 + 0.5);

  let pages: {name: number, href: string}[] = [];
  function calcPages(): void {
    pages = [];
    for(let i = 1; i <= pagesCount; i++){
      pages.push({name: i, href: "#" + paramsLoc({"page": i})});
    }
  }
  calcPages();
  let page: number = 1;

  //get values from querystring
  {
    const params = new URLSearchParams($querystring);

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

  $: setParams({"search": searchTerm});

  //keep hrefs up to date with querystring
  $: {
    pages = [];
    const params = new URLSearchParams($querystring);
    for(let i = 1; i <= pagesCount; i++){
      params.set("page", ""+i);
      params.sort();

      pages.push({name: i, href: "#" + $location + "?" + params.toString()});
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
    const filteredItems = hideOld ? items.filter((item) => item.status !== "downloaded") : items.slice();
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
  <div class="flex justify-between">
    <Checkbox bind:checked={hideOld} on:change={() => setHideOld(hideOld)}>Hide old jobs</Checkbox>
    <Button pill><PlusSolid class="mr-2"/>New Job</Button>
  </div>
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
      {#each sortItems.slice((page-1)*10, page*10) as item}
        <TableBodyRow>
          <TableBodyCell>{item.id}</TableBodyCell>
          <TableBodyCell>{item.fileName}</TableBodyCell>
          <TableBodyCell>{item.model}</TableBodyCell>
          <TableBodyCell>{item.language}</TableBodyCell>
          <TableBodyCell>{item.status}</TableBodyCell>
        </TableBodyRow>
      {/each}
    </TableBody>
  </TableSearch>

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
        <ChevronLeftOutline class="w-2.5 h-2.5" />
      </svelte:fragment>
      <svelte:fragment slot="next">
        <span class="sr-only">Next</span>
        <ChevronRightOutline class="w-2.5 h-2.5" />
      </svelte:fragment>
    </Pagination>

  </div>
</CenterPage>
