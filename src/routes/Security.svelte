<script lang="ts">
import { Button, Helper } from "flowbite-svelte";

import CenterPage from "../components/centerPage.svelte";
import ConfirmModal from "../components/confirmModal.svelte";
import ConfirmPasswordModal from "../components/confirmPasswordModal.svelte";
import PasswordWithRepeatField from "../components/passwordWithRepeatField.svelte";
import { type BackendResponse, postLoggedIn } from "../utils/httpRequests";
import { loginForward } from "../utils/navigation";
import { alerts, authHeader, loggedIn } from "../utils/stores";

$: if (!$loggedIn) loginForward();

let password: string;
let newPassword: string;
let passwordError = false;
let genPasswordError = false;
let anyPasswordError: boolean;
let passwordErrorMsg: string;
let passwordModalOpen = false;
let passwordResponse: BackendResponse | null = null;

$: anyPasswordError = passwordError || genPasswordError;

let invalidError = false;
let invalidErrorMsg: string;
let invalidModalOpen = false;
let invalidResponse: BackendResponse | null = null;

function openPasswordModal(event: Event) {
	event.preventDefault();
	passwordModalOpen = true;
}

async function postChangeUserPassword(): Promise<BackendResponse> {
	return postLoggedIn("users/changePassword", {
		password: password,
		newPassword: newPassword,
	});
}

async function postInvalidateAllTokens(): Promise<BackendResponse> {
	return postLoggedIn("users/invalidateAllTokens");
}

//post password modal code
$: if (!passwordModalOpen && passwordResponse != null) {
	if (passwordResponse.ok) alerts.add(passwordResponse.msg, "green");
	else {
		passwordErrorMsg = passwordResponse.msg;
		if (passwordResponse.errorType === "password") passwordError = true;
		else genPasswordError = true;
	}
	password = "";
	passwordResponse = null;
}

//post invalid modal code
$: if (!invalidModalOpen && invalidResponse != null) {
	if (invalidResponse.ok) {
		alerts.add(invalidResponse.msg, "green");
		authHeader.forgetToken();
		loginForward();
	} else {
		invalidErrorMsg = invalidResponse.msg;
		invalidError = true;
	}
	invalidResponse = null;
}
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
