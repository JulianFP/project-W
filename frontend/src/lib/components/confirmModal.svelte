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
		post_action?: () => Promise<void>;
		children?: import("svelte").Snippet;
	}

	let {
		open = $bindable(false),
		action,
		post_action = async () => {},
		children,
	}: Props = $props();

	async function submitAction(): Promise<void> {
		waitingForPromise = true;
		await action();
		open = false;
		waitingForPromise = false;
		await post_action();
	}
</script>

<Modal bind:open={open} size="xs" transition={slide} class="text-center">
  <ExclamationCircleOutline class="mx-auto mb-4 h-12 w-12 text-gray-400 dark:text-gray-200" />
  <Heading tag="h3">Are you sure?</Heading>
  <P class="text-center">{@render children?.()}</P>
  <div class="space-x-2">
    <WaitingSubmitButton color="red" class="w-full1" waiting={waitingForPromise} type="button" onclick={submitAction}>Confirm</WaitingSubmitButton>
    <Button color="alternative" onclick={() => open=false}>No, cancel</Button>
  </div>
</Modal>
