<script lang="ts">
import { Input, Range } from "flowbite-svelte";

let { value = $bindable(), min, max, step, id, ...rest } = $props();
</script>

<div class="flex gap-2 items-center">
  <Range class="w-full" bind:value={value} {id} {min} {max} {step} {...rest}/>
  <Input class="min-w-21 w-fit" type="number" id={`${id}_input`} bind:value={value} {min} {max} {step}/>
</div>
