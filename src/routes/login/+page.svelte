<script lang="ts">
import { A, Button, Helper } from "flowbite-svelte";

import EmailField from "$lib/emailField.svelte";
import GreetingPage from "$lib/greetingPage.svelte";
import PasswordField from "$lib/passwordField.svelte";
import WaitingButton from "$lib/waitingSubmitButton.svelte";

import { auth } from "$lib/global_state.svelte";
import { type BackendResponse, post } from "$lib/httpRequests";

run(() => {
	if (auth.loggedIn) destForward();
});

let error = $state(false);
let response: BackendResponse | null = $state(null);
let waitingForPromise = $state(false);
let email: string = $state("");
let password: string = $state("");

async function postLogin(event: Event): Promise<void> {
	waitingForPromise = true; //show loading button
	event.preventDefault(); //disable page reload after form submission

	//send post request and wait for response
	response = await post("users/login", { email: email, password: password });

	if (response.ok && response.accessToken != null) {
		auth.setToken(response.accessToken);
		//if it was successful, forward to different page
	} else {
		error = true; //display error message
		waitingForPromise = false;
	}
}
</script>

<GreetingPage>
  <form class="mx-auto max-w-lg" onsubmit={postLogin}>
    <EmailField bind:value={email} bind:error={error} tabindex="1"/>
    <PasswordField bind:value={password} bind:error={error} tabindex="2">Password</PasswordField>

    {#if error}
      <Helper class="mt-2" color="red"><span class="font-medium">Login failed!</span> {response.msg}</Helper>
    {/if}

    <div class="flex max-w-lg justify-between items-center my-2">
      <WaitingButton waiting={waitingForPromise} disabled={error} tabindex="3">Login</WaitingButton>
      <Button color="alternative" type="button" on:click={() => {routing.set({destination: "/signup", history: true})}} tabindex="4">Signup instead</Button>
    </div>

    <A href="#/requestPasswordReset" tabindex=5>Forgot password?</A>

  </form>
</GreetingPage>
