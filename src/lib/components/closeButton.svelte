<script lang="ts">
import { CloseOutline } from "flowbite-svelte-icons";

let props = $props();
</script>
<button class="text-gray-500 focus:ring-gray-400 hover:bg-gray-200 dark:hover:bg-gray-800 dark:hover:text-gray-300 m-0.5 rounded-lg focus:ring-2 p-2" color="alternative" {...props}>
  <CloseOutline/>
</button>
