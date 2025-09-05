<script lang="ts">
import WaitingForGoto from "$lib/components/waitingForGoto.svelte";
import { auth, routing } from "$lib/utils/global_state.svelte";

$effect(() => {
	if (!auth.loggedIn && auth.loggedInSettled) {
		routing.dest_forward();
	}
});

let { children } = $props();
</script>
{#await auth.awaitLoggedIn}
  <WaitingForGoto/>
{:then}
  {#if auth.loggedIn}
    {@render children()}
  {:else}
    {#await routing.dest_forward()}
      <WaitingForGoto/>
    {/await}
  {/if}
{/await}
