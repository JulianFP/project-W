<script lang="ts">
import { Helper, Input, Label, Span } from "flowbite-svelte";
import { CloseOutline, PenSolid } from "flowbite-svelte-icons";

import { alerts } from "$lib/utils/global_state.svelte";
import { BackendCommError, postLoggedIn } from "$lib/utils/httpRequests.svelte";
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

function toggleLock(): void {
	email = defaultValue;
	error = false;
	lockedInput = !lockedInput;
}

function openModal(event: Event) {
	event.preventDefault();
	modalOpen = true;
}

async function changeUserEmail(): Promise<void> {
	const response: string = await postLoggedIn<string>(
		"local-account/change_user_email",
		{
			password: password,
			new_email: email,
		},
	);
	alerts.push({ msg: response, color: "green" });
}
</script>

<form onsubmit={openModal}>
  <Label for="email" color={error ? "red" : "gray"} class="mb-2">Email address</Label>
  <Input id="email" class="ps-10" type="email" name="email" autocomplete="email" color={error ? "red" : "default"} required oninput={() => {error = false}} bind:value={email} readonly={lockedInput || null} {...rest}>
    {#snippet left()}
			<button type="button" class="pointer-events-auto cursor-pointer" onclick={toggleLock}>
	      {#if lockedInput}
	        <PenSolid class="w-6 h-6"/>
	      {:else}
	        <CloseOutline class="w-6 h-6"/>
	      {/if}
	    </button>
		{/snippet}
    {#snippet right()}
      {#if !lockedInput}
        <Button size="sm" type="submit" disabled={disabledSubmit}>Change Email</Button>
      {/if}
    {/snippet}
  </Input>
  {#if error}
    <Helper class="mt-2" color="red"><span class="font-medium"></span> {errorMsg}</Helper>
  {/if}
</form>

<ConfirmPasswordModal bind:open={modalOpen} bind:value={password} action={changeUserEmail} onerror={(err: BackendCommError) => {errorMsg = err.message; error = true;}}>
  You are about to change this accounts email address to <Span highlight="blue" class="font-bold">{email}</Span>. We will send you an email to this address. The actual change of the address will only occur once you clicked on the link in the email.
</ConfirmPasswordModal>
