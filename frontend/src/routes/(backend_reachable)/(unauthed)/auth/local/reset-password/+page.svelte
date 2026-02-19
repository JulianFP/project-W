<script lang="ts">
	import { Helper } from "flowbite-svelte";

	import FormPage from "$lib/components/formPage.svelte";
	import PasswordWithRepeatField from "$lib/components/passwordWithRepeatField.svelte";
	import WaitingButton from "$lib/components/waitingSubmitButton.svelte";
	import { localAccountResetPassword } from "$lib/generated";
	import { alerts, routing } from "$lib/utils/global_state.svelte";
	import { get_error_msg } from "$lib/utils/http_utils";

	let waitingForPromise = $state(false);
	let newPassword: string = $state("");

	let errorOccurred: boolean = $state(false);
	let errorMsg: string = $state("");

	async function resetPassword(event: Event): Promise<void> {
		waitingForPromise = true; //show loading button
		event.preventDefault(); //disable page reload after form submission

		const token = routing.querystring.get("token");
		if (token) {
			const { error } = await localAccountResetPassword({
				body: { token: token, new_password: newPassword },
			});
			if (error) {
				errorMsg = get_error_msg(error);
				errorOccurred = true;
			} else {
				alerts.push({ msg: "Password reset successful", color: "green" });
				await routing.set({
					destination: "#/",
					params: {},
					overwriteParams: true,
					history: true,
				});
			}
		} else {
			errorMsg = "No password reset token was provided";
			errorOccurred = true;
		}
		waitingForPromise = false;
	}
</script>

<FormPage backButtonUri="#/auth/local/login" heading="Reset password of your Project-W account">
  <form class="mx-auto max-w-lg" onsubmit={resetPassword}>
    <PasswordWithRepeatField bind:value={newPassword} bind:error={errorOccurred} bind:errorMsg={errorMsg} tabindex={1}/>

    {#if errorOccurred}
      <Helper class="mt-2" color="red"><span class="font-medium"></span> {errorMsg}</Helper>
    {/if}

    <div class="my-2">
      <WaitingButton waiting={waitingForPromise} tabindex={3}>Reset Password</WaitingButton>
    </div>

  </form>
</FormPage>
