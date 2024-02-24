<script lang="ts">
  import { Input, Label, Helper, Button } from "flowbite-svelte";
  import { LockSolid, LockOpenSolid } from "flowbite-svelte-icons";

  import ConfirmPasswordModal from "./confirmPasswordModal.svelte";
  import { postLoggedIn } from "../utils/httpRequests";
  import { alerts } from "../utils/stores";

  function toggleLock(): void {
    email = defaultValue;
    error = false;
    lockedInput = !lockedInput;
  }

  function openModal(event: Event){
    event.preventDefault();
    modalOpen = true;
  }

  async function postChangeUserEmail(): Promise<{[key: string]: any}> {
    return postLoggedIn("users/changeEmail", {"password": password, "newEmail": email});
  }

  //post modal code
  $: if(!modalOpen && Object.keys(response).length !== 0){
    if(response.status === 200) alerts.add(response.msg, "green");
    else{
      errorMsg = response.msg;
      error = true;
    }
    password = "";
    response = {};
  }

  //make submit only possible if value has changed
  $: {
    if(email === defaultValue) disabledSubmit = true;
    else disabledSubmit = false;
  }

  export let defaultValue: string;

  let lockedInput: boolean = true; 
  let disabledSubmit: boolean;
  let email: string = defaultValue;
  let password: string;
  let error: boolean = false;
  let errorMsg: string;
  let modalOpen: boolean = false;
  let response: {[key: string]: any} = {};
</script>

<form on:submit={openModal}>
  <Label for="email" color={error ? "red" : "gray"} class="mb-2">Email address</Label>
  <Input type="email" id="email" name="email" autocomplete="email" color={error ? "red" : "base"} required on:input={() => {error = false}} bind:value={email} readonly={lockedInput || null} {...$$restProps}>
    <button type="button" slot="left" class="pointer-events-auto" on:click={toggleLock}>
      {#if lockedInput}
        <LockSolid class="w-6 h-6"/>
      {:else}
        <LockOpenSolid class="w-6 h-6"/>
      {/if}
    </button>
    <Button slot="right" size="sm" type="submit" disabled={disabledSubmit||error}>Change Email</Button>
  </Input>
  {#if error}
    <Helper class="mt-2" color="red"><span class="font-medium"></span> {errorMsg}</Helper>
  {/if}
</form>

<ConfirmPasswordModal bind:open={modalOpen} bind:value={password} bind:response={response} action={postChangeUserEmail}>
  You are about to change this accounts email address to {email}. We will send you an email to this address. The actual change of the address will only occur ones you clicked on the link in the email.
</ConfirmPasswordModal>
