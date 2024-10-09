<script lang="ts">
import { Helper } from "flowbite-svelte";

import GreetingPage from "../components/greetingPage.svelte";
import PasswordWithRepeatField from "../components/passwordWithRepeatField.svelte";
import WaitingButton from "../components/waitingSubmitButton.svelte";

import { type BackendResponse, post } from "../utils/httpRequests";
import { alerts, loggedIn, routing } from "../utils/stores";

$: if ($loggedIn)
	routing.set({
		destination: "/",
		params: {},
		overwriteParams: true,
		history: true,
	});

let response: BackendResponse;
let waitingForPromise = false;
let newPassword: string;

let passwordError = false;
let generalError = false;
let anyError: boolean;
let errorMessage: string;
$: anyError = passwordError || generalError;

async function resetPassword(event: Event): Promise<void> {
	waitingForPromise = true; //show loading button
	event.preventDefault(); //disable page reload after form submission

	response = await post(
		"users/resetPassword",
		Object.assign(
			{ newPassword: newPassword },
			Object.fromEntries($routing.querystring),
		),
	);

	if (response.ok) {
		alerts.add(response.msg, "green");
		routing.set({
			destination: "/",
			params: {},
			overwriteParams: true,
			history: true,
		});
	} else {
		errorMessage = response.msg;
		if (response.errorType === "password") passwordError = true;
		else generalError = true;
		waitingForPromise = false;
	}
}
</script>

<GreetingPage>
  <form class="mx-auto max-w-lg" on:submit={resetPassword}>
    <PasswordWithRepeatField bind:value={newPassword} bind:error={passwordError} otherError={generalError} bind:errorMessage={errorMessage} tabindex="1"/>

    {#if anyError}
      <Helper class="mt-2" color="red"><span class="font-medium"></span> {errorMessage}</Helper>
    {/if}

    <div class="my-2">
      <WaitingButton waiting={waitingForPromise} disabled={anyError} tabindex="3">Reset Password</WaitingButton>
    </div>

  </form>
</GreetingPage>
