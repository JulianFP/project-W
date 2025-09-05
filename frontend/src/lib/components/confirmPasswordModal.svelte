<script lang="ts">
import { Helper, Modal, P } from "flowbite-svelte";

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

async function submitAction(): Promise<void> {
	waitingForPromise = true;
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

function onAction(params: { action: string; data: FormData }): boolean {
	if (params.action === "submit") {
		submitAction();
	}
	return false;
}
</script>

<Modal form title="Confirm by entering your password" bind:open={open} onaction={onAction} class="w-fit">
  <P>{@render children?.()}</P>
  <PasswordField bind:value={value} bind:error={error}>Your password</PasswordField>
  {#if error}
    <Helper color="red">{errorMsg}</Helper>
  {/if}
  <WaitingSubmitButton value="submit" class="w-full" waiting={waitingForPromise}>Confirm</WaitingSubmitButton>
</Modal>
