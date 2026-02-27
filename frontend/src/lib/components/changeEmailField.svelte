<script lang="ts">
	import { Helper, Input, Label, Span } from "flowbite-svelte";
	import { CloseOutline, PenSolid } from "flowbite-svelte-icons";
	import { onMount } from "svelte";
	import { localAccountChangeUserEmail } from "$lib/generated";
	import { alerts } from "$lib/utils/global_state.svelte";
	import { get_error_msg } from "$lib/utils/http_utils";
	import Button from "./button.svelte";
	import ConfirmPasswordModal from "./confirmPasswordModal.svelte";

	interface Props {
		defaultValue: string;
	}

	let { defaultValue, ...rest }: Props = $props();

	let email: string = $state("");
	onMount(() => {
		email = defaultValue;
	});

	let lockedInput = $state(true);
	let disabledSubmit: boolean = $derived(email === defaultValue); //make submit only possible if value has changed
	let password: string = $state("");
	let errorOccurred = $state(false);
	let errorMsg: string = $state("");
	let modalOpen = $state(false);

	function toggleLock(): void {
		email = defaultValue;
		errorOccurred = false;
		lockedInput = !lockedInput;
	}

	function openModal(event: Event) {
		event.preventDefault();
		modalOpen = true;
	}

	async function changeUserEmail(): Promise<{
		error: unknown;
		response: Response;
	}> {
		const { data, error, response } = await localAccountChangeUserEmail({
			body: { password: password, new_email: email },
		});
		if (error) {
			errorMsg = get_error_msg(error);
			errorOccurred = true;
		} else {
			alerts.push({ msg: data, color: "green" });
		}
		return { error: error, response: response };
	}
</script>

<form onsubmit={openModal}>
  <Label for="email" color={errorOccurred ? "red" : "gray"} class="mb-2">Email address</Label>
  <Input id="email" class="ps-10" type="email" name="email" autocomplete="email" color={errorOccurred ? "red" : "default"} required oninput={() => {errorOccurred = false}} bind:value={email} readonly={lockedInput || null} {...rest}>
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
  {#if errorOccurred}
    <Helper class="mt-2" color="red"><span class="font-medium"></span> {errorMsg}</Helper>
  {/if}
</form>

<ConfirmPasswordModal bind:open={modalOpen} bind:value={password} action={changeUserEmail} onerror={(error: unknown) => {errorMsg = get_error_msg(error); errorOccurred = true;}}>
  You are about to change this accounts email address to <Span highlight="blue" class="font-bold">{email}</Span>. We will send you an email to this address. The actual change of the address will only occur once you clicked on the link in the email.
</ConfirmPasswordModal>
