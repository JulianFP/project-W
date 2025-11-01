<script lang="ts">
	import { Helper } from "flowbite-svelte";

	import FormPage from "$lib/components/formPage.svelte";
	import PasswordWithRepeatField from "$lib/components/passwordWithRepeatField.svelte";
	import WaitingButton from "$lib/components/waitingSubmitButton.svelte";

	import { alerts, routing } from "$lib/utils/global_state.svelte";
	import { BackendCommError, post } from "$lib/utils/httpRequests.svelte";

	let waitingForPromise = $state(false);
	let newPassword: string = $state("");

	let error: boolean = $state(false);
	let errorMsg: string = $state("");

	async function resetPassword(event: Event): Promise<void> {
		waitingForPromise = true; //show loading button
		event.preventDefault(); //disable page reload after form submission

		try {
			await post<null>(
				"local-account/reset_password",
				Object.assign(
					{ new_password: newPassword },
					Object.fromEntries(routing.querystring),
				),
			);
			alerts.push({ msg: "Password reset successful", color: "green" });
			await routing.set({
				destination: "#/",
				params: {},
				overwriteParams: true,
				history: true,
			});
		} catch (err: unknown) {
			if (err instanceof BackendCommError) {
				errorMsg = err.message;
			} else {
				errorMsg = "Unknown error";
			}
			error = true;
			waitingForPromise = false;
		}
	}
</script>

<FormPage backButtonUri="#/auth/local/login" heading="Reset password of your Project-W account">
  <form class="mx-auto max-w-lg" onsubmit={resetPassword}>
    <PasswordWithRepeatField bind:value={newPassword} bind:error={error} bind:errorMsg={errorMsg} tabindex={1}/>

    {#if error}
      <Helper class="mt-2" color="red"><span class="font-medium"></span> {errorMsg}</Helper>
    {/if}

    <div class="my-2">
      <WaitingButton waiting={waitingForPromise} tabindex={3}>Reset Password</WaitingButton>
    </div>

  </form>
</FormPage>
