<script lang="ts">
	import { Helper } from "flowbite-svelte";

	import EmailField from "$lib/components/emailField.svelte";
	import FormPage from "$lib/components/formPage.svelte";
	import WaitingButton from "$lib/components/waitingSubmitButton.svelte";
	import { localAccountRequestPasswordReset } from "$lib/generated";
	import { alerts, routing } from "$lib/utils/global_state.svelte";
	import { get_error_msg } from "$lib/utils/http_utils";

	let errorOccurred = $state(false);
	let errorMsg = $state("");
	let waitingForPromise = $state(false);
	let email: string = $state("");

	async function postRequestPasswordReset(event: Event): Promise<void> {
		waitingForPromise = true; //show loading button
		event.preventDefault(); //disable page reload after form submission

		const { error, data } = await localAccountRequestPasswordReset({
			query: { email: email },
		});
		if (error) {
			errorMsg = get_error_msg(error);
			errorOccurred = true;
			waitingForPromise = false;
		} else {
			alerts.push({ msg: data, color: "green" });
			await routing.set({
				destination: "#/",
				params: {},
				overwriteParams: true,
				history: true,
			});
		}
	}
</script>

<FormPage backButtonUri="#/auth/local/login" heading="Request password reset email for your Project-W account">
  <form class="mx-auto max-w-lg" onsubmit={postRequestPasswordReset}>
    <EmailField bind:value={email} bind:error={errorOccurred} tabindex="1"/>

    {#if errorOccurred}
      <Helper class="mt-2" color="red"><span class="font-medium">Sending request for password reset failed!</span> {errorMsg}</Helper>
    {/if}

    <div class="my-2">
      <WaitingButton waiting={waitingForPromise} disabled={errorOccurred} tabindex="2">Request Password Reset Email</WaitingButton>
    </div>
  </form>
</FormPage>
