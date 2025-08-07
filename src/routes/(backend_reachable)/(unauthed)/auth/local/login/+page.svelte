<script lang="ts">
import { A, Helper } from "flowbite-svelte";

import Button from "$lib/components/button.svelte";
import EmailField from "$lib/components/emailField.svelte";
import FormPage from "$lib/components/formPage.svelte";
import PasswordField from "$lib/components/passwordField.svelte";
import WaitingButton from "$lib/components/waitingSubmitButton.svelte";

import { auth } from "$lib/utils/global_state.svelte";
import { BackendCommError, post } from "$lib/utils/httpRequests.svelte";
import type { components } from "$lib/utils/schema";
import { AngleRightOutline } from "flowbite-svelte-icons";

type Data = {
	auth_settings: components["schemas"]["AuthSettings"];
};

interface Props {
	data: Data;
}
let { data }: Props = $props();

let error: boolean = $state(false);
let errorMsg: string = $state("");
let waitingForPromise = $state(false);
let email: string = $state("");
let password: string = $state("");

async function postLogin(event: Event): Promise<void> {
	waitingForPromise = true; //show loading button
	event.preventDefault(); //disable page reload after form submission

	//send post request and wait for response
	try {
		await post<string>(
			"local-account/login",
			{
				grant_type: "password",
				username: email,
				password: password,
			},
			true,
			{},
			{},
			window.fetch,
			true,
		);
		auth.login();
	} catch (err: unknown) {
		if (err instanceof BackendCommError) {
			errorMsg = err.message;
		} else {
			errorMsg = "Unknown error";
		}
		error = true;
	}
	waitingForPromise = false;
}
</script>

<FormPage backButtonUri="#/auth" heading="Login with Project-W account">
  <form class="mx-auto max-w-lg" onsubmit={postLogin}>
    <EmailField bind:value={email} bind:error={error} tabindex={1}/>
    <PasswordField bind:value={password} bind:error={error} tabindex={2}>Password</PasswordField>

    {#if error}
      <Helper class="mt-2" color="red"><span class="font-medium">Login failed!</span> {errorMsg}</Helper>
    {/if}

    <div class="flex max-w-lg justify-between items-center my-2">
      {#if data.auth_settings.local_account.mode === "enabled"}
        <Button color="alternative" type="button" href="#/auth/local/signup" tabindex={4}>Sign up instead</Button>
      {/if}
      <WaitingButton waiting={waitingForPromise} tabindex={3}><AngleRightOutline class="mr-2"/>Log in</WaitingButton>
    </div>

    <div class="flex justify-end">
      <A href="#/auth/local/request-password-reset" tabindex={5}>Forgot password?</A>
    </div>

  </form>
</FormPage>
