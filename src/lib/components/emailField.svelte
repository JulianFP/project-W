<script lang="ts">
import { Helper, Input, Label } from "flowbite-svelte";
import { EnvelopeSolid, InfoCircleSolid } from "flowbite-svelte-icons";

let {
	value = $bindable(),
	error = $bindable(false),
	helper_text = "",
	...rest
} = $props();
</script>

<div class="mb-6">
  <Label for="email" color={error ? "red" : "gray"} class="mb-2">Email address</Label>
  <!-- set type, id, name and autocomplete  according to chromes recommendations: https://www.chromium.org/developers/design-documents/form-styles-that-chromium-understands//>-->
  <Input type="email" id="email" name="email" autocomplete="email" class="ps-9" color={error ? "red" : "default"} placeholder="alice@example.com" required {...rest} bind:value={value}>
    {#snippet left()}
      <EnvelopeSolid class="h-5 w-5"/>
    {/snippet}
  </Input>
  {#if helper_text}
    <Helper class="mt-2 text-sm">
      <InfoCircleSolid class="inline"/> {helper_text}
    </Helper>
  {/if}
</div>
