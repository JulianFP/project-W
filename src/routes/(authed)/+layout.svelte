<script lang="ts">
import { auth, routing } from "$lib/utils/global_state.svelte";

$effect(() => {
	if (!auth.loggedIn) {
		routing.dest_forward();
	}
});

let { children } = $props();
</script>
{@render children()}
