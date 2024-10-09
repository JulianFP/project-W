<script lang="ts">
import { P } from "flowbite-svelte";
</script>

<div class="flex flex-col w-full h-full justify-evenly items-center my-8">
  <P color="text-red-700 dark:text-red-500">Error occurred when fetching data: <slot/></P>
</div>
