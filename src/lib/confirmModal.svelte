<script lang="ts">
import { Heading, Modal, P } from "flowbite-svelte";

import type { BackendResponse } from "$lib/httpRequests";
import WaitingSubmitButton from "./waitingSubmitButton.svelte";

let waitingForPromise = $state(false);

interface Props {
	open?: boolean;
	action: () => Promise<BackendResponse>;
	response?: BackendResponse | null;
	children?: import("svelte").Snippet;
}

let {
	open = $bindable(false),
	action,
	response = $bindable(null),
	children,
}: Props = $props();

async function submitAction(): Promise<void> {
	waitingForPromise = true;
	response = await action();
	open = false;
	waitingForPromise = false;
}
</script>

<Modal bind:open={open} autoclose={false} class="w-fit">
  <Heading tag="h3">Are you sure?</Heading>
  <P>{@render children?.()}</P>
  <WaitingSubmitButton class="w-full1" waiting={waitingForPromise} type="button" on:click={submitAction}>Confirm</WaitingSubmitButton>
</Modal>
