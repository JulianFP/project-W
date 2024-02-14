<script lang="ts">
  import { Modal, Helper, Heading, P } from "flowbite-svelte";

  import PasswordField from "./passwordField.svelte";
  import WaitingSubmitButton from "./waitingSubmitButton.svelte";

  async function submitAction(event: Event): Promise<void> {
    waitingForPromise = true;
    event.preventDefault();

    response = await action();

    if(!response.ok && response.errorType === "auth"){
      error = true;
    }
    else open = false;

    waitingForPromise = false;
  }

  let waitingForPromise: boolean = false;
  let error: boolean = false;

  export let open: boolean = false;
  export let value: string;
  export let action: () => Promise<{[key: string]: any}>;
  export let response: {[key: string]: any};
</script>

<Modal bind:open={open} autoclose={false} class="w-fit">
  <form class="flex flex-col space-y-6" on:submit={submitAction}>
    <Heading tag="h3">Confirm by entering your password</Heading>
    <P><slot/></P>
    <PasswordField bind:value={value} bind:error={error}/>
    <WaitingSubmitButton class="w-full1" waiting={waitingForPromise} disabled={error}>Confirm</WaitingSubmitButton>

    {#if error}
      <Helper class="mt-2" color="red"><span class="font-medium"></span> {response.msg}</Helper>
    {/if}
  </form>
</Modal>
