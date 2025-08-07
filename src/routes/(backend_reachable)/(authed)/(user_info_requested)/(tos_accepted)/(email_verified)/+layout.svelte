<script lang="ts">
import WaitingSubmitButton from "$lib/components/waitingSubmitButton.svelte";
import { alerts } from "$lib/utils/global_state.svelte";
import { BackendCommError } from "$lib/utils/httpRequests.svelte";
import { getLoggedIn } from "$lib/utils/httpRequestsAuth.svelte";
import type { components } from "$lib/utils/schema";
import { Heading, Helper, P } from "flowbite-svelte";
import { MailBoxSolid } from "flowbite-svelte-icons";
import type { Snippet } from "svelte";

type Data = {
	user_info: components["schemas"]["User"];
};
interface Props {
	data: Data;
	children: Snippet;
}
let { data, children }: Props = $props();

let waitingForResend = $state(false);
let resendError = $state(false);
let resendErrorMsg = $state("");

async function getResendEmail() {
	waitingForResend = true;
	resendError = false;
	resendErrorMsg = "";

	try {
		let resendResponse = await getLoggedIn<string>(
			"local-account/resend_activation_email",
		);
		alerts.push({ msg: resendResponse, color: "green" });
	} catch (err: unknown) {
		if (err instanceof BackendCommError) {
			resendErrorMsg = err.message;
		} else {
			resendErrorMsg = "Unknown error";
		}
		resendError = true;
	}

	waitingForResend = false;
}
</script>
{#if data.user_info.is_verified}
  {@render children()}
{:else}
  <div class="flex-1 max-w-screen-sm h-full mx-auto flex flex-col items-center justify-center gap-4">
    <Heading tag="h2" class="flex items-center gap-4">
      <MailBoxSolid size="xl" class="inline h-24 w-24"/>
      You've Got Mail
    </Heading>
    <P class="text-center">Your account was successfully created! Before you can start using this service you need to verify your email address by clicking on the link in the mail we just sent to you.</P>
    <WaitingSubmitButton class="max-w-fit" size="xs" waiting={waitingForResend} type="button" onclick={getResendEmail}>Resend email</WaitingSubmitButton>
    {#if resendError}
      <Helper class="mt-2" color="red">{resendErrorMsg}</Helper>
    {/if}
  </div>
{/if}
