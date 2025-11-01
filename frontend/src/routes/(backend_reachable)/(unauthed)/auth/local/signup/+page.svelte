<script lang="ts">
	import { Helper } from "flowbite-svelte";
	import { UserAddSolid } from "flowbite-svelte-icons";
	import Button from "$lib/components/button.svelte";
	import EmailField from "$lib/components/emailField.svelte";
	import FormPage from "$lib/components/formPage.svelte";
	import PasswordWithRepeatField from "$lib/components/passwordWithRepeatField.svelte";
	import WaitingButton from "$lib/components/waitingSubmitButton.svelte";
	import { auth } from "$lib/utils/global_state.svelte";
	import { BackendCommError, post } from "$lib/utils/httpRequests.svelte";
	import type { components } from "$lib/utils/schema";

	let email: string = $state("");
	let password: string = $state("");

	let error = $state(false);
	let errorMsg: string = $state("");

	let waitingForPromise = $state(false);

	async function postSignup(event: Event): Promise<void> {
		waitingForPromise = true; //show loading button
		event.preventDefault(); //disable page reload after form submission

		//send post request and wait for response
		try {
			await post<string>("local-account/signup", {
				email: email,
				password: password,
			});

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
					errorMsg = `Account created, however automatic login failed: ${err.message}`;
				} else {
					errorMsg =
						"Account created, however automatic login failed: Unknown error";
				}
				error = true;
			}
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

	type Data = {
		auth_settings: components["schemas"]["AuthSettings"];
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
    <EmailField bind:value={email} bind:error={error} helper_text={helper_text} tabindex={1}/>
    <PasswordWithRepeatField bind:value={password} bind:error={error} bind:errorMsg={errorMsg} tabindex={2}/>

    {#if error}
      <Helper class="mt-2" color="red"><span class="font-medium"></span> {errorMsg}</Helper>
    {/if}

    <div class="flex max-w-lg justify-between items-center my-2">
      <Button color="alternative" type="button" href="#/auth/local/login" tabindex={4}>Log in instead</Button>
      <WaitingButton waiting={waitingForPromise} tabindex={3}><UserAddSolid class="mr-2"/>Sign up</WaitingButton>
    </div>
  </form>
</FormPage>
