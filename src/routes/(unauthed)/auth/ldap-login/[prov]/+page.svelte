<script lang="ts">
import { Helper, Input, Label } from "flowbite-svelte";

import FormPage from "$lib/components/formPage.svelte";
import PasswordField from "$lib/components/passwordField.svelte";
import WaitingButton from "$lib/components/waitingSubmitButton.svelte";

import { auth } from "$lib/utils/global_state.svelte";
import { BackendCommError, post } from "$lib/utils/httpRequests.svelte";
import type { components } from "$lib/utils/schema";

type Data = {
	auth_settings: components["schemas"]["AuthSettings"];
	prov: string;
};

interface Props {
	data: Data;
}
let { data }: Props = $props();

let error: boolean = $state(false);
let errorMsg: string = $state("");
let waitingForPromise = $state(false);
let username: string = $state("");
let password: string = $state("");

async function postLogin(event: Event): Promise<void> {
	waitingForPromise = true; //show loading button
	event.preventDefault(); //disable page reload after form submission

	//send post request and wait for response
	try {
		const token = await post<string>(
			`ldap/login/${data.prov}`,
			{
				grant_type: "password",
				username: username,
				password: password,
			},
			true,
		);
		auth.setToken(token);
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

<FormPage backButtonUri="#/auth" heading={`Login with ${data.prov} account`}>
  <form class="mx-auto max-w-lg" onsubmit={postLogin}>
    <div class="mb-6">
      <Label for="username" color={error ? "red" : "gray"} class="mb-2">Username</Label>
      <!-- set type, id, name and autocomplete  according to chromes recommendations: https://www.chromium.org/developers/design-documents/form-styles-that-chromium-understands//>-->
      <Input id="username" type="text" name="username" autocomplete="username" color={error ? "red" : "default"} placeholder="alice" required bind:value={username} tabindex={1}/>
    </div>
    <PasswordField bind:value={password} bind:error={error} tabindex={2}>Password</PasswordField>

    {#if error}
      <Helper class="mt-2" color="red"><span class="font-medium">Login failed!</span> {errorMsg}</Helper>
    {/if}

    <div class="flex max-w-lg justify-between items-center my-2">
      <WaitingButton waiting={waitingForPromise} tabindex={3}>Login</WaitingButton>
    </div>
  </form>
</FormPage>
