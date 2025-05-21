<script lang="ts">
import { A, Heading, Helper } from "flowbite-svelte";
import { ArrowLeftOutline } from "flowbite-svelte-icons";

import { PUBLIC_BACKEND_BASE_URL } from "$env/static/public";

import Button from "$lib/components/button.svelte";
import EmailField from "$lib/components/emailField.svelte";
import PasswordField from "$lib/components/passwordField.svelte";
import WaitingButton from "$lib/components/waitingSubmitButton.svelte";

import { auth, routing } from "$lib/utils/global_state.svelte";
import type { components } from "$lib/utils/schema";

type Data = {
	auth_settings: components["schemas"]["AuthSettings"];
};

interface Props {
	data: Data;
}
let { data }: Props = $props();

let error: boolean = $state(false);
let errorMsg: string = $state("");
let response: Response | null = $state(null);
let waitingForPromise = $state(false);
let email: string = $state("");
let password: string = $state("");

async function postLogin(event: Event): Promise<void> {
	waitingForPromise = true; //show loading button
	event.preventDefault(); //disable page reload after form submission

	//send post request and wait for response
	response = await fetch(`${PUBLIC_BACKEND_BASE_URL}/api/local-account/login`, {
		method: "POST",
		headers: {
			"Content-Type": "application/x-www-form-urlencoded",
		},
		body: new URLSearchParams({
			grant_type: "password",
			username: email,
			password: password,
		}),
	});

	const contentType = response.headers.get("content-type");
	if (response.ok) {
		auth.setToken(await response.text());
		//if it was successful, forward to different page
	} else if (contentType?.includes("application/json")) {
		const responseObj = await response.json();
		errorMsg = responseObj.detail;
		error = true;
	} else {
		errorMsg = `Backend returned ${response.status}`;
		error = true;
	}
	waitingForPromise = false;
}
</script>

<form class="mx-auto max-w-lg" onsubmit={postLogin}>
  <Button class="mb-3" size="xs" color="alternative" type="button" href="#/auth"><ArrowLeftOutline class="me-2 h-4 w-4"/>Back</Button>
  <Heading tag="h2" class="text-xl sm:text-2xl md:text-3xl mb-8">Login with Project-W account</Heading>

  <EmailField bind:value={email} bind:error={error} tabindex={1}/>
  <PasswordField bind:value={password} bind:error={error} tabindex={2}>Password</PasswordField>

  {#if error}
    <Helper class="mt-2" color="red"><span class="font-medium">Login failed!</span> {response !== null ? errorMsg : "Unknown error"}</Helper>
  {/if}

  <div class="flex max-w-lg justify-between items-center my-2">
    <WaitingButton waiting={waitingForPromise} tabindex={3}>Login</WaitingButton>
    {#if data.auth_settings.local_account.mode === "enabled"}
      <Button color="alternative" type="button" onclick={() => {routing.set({destination: "#/auth/local-signup", history: true})}} tabindex={4}>Signup instead</Button>
    {/if}
  </div>

  <A href="#/requestPasswordReset" tabindex={5}>Forgot password?</A>

</form>
