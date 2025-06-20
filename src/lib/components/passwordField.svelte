<script lang="ts">
import { Helper, Input, Label } from "flowbite-svelte";
import {
	EyeOutline,
	EyeSlashOutline,
	InfoCircleSolid,
} from "flowbite-svelte-icons";

function disableError(): void {
	error = false;
}

let {
	children,
	id = "password",
	value = $bindable(),
	error = $bindable(false),
	passwordVisible = $bindable(false),
	password_new = false,
	helper_text = "",
	...rest
} = $props();
</script>

<div class="mb-6 w-full">
  <Label for={id} color={error ? "red" : "gray"} class="mb-2">{@render children?.()}</Label>
  <Input wrapperClass="w-full" type={passwordVisible ? "text" : "password"} {id} name="password" autocomplete={password_new ? "new-password" : "current-password"} color={error ? "red" : "default"} placeholder={passwordVisible ? "alice's password" : "••••••••••••••••"} required oninput={disableError} {...rest} bind:value={value}>
    {#snippet right()}
      <button onclick={() => (passwordVisible = !passwordVisible)} tabindex={-1} class="cursor-pointer" type="button">
        {#if passwordVisible}
          <EyeOutline class="w-6 h-6" />
        {:else}
          <EyeSlashOutline class="w-6 h-6" />
        {/if}
      </button>
    {/snippet}
  </Input>
  {#if helper_text}
    <Helper class="mt-2 text-sm">
      <InfoCircleSolid class="inline"/> {helper_text}
    </Helper>
  {/if}
</div>
