<script lang="ts">
	import { Heading, P } from "flowbite-svelte";
	import CenterPage from "$lib/components/centerPage.svelte";

	import type { components } from "$lib/utils/schema";

	type Data = {
		about: components["schemas"]["AboutResponse"];
	};
	interface Props {
		data: Data;
	}
	let { data }: Props = $props();
</script>

<CenterPage title="Terms of Services">
  <div class="flex flex-col gap-4">
    <P>These are the terms of services that are in place on this Project-W instance:</P>
    {#each Object.values(data.about.terms_of_services) as tos}
      <div>
        <Heading tag="h3">{tos.name} (v{tos.version})</Heading>
        <div class="flowbite-anchors text-gray-900 dark:text-white my-2">
          {@html tos.tos_html}
        </div>
      </div>
    {/each}
  </div>
</CenterPage>
