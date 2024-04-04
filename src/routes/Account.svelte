<script lang="ts">
  import { Alert, Button, Helper } from "flowbite-svelte";

  import Waiting from "../components/waiting.svelte";
  import ChangeEmailField from "../components/changeEmailField.svelte";
  import ConfirmPasswordModal from "../components/confirmPasswordModal.svelte";
  import CenterPage from "../components/centerPage.svelte";
  import WaitingSubmitButton from "../components/waitingSubmitButton.svelte";
  import { getLoggedIn, postLoggedIn } from "./../utils/httpRequests";
  import { authHeader, loggedIn } from "../utils/stores";
  import { loginForward } from "../utils/navigation";
  import { alerts } from "../utils/stores";
    import ErrorMsg from "../components/errorMsg.svelte";

  $: if(!$loggedIn) loginForward();

  async function postDeleteUser(): Promise<{[key: string]: any}> {
    return postLoggedIn("users/delete", {"password": password});
  }

  async function getResendEmail(): Promise<void> {
    waitingForResend = true;
    resendError = false;

    resendResponse = await getLoggedIn("users/resendActivationEmail");

    if(!resendResponse.ok) resendError = true;
    else alerts.add(resendResponse.msg, "green");

    waitingForResend = false;
  }

  //post modal code
  $: if(!modalOpen && Object.keys(deleteResponse).length !== 0){
    if(deleteResponse.status === 200){
      alerts.add(deleteResponse.msg, "green");
      authHeader.forgetToken();
      loginForward();
    }
    else{
      deleteErrorMsg = deleteResponse.msg;
      deleteError = true;
    }
    password = "";
    deleteResponse = {};
  }

  let waitingForResend: boolean = false;
  let resendResponse: {[key: string]: any};
  let resendError: boolean = false;

  let password: string;
  let deleteError: boolean = false;
  let deleteErrorMsg: string;
  let modalOpen: boolean = false;
  let deleteResponse: {[key: string]: any} = {};
</script>

<CenterPage title="Account settings">
{#await getLoggedIn("users/info")}
  <Waiting/>
{:then userinfoResponse} 
  {#if userinfoResponse.status !== 200}
    <ErrorMsg>{userinfoResponse.msg}</ErrorMsg>
  {:else}
    {#if !userinfoResponse.activated}
      <div>
        <Alert class="border-t-4" color="red" dismissable>
          <span class="font-medium">Account not activated!</span>
          To activate your account please confirm your email address by clicking on the link in the mail you got from us.
          <WaitingSubmitButton slot="close-button" size="xs" class="ms-auto" waiting={waitingForResend} type="button" on:click={getResendEmail}>Resend email</WaitingSubmitButton>
        </Alert>
        {#if resendError}
          <Helper class="mt-2" color="red">{resendResponse.msg}</Helper>
        {/if}
      </div>
    {:else}
      <Alert class="border-t-4" color="green">
        <span class="font-medium">Account active!</span>
        Your email address is confirmed.
      </Alert>
    {/if}
    <Alert class="border-t-4" color="dark">
      {userinfoResponse.isAdmin ? "This is an admin account." : "This is a non-admin account."}
    </Alert>

    <ChangeEmailField defaultValue={userinfoResponse.email}/>

    <Button outline color="red" on:click={() => {modalOpen = true;}}>Delete account</Button>
  {/if}
{/await}
</CenterPage>

<ConfirmPasswordModal bind:open={modalOpen} bind:value={password} bind:response={deleteResponse} action={postDeleteUser}>
  Do you really want to delete your account? By doing this you will loose all data attached to this account. This process is not reversible. If signups are disabled on this server then you might not be able to create another account.
</ConfirmPasswordModal>
