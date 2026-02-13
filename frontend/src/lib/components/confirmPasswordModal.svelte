<script lang="ts">
	import { Helper, Modal, P } from "flowbite-svelte";
	import { get_error_msg } from "$lib/utils/http_utils";
	import PasswordField from "./passwordField.svelte";
	import WaitingSubmitButton from "./waitingSubmitButton.svelte";

	let waitingForPromise = $state(false);
	let errorMsg = $state("");
	let errorOccurred = $state(false);

	interface Props {
		open?: boolean;
		value: string;
		onerror: (error: unknown) => void;
		action: () => Promise<{ error: unknown; response: Response }>;
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
		errorOccurred = false;
		errorMsg = "";

		const { error, response } = await action();
		if (error) {
			if (response.status === 403) {
				errorMsg = get_error_msg(error);
				errorOccurred = true;
			} else {
				value = "";
				open = false;
				onerror(error);
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
  <PasswordField bind:value={value} bind:error={errorOccurred}>Your password</PasswordField>
  {#if errorOccurred}
    <Helper color="red">{errorMsg}</Helper>
  {/if}
  <WaitingSubmitButton value="submit" class="w-full" waiting={waitingForPromise}>Confirm</WaitingSubmitButton>
</Modal>
