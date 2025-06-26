<script lang="ts">
import { invalidate } from "$app/navigation";
import CenterPage from "$lib/components/centerPage.svelte";
import WaitingSubmitButton from "$lib/components/waitingSubmitButton.svelte";
import { BackendCommError, postLoggedIn } from "$lib/utils/httpRequests.svelte";
import type { components } from "$lib/utils/schema";
import { Checkbox, Heading, Helper, P } from "flowbite-svelte";
import type { Snippet } from "svelte";

type Data = {
	about: components["schemas"]["AboutResponse"];
	user_info: components["schemas"]["User"];
};
interface Props {
	data: Data;
	children: Snippet;
}
let { data, children }: Props = $props();

let not_accepted_tos: [string, boolean][] = $state([]);

function reset_not_accepted_tos() {
	not_accepted_tos = [];
	for (let [server_tos_id, server_tos] of Object.entries(
		data.about.terms_of_services,
	)) {
		if (
			!data.user_info.accepted_tos[server_tos_id] ||
			data.user_info.accepted_tos[server_tos_id] < server_tos.version
		) {
			not_accepted_tos.push([server_tos_id, false]);
		}
	}
}
reset_not_accepted_tos();

let waiting: boolean = $state(false);
let error: boolean = $state(false);
let errorMsg: string = $state("");
let enabled = $derived(not_accepted_tos.every(([_, accepted]) => accepted));

async function acceptTos(): Promise<void> {
	waiting = true;
	try {
		for (let [tos_id, selected] of not_accepted_tos) {
			if (selected) {
				await postLoggedIn<string>("users/accept_tos", {}, false, {
					tos_id: tos_id,
					tos_version: data.about.terms_of_services[tos_id].version.toString(),
				});
			}
		}
	} catch (err: unknown) {
		if (err instanceof BackendCommError) {
			errorMsg = err.message;
		} else {
			errorMsg = "Unknown error";
		}
		error = true;
	}
	await invalidate("app:user_info");
	reset_not_accepted_tos();
	waiting = false;
}
</script>
{#if not_accepted_tos.length === 0}
  {@render children()}
{:else}
  <CenterPage title="Terms of Services">
    <form onsubmit={acceptTos} class="flex flex-col gap-6">
      <P>Before you can use this Project-W instance you have to agree to the following terms of services:</P>
      {#each not_accepted_tos as [tos_id,_], i}
        <div>
          <Heading tag="h3">{data.about.terms_of_services[tos_id].name} (v{data.about.terms_of_services[tos_id].version})</Heading>
          <div class="flowbite-anchors text-gray-900 dark:text-white my-2">
            {@html data.about.terms_of_services[tos_id].tos_html}
          </div>
          <Checkbox bind:checked={not_accepted_tos[i][1]} tabindex={i+1}><P>I have read the terms and conditions above ({data.about.terms_of_services[tos_id].name}) and hereby agree to them</P></Checkbox>
        </div>
      {/each}
      {#if error}
        <Helper class="mt-2" color="red"><span class="font-medium">Accepting the terms of services failed:</span> {errorMsg}</Helper>
      {/if}
      <WaitingSubmitButton waiting={waiting} disabled={!enabled} tabindex={not_accepted_tos.length+1}>Confirm</WaitingSubmitButton>
    </form>
  </CenterPage>
{/if}
