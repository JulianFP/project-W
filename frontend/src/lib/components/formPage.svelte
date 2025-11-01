<script lang="ts">
	import { Heading } from "flowbite-svelte";
	import { ArrowLeftOutline } from "flowbite-svelte-icons";

	import Button from "./button.svelte";

	let { backButtonUri, heading, children } = $props();
</script>

<div class="mx-auto max-w-lg">
  {#if backButtonUri}
    <Button class="mb-3" size="xs" color="alternative" type="button" href={backButtonUri}><ArrowLeftOutline class="me-2 h-4 w-4"/>Back</Button>
  {/if}
  <Heading tag="h2" class="text-xl sm:text-2xl md:text-3xl mb-8">{heading}</Heading>
</div>
{@render children?.()}
