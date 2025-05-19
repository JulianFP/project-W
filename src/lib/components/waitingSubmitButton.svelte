<script lang="ts">
import { Button, Spinner } from "flowbite-svelte";

let { waiting = false, disabled = false, children, ...rest } = $props();
</script>

{#if waiting}
  <Button type="submit" disabled>
    <Spinner class="me-3" size="4" color="secondary" />Loading ...
  </Button>
{:else}
  <Button type="submit" disabled={disabled} {...rest}>{@render children?.()}</Button>
{/if}
