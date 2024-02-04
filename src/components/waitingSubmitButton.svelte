<script lang="ts">
import { Button, Spinner } from "flowbite-svelte";

export let waiting: boolean = false;
export let disabled: boolean = false;
</script>

{#if waiting}
  <Button type="submit" disabled>
    <Spinner class="me-3" size="4" color="white" />Loading ...
  </Button>
{:else}
  <Button type="submit" disabled={disabled} {...$$restProps}><slot/></Button>
{/if}
