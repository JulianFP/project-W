<script lang="ts">
import { Heading, Helper, Modal, P } from "flowbite-svelte";

import type { BackendResponse } from "$lib/httpRequests";
import PasswordField from "./passwordField.svelte";
import WaitingSubmitButton from "./waitingSubmitButton.svelte";

let waitingForPromise = $state(false);
let error = $state(false);

interface Props {
	open?: boolean;
	value: string;
	onclose: () => void;
	action: () => Promise<BackendResponse>;
	response: BackendResponse | null;
	children?: import("svelte").Snippet;
}

let {
	open = $bindable(false),
	value = $bindable(),
	action,
	onclose,
	response = $bindable(),
	children,
}: Props = $props();

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

<Modal onclose={onclose} bind:open={open} autoclose={false} class="w-fit">
  <form class="flex flex-col space-y-6" onsubmit={submitAction}>
    <Heading tag="h3">Confirm by entering your password</Heading>
    <P>{@render children?.()}</P>
    <PasswordField bind:value={value} bind:error={error}/>
    <WaitingSubmitButton class="w-full1" waiting={waitingForPromise} disabled={error}>Confirm</WaitingSubmitButton>

    {#if error}
      <Helper class="mt-2" color="red"><span class="font-medium"></span> {(response ?? {msg: "Couldn't read server response"}).msg}</Helper>
    {/if}
  </form>
</Modal>
