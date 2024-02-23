<script lang="ts">
  import { Table, TableBody, TableBodyCell, TableBodyRow, TableHead, TableHeadCell } from "flowbite-svelte";
  import { CaretSortSolid, CaretUpSolid, CaretDownSolid } from "flowbite-svelte-icons";
  import { writable } from "svelte/store";
  import type { Writable } from "svelte/store";

  import CenterPage from "../components/centerPage.svelte";
  import { loggedIn } from "../utils/stores";
  import { loginForward } from "../utils/navigation";

  $: if(!$loggedIn) loginForward();

  type itemKey = 'id'|'fileName'|'model'|'language'|'status';
  let keys: itemKey[] = ['id','fileName','model','language','status'];
  type itemValue = string|number;
  type itemObj = {id: number, fileName: string, model: string, language: string, status: string};
  let items: itemObj[] = [
    { id: 1, fileName: 'lecture.mp3', model: 'base', language: 'German', status: 'pending_runner' },
    { id: 2, fileName: 'interview.mp3', model: 'medium.en', language: 'English', status: 'runner_in_progress' },
    { id: 3, fileName: 'lightning_talk.m4a', model: 'tiny.en', language: 'English', status: 'success' },
    { id: 4, fileName: 'random_noise.aac', model: 'large', language: 'Finnish', status: 'failed' }
  ];

  const sortKey: Writable<itemKey> = writable('id'); // default sort key
  const sortDirection: Writable<number> = writable(1); // default sort direction (ascending)
  const sortItems: Writable<itemObj[]> = writable(items.slice()); // make a copy of the items array

  // Define a function to sort the items
  const sortTable = (key: itemKey) => {
    // If the same key is clicked, reverse the sort direction
    if ($sortKey === key) {
      sortDirection.update((val: number) => -val);
    } else {
      sortKey.set(key);
      sortDirection.set(1);
    }
  };

  $: {
    const key: itemKey = $sortKey;
    const direction: number = $sortDirection;
    const sorted = [...$sortItems].sort((a: itemObj, b: itemObj) => {
      const aVal: itemValue = a[key];
      const bVal: itemValue = b[key];
      if (aVal < bVal) {
        return -direction;
      } else if (aVal > bVal) {
        return direction;
      }
      return 0;
    });
    sortItems.set(sorted);
  }
</script>

<CenterPage title="Your transcription jobs">
<Table shadow>
  <TableHead> 
    {#each keys as key}
      <TableHeadCell class="hover:dark:text-white hover:text-primary-600 hover:cursor-pointer" on:click={() => sortTable(key)}>
        <div class="flex">
          {#if $sortKey === key}
            {#if $sortDirection === 1}
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
    {#each $sortItems as item}
      <TableBodyRow>
        <TableBodyCell>{item.id}</TableBodyCell>
        <TableBodyCell>{item.fileName}</TableBodyCell>
        <TableBodyCell>{item.model}</TableBodyCell>
        <TableBodyCell>{item.language}</TableBodyCell>
        <TableBodyCell>{item.status}</TableBodyCell>
      </TableBodyRow>
    {/each}
  </TableBody>
</Table>
</CenterPage>
