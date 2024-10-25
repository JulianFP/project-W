<script lang="ts">
import { Heading, Modal, P } from "flowbite-svelte";

import type { BackendResponse } from "../utils/httpRequests";
import WaitingSubmitButton from "./waitingSubmitButton.svelte";

let waitingForPromise = false;

export let open = false;
export let action: () => Promise<BackendResponse>;
export let response: BackendResponse | null = null;

async function submitAction(): Promise<void> {
	waitingForPromise = true;
	response = await action();
	open = false;
	waitingForPromise = false;
}
</script>

<Modal bind:open={open} autoclose={false} class="w-fit">
  <Heading tag="h3">Are you sure?</Heading>
  <P><slot/></P>
  <WaitingSubmitButton class="w-full1" waiting={waitingForPromise} type="button" on:click={submitAction}>Confirm</WaitingSubmitButton>
</Modal>
