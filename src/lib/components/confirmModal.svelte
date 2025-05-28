<script lang="ts">
import { Heading, Modal, P } from "flowbite-svelte";
import { ExclamationCircleOutline } from "flowbite-svelte-icons";
import { slide } from "svelte/transition";

import Button from "./button.svelte";
import WaitingSubmitButton from "./waitingSubmitButton.svelte";

let waitingForPromise = $state(false);

interface Props {
	open?: boolean;
	action: () => Promise<void>;
	children?: import("svelte").Snippet;
}

let { open = $bindable(false), action, children }: Props = $props();

async function submitAction(): Promise<void> {
	waitingForPromise = true;
	await action();
	open = false;
	waitingForPromise = false;
}
</script>

<Modal bind:open={open} size="sm" autoclose={false} transition={slide} class="w-fit">
  <ExclamationCircleOutline class="mx-auto mb-4 h-12 w-12 text-gray-400 dark:text-gray-200" />
  <Heading tag="h3">Are you sure?</Heading>
  <P>{@render children?.()}</P>
  <div class="flex items-end gap-2 w-full">
    <WaitingSubmitButton color="red" class="w-full1" waiting={waitingForPromise} type="button" onclick={submitAction}>Confirm</WaitingSubmitButton>
    <Button color="alternative" onclick={() => open=false}>No, cancel</Button>
  </div>
</Modal>
