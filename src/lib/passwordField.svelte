<!-- @migration-task Error while migrating Svelte code: $$props is used together with named props in a way that cannot be automatically migrated. -->
<script lang="ts">
import { Input, Label } from "flowbite-svelte";
import { EyeOutline, EyeSlashOutline } from "flowbite-svelte-icons";

export let value: string;
export let passwordVisible = false;
export let error = false;

function disableError(): void {
	error = false;
}
</script>

<div class="mb-6">
  <Label for={$$props.id ? $$props.id: "password"} color={error ? "red" : "gray"} class="mb-2"><slot/></Label>
  <Input type={passwordVisible ? "text" : "password"} id={$$props.id ? $$props.id: "password"} name="password" autocomplete={$$props.autocomplete ? $$props.autocomplete: "current-password"} color={error ? "red" : "base"} placeholder={passwordVisible ? "alice's password" : "••••••••••••••••"} required on:input={disableError} {...$$restProps} bind:value={value}>
    <button type="button" slot="right" on:click={() => (passwordVisible = !passwordVisible)} tabindex="-1">
      {#if passwordVisible}
        <EyeOutline class="w-6 h-6" />
      {:else}
        <EyeSlashOutline class="w-6 h-6" />
      {/if}
    </button>
  </Input>
</div>
