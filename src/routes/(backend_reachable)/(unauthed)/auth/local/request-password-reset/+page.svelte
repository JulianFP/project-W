<script lang="ts">
import { Helper } from "flowbite-svelte";

import EmailField from "$lib/components/emailField.svelte";
import FormPage from "$lib/components/formPage.svelte";
import WaitingButton from "$lib/components/waitingSubmitButton.svelte";

import { alerts, routing } from "$lib/utils/global_state.svelte";
import { BackendCommError, get } from "$lib/utils/httpRequests.svelte";

let error = $state(false);
let errorMsg = $state("");
let response: string = $state("");
let waitingForPromise = $state(false);
let email: string = $state("");

async function postRequestPasswordReset(event: Event): Promise<void> {
	waitingForPromise = true; //show loading button
	event.preventDefault(); //disable page reload after form submission

	try {
		response = await get<string>("local-account/request_password_reset", {
			email: email,
		});

		alerts.push({ msg: response, color: "green" });
		await routing.set({
			destination: "#/",
			params: {},
			overwriteParams: true,
			history: true,
		});
	} catch (err: unknown) {
		if (err instanceof BackendCommError) {
			errorMsg = err.message;
		} else {
			errorMsg = "Unknown error";
		}
		error = true;
		waitingForPromise = false;
	}
}
</script>

<FormPage backButtonUri="#/auth/local/login" heading="Request password reset email for your Project-W account">
  <form class="mx-auto max-w-lg" onsubmit={postRequestPasswordReset}>
    <EmailField bind:value={email} bind:error={error} tabindex="1"/>

    {#if error}
      <Helper class="mt-2" color="red"><span class="font-medium">Sending request for password reset failed!</span> {errorMsg}</Helper>
    {/if}

    <div class="my-2">
      <WaitingButton waiting={waitingForPromise} disabled={error} tabindex="2">Request Password Reset Email</WaitingButton>
    </div>
  </form>
</FormPage>
