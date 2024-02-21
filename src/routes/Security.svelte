<script lang="ts">
  import { Button, Helper } from "flowbite-svelte";

  import CenterPage from "../components/centerPage.svelte";
  import PasswordWithRepeatField from "../components/passwordWithRepeatField.svelte";
  import ConfirmPasswordModal from "../components/confirmPasswordModal.svelte";
  import ConfirmModal from "../components/confirmModal.svelte";
  import { getLoggedIn, postLoggedIn } from "../utils/httpRequests";
  import { loggedIn, alerts, authHeader } from "../utils/stores";
  import { loginForward } from "../utils/navigation";

  $: if(!$loggedIn) loginForward();

  function openPasswordModal(event: Event){
    event.preventDefault();
    passwordModalOpen = true;
  }

  
  async function postChangeUserPassword(): Promise<{[key: string]: any}> {
    return postLoggedIn("user/changePassword", {"password": password, "newPassword": newPassword});
  }

  async function postInvalidateAllTokens(): Promise<{[key: string]: any}> {
    return postLoggedIn("user/invalidateAllTokens");
  }

  //post password modal code
  $: if(!passwordModalOpen && Object.keys(passwordResponse).length !== 0){
    if(passwordResponse.status === 200) alerts.add(passwordResponse.msg, "green");
    else{
      passwordErrorMsg = passwordResponse.msg;
      if(passwordResponse.errorType === "password") passwordError = true;
      else genPasswordError = true;
    }
    password = "";
    passwordResponse = {};
  }

  //post invalid modal code 
  $: if(!invalidModalOpen && Object.keys(invalidResponse).length !== 0){
    if(invalidResponse.status === 200){
      alerts.add(invalidResponse.msg, "green");
      authHeader.forgetToken();
      loginForward();
    } 
    else {
      invalidErrorMsg = invalidResponse.msg;
      invalidError = true;
    }
    invalidResponse = {};
  }

  let password: string;
  let newPassword: string;
  let passwordError: boolean = false;
  let genPasswordError: boolean = false;
  let anyPasswordError: boolean;
  let passwordErrorMsg: string;
  let passwordModalOpen: boolean = false;
  let passwordResponse: {[key: string]: any} = {};

  $: anyPasswordError = passwordError || genPasswordError;

  let invalidError: boolean = false;
  let invalidErrorMsg: string;
  let invalidModalOpen: boolean = false;
  let invalidResponse: {[key: string]: any} = {};
</script>

<CenterPage title="Account security">
  <form on:submit={openPasswordModal}>
    <PasswordWithRepeatField bind:value={newPassword} bind:error={passwordError} otherError={genPasswordError} bind:errorMessage={passwordErrorMsg}/>

    {#if anyPasswordError}
      <Helper class="mt-2" color="red">{passwordErrorMsg}</Helper>
    {/if}

    <div class="my-2">
      <Button type="submit" disabled={anyPasswordError}>Change Password</Button>
    </div>
  </form>

  <div>
    <Button outline color="red" class="w-full" on:click={() => {invalidModalOpen = true;}}>Log out all sessions</Button>
    {#if invalidError}
      <Helper class="mt-2" color="red">{invalidErrorMsg}</Helper>
    {/if}
  </div>
</CenterPage>

<ConfirmPasswordModal bind:open={passwordModalOpen} bind:value={password} bind:response={passwordResponse} action={postChangeUserPassword}>
  You are about to change this accounts password. You have to remember your new password in order to login in the future.
</ConfirmPasswordModal>

<ConfirmModal bind:open={invalidModalOpen} bind:response={invalidResponse} action={postInvalidateAllTokens}>
  We will invalidate all your session tokens thus logging you out from all devices (including this). You will have to login again.  
</ConfirmModal>
