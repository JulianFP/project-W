<script lang="ts">
import { Heading, Helper, Modal, P } from "flowbite-svelte";

import { BackendCommError } from "$lib/utils/httpRequests.svelte";
import PasswordField from "./passwordField.svelte";
import WaitingSubmitButton from "./waitingSubmitButton.svelte";

let waitingForPromise = $state(false);
let errorMsg = $state("");
let error = $state(false);

interface Props {
	open?: boolean;
	value: string;
	onerror: (err: BackendCommError) => void;
	action: () => Promise<void>;
	children?: import("svelte").Snippet;
}

let {
	open = $bindable(false),
	value = $bindable(),
	onerror,
	action,
	children,
}: Props = $props();

async function submitAction(event: Event): Promise<void> {
	waitingForPromise = true;
	event.preventDefault();
	error = false;
	errorMsg = "";

	try {
		await action();
		value = "";
		open = false;
	} catch (err: unknown) {
		if (err instanceof BackendCommError) {
			if (err.status === 403) {
				errorMsg = err.message;
				error = true;
			} else {
				value = "";
				open = false;
				onerror(err);
			}
		} else {
			errorMsg = "Unknown error!";
			error = true;
		}
	}

	waitingForPromise = false;
}
</script>

<Modal bind:open={open} autoclose={false} class="w-fit">
  <form class="flex flex-col space-y-6" onsubmit={submitAction}>
    <Heading tag="h3">Confirm by entering your password</Heading>
    <P>{@render children?.()}</P>
    <PasswordField bind:value={value} bind:error={error}>Your password</PasswordField>
    {#if error}
      <Helper color="red">{errorMsg}</Helper>
    {/if}
    <WaitingSubmitButton class="w-full1" waiting={waitingForPromise}>Confirm</WaitingSubmitButton>
  </form>
</Modal>
