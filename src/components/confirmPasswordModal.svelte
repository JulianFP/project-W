<script lang="ts">
  import { Modal, Helper } from "flowbite-svelte";

  import PasswordField from "./passwordField.svelte";
  import WaitingSubmitButton from "./waitingSubmitButton.svelte";

  async function submitAction(event: Event): Promise<void> {
    waitingForPromise = true;
    event.preventDefault();

    response = await action();

    if(!response.ok && response.errorType === "incorrectPassword"){
      error = true;
    }
    else open = false;

    waitingForPromise = false;
  }

  let waitingForPromise = false;
  let error: boolean = false;

  export let open: boolean = false;
  export let value: string;
  export let action: () => Promise<{[key: string]: any}>;
  export let response: {[key: string]: any};
</script>

<Modal bind:open={open} size="xs" autoclose={false} class="w-full">
  <form class="flex flex-col space-y-6" on:submit={submitAction}>
    <h3 class="mb-4 text-xl font-medium text-gray-900 dark:text-white">Confirm by entering your password</h3>
    <PasswordField bind:value={value} bind:error={error}/>
    <WaitingSubmitButton class="w-full1" waiting={waitingForPromise} disabled={error}>Confirm</WaitingSubmitButton>

    {#if error}
      <Helper class="mt-2" color="red"><span class="font-medium"></span> {response.msg}</Helper>
    {/if}
  </form>
</Modal>
