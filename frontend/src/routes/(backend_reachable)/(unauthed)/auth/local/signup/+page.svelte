<script lang="ts">
	import { Helper } from "flowbite-svelte";
	import { UserAddSolid } from "flowbite-svelte-icons";
	import Button from "$lib/components/button.svelte";
	import EmailField from "$lib/components/emailField.svelte";
	import FormPage from "$lib/components/formPage.svelte";
	import PasswordWithRepeatField from "$lib/components/passwordWithRepeatField.svelte";
	import WaitingButton from "$lib/components/waitingSubmitButton.svelte";
	import {
		type AuthSettingsResponse,
		localAccountLogin,
		localAccountSignup,
	} from "$lib/generated";
	import { auth } from "$lib/utils/global_state.svelte";
	import { get_error_msg } from "$lib/utils/http_utils";

	let email: string = $state("");
	let password: string = $state("");

	let errorOccurred = $state(false);
	let errorMsg: string = $state("");

	let waitingForPromise = $state(false);

	async function postSignup(event: Event): Promise<void> {
		waitingForPromise = true; //show loading button
		event.preventDefault(); //disable page reload after form submission

		//send post request and wait for response
		const { error } = await localAccountSignup({
			body: { email: email, password: password },
		});
		if (error) {
			errorMsg = get_error_msg(error);
			errorOccurred = true;
		} else {
			const { error } = await localAccountLogin({
				body: { grant_type: "password", username: email, password: password },
			});
			if (error) {
				errorMsg = `Account created, however automatic login failed: ${get_error_msg(error)}`;
				errorOccurred = true;
			} else {
				auth.login();
			}
		}
		waitingForPromise = false;
	}

	type Data = {
		auth_settings: AuthSettingsResponse;
	};
	interface Props {
		data: Data;
	}
	let { data }: Props = $props();

	let helper_text = $derived(
		data.auth_settings.local_account.allowed_email_domains.length > 0
			? `Account creation is only permitted with email addresses that use one of the following domains: ${data.auth_settings.local_account.allowed_email_domains.join(", ")}`
			: "",
	);
</script>

<FormPage backButtonUri="#/auth" heading="Signup for Project-W account">
  <form class="mx-auto max-w-lg" onsubmit={postSignup}>
    <EmailField bind:value={email} bind:error={errorOccurred} helper_text={helper_text} tabindex={1}/>
    <PasswordWithRepeatField bind:value={password} bind:error={errorOccurred} bind:errorMsg={errorMsg} tabindex={2}/>

    {#if errorOccurred}
      <Helper class="mt-2" color="red"><span class="font-medium"></span> {errorMsg}</Helper>
    {/if}

    <div class="flex max-w-lg justify-between items-center my-2">
      <Button color="alternative" type="button" href="#/auth/local/login" tabindex={4}>Log in instead</Button>
      <WaitingButton waiting={waitingForPromise} tabindex={3}><UserAddSolid class="mr-2"/>Sign up</WaitingButton>
    </div>
  </form>
</FormPage>
