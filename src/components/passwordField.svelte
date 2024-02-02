<script lang="ts">
  import { Label, Input } from "flowbite-svelte";
  import { EyeOutline, EyeSlashOutline} from "flowbite-svelte-icons";


  function disableError(): void {
    error = false
  }

  export let passwordVisible: boolean = false;
  export let error: boolean = false;
  export let value: string;
</script>

<div class="mb-6">
  <Label for="password" color={error ? "red" : "gray"} class="mb-2"><slot/></Label>
  <Input type={passwordVisible ? "text" : "password"} id="password" color={error ? "red" : "base"} placeholder={passwordVisible ? "alice's password" : "••••••••••••••••"} required bind:value={value} on:input={disableError}>
    <button type="button" slot="right" on:click={() => (passwordVisible = !passwordVisible)} class="bg-transparent">
      {#if passwordVisible}
        <EyeOutline class="w-6 h-6" />
      {:else}
        <EyeSlashOutline class="w-6 h-6" />
      {/if}
    </button>
  </Input>
</div>
