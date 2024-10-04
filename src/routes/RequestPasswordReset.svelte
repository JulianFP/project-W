<script lang="ts">
import { Helper } from "flowbite-svelte";
import { push } from "svelte-spa-router";

import EmailField from "../components/emailField.svelte";
import GreetingPage from "../components/greetingPage.svelte";
import WaitingButton from "../components/waitingSubmitButton.svelte";

import { type BackendResponse, get } from "../utils/httpRequests";
import { alerts, loggedIn } from "../utils/stores";

$: if ($loggedIn) push("/");

let error = false;
let response: BackendResponse;
let waitingForPromise = false;
let email: string;

async function postRequestPasswordReset(event: Event): Promise<void> {
	waitingForPromise = true; //show loading button
	event.preventDefault(); //disable page reload after form submission

	response = await get("users/requestPasswordReset", { email: email });

	if (response.ok) {
		alerts.add(response.msg, "green");
		push("/");
	} else {
		error = true;
		waitingForPromise = false;
	}
}
</script>

<GreetingPage>
  <form class="mx-auto max-w-lg" on:submit={postRequestPasswordReset}>
    <EmailField bind:value={email} bind:error={error} tabindex="1"/>

    {#if error}
      <Helper class="mt-2" color="red"><span class="font-medium">Sending request for password reset failed!</span> {response.msg}</Helper>
    {/if}

    <div class="my-2">
      <WaitingButton waiting={waitingForPromise} disabled={error} tabindex="2">Request Password Reset Email</WaitingButton>
    </div>

  </form>
</GreetingPage>
