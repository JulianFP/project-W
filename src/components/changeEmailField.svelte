<script lang="ts">
  import { Input, Label, Helper, Button } from "flowbite-svelte";
  import { LockSolid, LockOpenSolid } from "flowbite-svelte-icons";
  import { push, location } from "svelte-spa-router";

  import ConfirmPasswordModal from "./confirmPasswordModal.svelte";
  import { postLoggedIn } from "../utils/httpRequests";
  import { alerts } from "../utils/stores";

  function toggleLock(): void {
    email = defaultValue;
    lockedInput = !lockedInput;
  }

  async function postChangeUserEmail(): Promise<{[key: string]: any}> {
    promise =  postLoggedIn("changeUserEmail", {"password": password, "newEmail": email});
    return promise;
  }

  //post modal code
  $: if(!modalOpen && response){
    if(response.status === 200) alerts.add(response.msg, "green");
    else error = true;
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
  let promise: Promise<{[key: string]: any}>;
  let error: boolean = false;
  let modalOpen: boolean = false;
  let response: {[key: string]: any};
</script>

<form on:submit={() => {modalOpen = true}}>
  <Label for="email" color={error ? "red" : "gray"} class="mb-2">Email address</Label>
  <Input type="email" id="email" name="email" autocomplete="email" color={error ? "red" : "base"} required on:input={() => {error = false}} bind:value={email} readonly={lockedInput || null} {...$$restProps}>
    <button type="button" slot="left" class="pointer-events-auto" on:click={toggleLock}>
      {#if lockedInput}
        <LockSolid class="w-6 h-6"/>
      {:else}
        <LockOpenSolid class="w-6 h-6"/>
      {/if}
    </button>
    <Button slot="right" size="sm" disabled={disabledSubmit} on:click={() => {modalOpen = true;}}>Change Email</Button>
  </Input>
  {#if error}
    <Helper class="mt-2" color="red"><span class="font-medium"></span> {response.msg}</Helper>
  {/if}
</form>

<ConfirmPasswordModal bind:open={modalOpen} bind:value={password} bind:response={response} action={postChangeUserEmail}/>
