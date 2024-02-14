<script lang="ts">
  import { Modal, Heading, P } from "flowbite-svelte";

  import WaitingSubmitButton from "./waitingSubmitButton.svelte";

  async function submitAction(): Promise<void> {
    waitingForPromise = true;
    response = await action();
    open = false;
    waitingForPromise = false;
  }

  let waitingForPromise: boolean = false;

  export let open: boolean = false;
  export let action: () => Promise<{[key: string]: any}>;
  export let response: {[key: string]: any};
</script>

<Modal bind:open={open} autoclose={false} class="w-fit">
  <Heading tag="h3">Are you sure?</Heading>
  <P><slot/></P>
  <WaitingSubmitButton class="w-full1" waiting={waitingForPromise} type="button" on:click={submitAction}>Confirm</WaitingSubmitButton>
</Modal>
