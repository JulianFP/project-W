<script lang="ts">
import { auth, routing } from "$lib/utils/global_state.svelte";

$effect(() => {
	if (!auth.loggedIn) {
		const locationVal: string = routing.location;
		if (locationVal && locationVal !== "#/")
			localStorage.setItem("dest", locationVal);
		routing.set({ destination: "#/auth" });
	}
});

let { children } = $props();
</script>
{@render children()}
