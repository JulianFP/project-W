<script lang="ts">
import { Alert, Button, Helper } from "flowbite-svelte";

import CenterPage from "../components/centerPage.svelte";
import ChangeEmailField from "../components/changeEmailField.svelte";
import ConfirmPasswordModal from "../components/confirmPasswordModal.svelte";
import ErrorMsg from "../components/errorMsg.svelte";
import Waiting from "../components/waiting.svelte";
import WaitingSubmitButton from "../components/waitingSubmitButton.svelte";
import { loginForward } from "../utils/navigation";
import { authHeader, loggedIn } from "../utils/stores";
import { alerts } from "../utils/stores";
import {
	type BackendResponse,
	getLoggedIn,
	postLoggedIn,
} from "./../utils/httpRequests";

let waitingForResend = false;
let resendResponse: BackendResponse;
let resendError = false;

let password: string;
let deleteError = false;
let deleteErrorMsg: string;
let modalOpen = false;
let deleteResponse: BackendResponse | null = null;

$: if (!$loggedIn) loginForward();

async function postDeleteUser(): Promise<BackendResponse> {
	return postLoggedIn("users/delete", { password: password });
}

async function getResendEmail(): Promise<void> {
	waitingForResend = true;
	resendError = false;

	resendResponse = await getLoggedIn("users/resendActivationEmail");

	if (!resendResponse.ok) resendError = true;
	else alerts.add(resendResponse.msg, "green");

	waitingForResend = false;
}

//post modal code
$: if (!modalOpen && deleteResponse != null) {
	if (deleteResponse.ok) {
		alerts.add(deleteResponse.msg, "green");
		authHeader.forgetToken();
		loginForward();
	} else {
		deleteErrorMsg = deleteResponse.msg;
		deleteError = true;
	}
	password = "";
	deleteResponse = null;
}
</script>

<CenterPage title="Account settings">
{#await getLoggedIn("users/info")}
  <Waiting/>
{:then userinfoResponse}
  {#if !userinfoResponse.ok}
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

    <ChangeEmailField defaultValue={userinfoResponse.email ?? "Error: Response didn't contain email address"}/>

    <Button outline color="red" on:click={() => {modalOpen = true;}}>Delete account</Button>
  {/if}
{/await}
</CenterPage>

<ConfirmPasswordModal bind:open={modalOpen} bind:value={password} bind:response={deleteResponse} action={postDeleteUser}>
  Do you really want to delete your account? By doing this you will loose all data attached to this account. This process is not reversible. If signups are disabled on this server then you might not be able to create another account.
</ConfirmPasswordModal>
