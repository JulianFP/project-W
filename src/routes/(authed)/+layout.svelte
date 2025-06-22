<script lang="ts">
import { auth, routing } from "$lib/utils/global_state.svelte";

import WaitingForGoto from "$lib/components/waitingForGoto.svelte";

$effect(() => {
	if (!auth.loggedIn) {
		routing.dest_forward();
	}
});

let { children } = $props();
</script>
{#if auth.loggedIn}
  {@render children()}
{:else}
  {#await routing.dest_forward()}
    <WaitingForGoto/>
  {/await}
{/if}
