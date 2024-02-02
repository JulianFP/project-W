<script lang="ts">
  import { Label, Input } from "flowbite-svelte";
  import { EyeOutline, EyeSlashOutline} from "flowbite-svelte-icons";


  function disableError(): void {
    error = false
  }

  export let value: string;
  export let passwordVisible: boolean = false;
  export let error: boolean = false;
</script>

<div class="mb-6">
  <Label for={$$props.id ? $$props.id: "password"} color={error ? "red" : "gray"} class="mb-2"><slot/></Label>
  <Input type={passwordVisible ? "text" : "password"} id={$$props.id ? $$props.id: "password"} name="password" autocomplete={$$props.autocomplete ? $$props.autocomplete: "current-password"} color={error ? "red" : "base"} placeholder={passwordVisible ? "alice's password" : "••••••••••••••••"} required on:input={disableError} {...$$restProps} bind:value={value}>
    <button type="button" slot="right" on:click={() => (passwordVisible = !passwordVisible)} class="bg-transparent">
      {#if passwordVisible}
        <EyeOutline class="w-6 h-6" />
      {:else}
        <EyeSlashOutline class="w-6 h-6" />
      {/if}
    </button>
  </Input>
</div>
