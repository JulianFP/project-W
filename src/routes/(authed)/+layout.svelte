<script lang="ts">
import { auth, routing } from "$lib/utils/global_state.svelte";

$effect(() => {
	if (!auth.loggedIn) {
		const locationVal: string = routing.location;
		let newParams: Record<string, string> | null = null;
		if (locationVal && locationVal !== "#/") newParams = { dest: locationVal };
		routing.set({ destination: "#/login", params: newParams });
	}
});

let { children } = $props();
</script>
{@render children()}
