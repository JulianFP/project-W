<script lang="ts">
import { Input, Label } from "flowbite-svelte";

let { value = $bindable(), error = $bindable(false), ...rest } = $props();
</script>

<div class="mb-6">
  <Label for="email" color={error ? "red" : "gray"} class="mb-2">Email address</Label>
  <!-- set type, id, name and autocomplete  according to chromes recommendations: https://www.chromium.org/developers/design-documents/form-styles-that-chromium-understands//>-->
  <Input type="email" id="email" name="email" autocomplete="email" color={error ? "red" : "default"} placeholder="alice@example.com" required {...rest} bind:value={value}/>
</div>
