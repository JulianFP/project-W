<script lang="ts">
import { Helper, Input, Label } from "flowbite-svelte";
import { LockOpenSolid, LockSolid } from "flowbite-svelte-icons";

import { alerts } from "$lib/global_state.svelte";
import { type BackendResponse, postLoggedIn } from "$lib/httpRequests";
import Button from "./button.svelte";
import ConfirmPasswordModal from "./confirmPasswordModal.svelte";

interface Props {
	defaultValue: string;
}

let { defaultValue, ...rest }: Props = $props();

let lockedInput = $state(true);
let email: string = $state(defaultValue);
let disabledSubmit: boolean = $derived(email === defaultValue); //make submit only possible if value has changed
let password: string = $state("");
let error = $state(false);
let errorMsg: string = $state("");
let modalOpen = $state(false);
let response: BackendResponse | null = $state(null);

function toggleLock(): void {
	email = defaultValue;
	error = false;
	lockedInput = !lockedInput;
}

function openModal(event: Event) {
	event.preventDefault();
	modalOpen = true;
}

async function postChangeUserEmail(): Promise<BackendResponse> {
	return postLoggedIn("users/changeEmail", {
		password: password,
		newEmail: email,
	});
}

//post modal code
function onModalClose() {
	if (!modalOpen && response != null) {
		if (response.ok) alerts.push({ msg: response.msg, color: "green" });
		else {
			errorMsg = response.msg;
			error = true;
		}
		password = "";
		response = null;
	}
}
</script>

<form onsubmit={openModal}>
  <Label for="email" color={error ? "red" : "gray"} class="mb-2">Email address</Label>
  <Input type="email" id="email" name="email" autocomplete="email" color={error ? "red" : "primary"} required oninput={() => {error = false}} bind:value={email} readonly={lockedInput || null} {...rest}>
    {#snippet left()}
				<button type="button"  class="pointer-events-auto" onclick={toggleLock}>
	      {#if lockedInput}
	        <LockSolid class="w-6 h-6"/>
	      {:else}
	        <LockOpenSolid class="w-6 h-6"/>
	      {/if}
	    </button>
			{/snippet}
    {#snippet right()}
				<Button  size="sm" type="submit" disabled={disabledSubmit||error}>Change Email</Button>
			{/snippet}
  </Input>
  {#if error}
    <Helper class="mt-2" color="red"><span class="font-medium"></span> {errorMsg}</Helper>
  {/if}
</form>

<ConfirmPasswordModal bind:open={modalOpen} bind:value={password} bind:response={response} action={postChangeUserEmail} onclose={onModalClose}>
  You are about to change this accounts email address to {email}. We will send you an email to this address. The actual change of the address will only occur ones you clicked on the link in the email.
</ConfirmPasswordModal>
