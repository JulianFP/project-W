<script lang="ts">
import { Button, Spinner } from "flowbite-svelte";

interface Props {
	waiting?: boolean;
	disabled?: boolean;
	children?: import("svelte").Snippet;
}

let { waiting = false, disabled = false, children, ...rest }: Props = $props();
</script>

{#if waiting}
  <Button type="submit" disabled>
    <Spinner class="me-3" size="4" color="white" />Loading ...
  </Button>
{:else}
  <Button type="submit" disabled={disabled} on:click {...rest}>{@render children?.()}</Button>
{/if}
