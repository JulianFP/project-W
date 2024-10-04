<script lang="ts">
import { A, Button, Helper } from "flowbite-svelte";

import EmailField from "../components/emailField.svelte";
import GreetingPage from "../components/greetingPage.svelte";
import PasswordField from "../components/passwordField.svelte";
import WaitingButton from "../components/waitingSubmitButton.svelte";

import { type BackendResponse, post } from "../utils/httpRequests";
import { destForward, preserveQuerystringForward } from "../utils/navigation";
import { authHeader, loggedIn } from "../utils/stores";

$: if ($loggedIn) destForward();

let error = false;
let response: BackendResponse;
let waitingForPromise = false;
let email: string;
let password: string;

async function postLogin(event: Event): Promise<void> {
	waitingForPromise = true; //show loading button
	event.preventDefault(); //disable page reload after form submission

	//send post request and wait for response
	response = await post("users/login", { email: email, password: password });

	if (response.ok && response.accessToken != null) {
		authHeader.setToken(response.accessToken);
		//if it was successfull, forward to different page
		destForward();
	} else {
		error = true; //display error message
		waitingForPromise = false;
	}
}
</script>

<GreetingPage>
  <form class="mx-auto max-w-lg" on:submit={postLogin}>
    <EmailField bind:value={email} bind:error={error} tabindex="1"/>
    <PasswordField bind:value={password} bind:error={error} tabindex="2">Password</PasswordField>

    {#if error}
      <Helper class="mt-2" color="red"><span class="font-medium">Login failed!</span> {response.msg}</Helper>
    {/if}

    <div class="flex max-w-lg justify-between items-center my-2">
      <WaitingButton waiting={waitingForPromise} disabled={error} tabindex="3">Login</WaitingButton>
      <Button color="alternative" type="button" on:click={() => {preserveQuerystringForward("/signup")}} tabindex="4">Signup instead</Button>
    </div>

    <A href="#/requestPasswordReset" tabindex=5>Forgot password?</A>

  </form>
</GreetingPage>
