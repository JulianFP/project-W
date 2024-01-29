<script lang="ts">
  import { Label, Input } from "flowbite-svelte";

  function disableError(): void {
    error = false
  }

  export let error: boolean = false;
  export let value: string;
</script>

<div class="mb-6">
  <Label for="email" color={error ? "red" : "gray"} class="mb-2">Email address</Label>
  <Input type="email" id="email" color={error ? "red" : "base"} placeholder="alice@example.com" required bind:value={value} on:input={disableError}/>
</div>
