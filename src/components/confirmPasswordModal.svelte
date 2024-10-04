<script lang="ts">
import { Heading, Helper, Modal, P } from "flowbite-svelte";

import type { BackendResponse } from "../utils/httpRequests";
import PasswordField from "./passwordField.svelte";
import WaitingSubmitButton from "./waitingSubmitButton.svelte";

let waitingForPromise = false;
let error = false;

export let open = false;
export let value: string;
export let action: () => Promise<BackendResponse>;
export let response: BackendResponse | null;

async function submitAction(event: Event): Promise<void> {
	waitingForPromise = true;
	event.preventDefault();

	response = await action();

	if (!response.ok && response.errorType === "auth") {
		error = true;
	} else open = false;

	waitingForPromise = false;
}
</script>

<Modal bind:open={open} autoclose={false} class="w-fit">
  <form class="flex flex-col space-y-6" on:submit={submitAction}>
    <Heading tag="h3">Confirm by entering your password</Heading>
    <P><slot/></P>
    <PasswordField bind:value={value} bind:error={error}/>
    <WaitingSubmitButton class="w-full1" waiting={waitingForPromise} disabled={error}>Confirm</WaitingSubmitButton>

    {#if error}
      <Helper class="mt-2" color="red"><span class="font-medium"></span> {(response ?? {msg: "Couldn't read server response"}).msg}</Helper>
    {/if}
  </form>
</Modal>
