<script lang="ts">
  import { Label, Input } from "flowbite-svelte";

  function disableError(): void {
    error = false
  }

  export let value: string;
  export let error: boolean = false;
</script>

<div class="mb-6">
  <Label for="email" color={error ? "red" : "gray"} class="mb-2">Email address</Label>
  <!-- set type, id, name and autocomplete  according to chromes recommendations: https://www.chromium.org/developers/design-documents/form-styles-that-chromium-understands//>-->
  <Input type="email" id="email" name="email" autocomplete="email" color={error ? "red" : "base"} placeholder="alice@example.com" required on:input={disableError} {...$$restProps} bind:value={value}/>
</div>
