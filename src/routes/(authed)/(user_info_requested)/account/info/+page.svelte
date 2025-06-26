<script lang="ts">
import { Alert, Helper } from "flowbite-svelte";

import Button from "$lib/components/button.svelte";
import CenterPage from "$lib/components/centerPage.svelte";
import ChangeEmailField from "$lib/components/changeEmailField.svelte";
import ConfirmModal from "$lib/components/confirmModal.svelte";
import WaitingSubmitButton from "$lib/components/waitingSubmitButton.svelte";
import { alerts, auth } from "$lib/utils/global_state.svelte";
import {
	BackendCommError,
	deletLoggedIn,
	getLoggedIn,
} from "$lib/utils/httpRequests.svelte";
import type { components } from "$lib/utils/schema";

type Data = {
	user_info: components["schemas"]["User"];
};
interface Props {
	data: Data;
}
let { data }: Props = $props();

let waitingForResend = $state(false);
let resendError = $state(false);
let resendErrorMsg = $state("");

let modalOpen = $state(false);

async function deleteUser() {
	try {
		await deletLoggedIn<null>("users/delete");
		alerts.push({ msg: "User was deleted successfully!", color: "green" });
		auth.forgetToken();
	} catch (err: unknown) {
		let errorMsg = "Error occured during user deletion: ";
		if (err instanceof BackendCommError) {
			errorMsg += err.message;
		} else {
			errorMsg += "Unknown error";
		}
		alerts.push({ msg: errorMsg, color: "red" });
	}
}

async function getResendEmail() {
	waitingForResend = true;
	resendError = false;
	resendErrorMsg = "";

	try {
		let resendResponse = await getLoggedIn<string>(
			"local-account/resend_activation_email",
		);
		alerts.push({ msg: resendResponse, color: "green" });
	} catch (err: unknown) {
		if (err instanceof BackendCommError) {
			resendErrorMsg = err.message;
		} else {
			resendErrorMsg = "Unknown error";
		}
		resendError = true;
	}

	waitingForResend = false;
}
</script>

<CenterPage title="Account settings">
  <Alert class="border-t-4" color="gray">
    {#if data.user_info.user_type === "local"}
      This is a local Project-W account.
    {:else}
      This is an {data.user_info.user_type.toUpperCase()} user from the identity provider {data.user_info.provider_name}
    {/if}
  </Alert>
  {#if data.user_info.user_type === "local"}
    {#if !data.user_info.is_verified}
      <div>
        <Alert class="border-t-4" color="red">
          <span class="font-medium">Account not activated!</span>
          To activate your account please confirm your email address by clicking on the link in the mail you got from us.
          <WaitingSubmitButton size="xs" class="ms-auto" waiting={waitingForResend} type="button" onclick={getResendEmail}>Resend email</WaitingSubmitButton>
        </Alert>
        {#if resendError}
          <Helper class="mt-2" color="red">{resendErrorMsg}</Helper>
        {/if}
      </div>
    {:else}
      <Alert class="border-t-4" color="green">
        <span class="font-medium">Account active!</span>
        Your email address is confirmed.
      </Alert>
    {/if}
  {/if}
  <Alert class="border-t-4" color="gray">
    {data.user_info.is_admin ? "This is an admin account." : "This is a non-admin account."}
  </Alert>

  {#if data.user_info.user_type === "local"}
    <ChangeEmailField defaultValue={data.user_info.email}/>
  {:else}
    <Alert class="border-t-4" color="gray">
      Email address: {data.user_info.email}
    </Alert>
  {/if}

  <Button outline color="red" onclick={() => {modalOpen = true;}}>Delete account</Button>
</CenterPage>

<ConfirmModal bind:open={modalOpen} action={deleteUser}>
  Do you really want to delete your account? By doing this you will loose all data attached to this account. This process is not reversible. If signups are disabled on this server then you might not be able to create another account.
</ConfirmModal>
