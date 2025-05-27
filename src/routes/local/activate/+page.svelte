<script lang="ts">
import Waiting from "$lib/components/waiting.svelte";
import { alerts, auth, routing } from "$lib/utils/global_state.svelte";
import { BackendCommError, post } from "$lib/utils/httpRequests.svelte";

async function activate(): Promise<void> {
	//send get request and wait for response
	try {
		await post<null>(
			"local-account/activate",
			{},
			false,
			Object.fromEntries(routing.querystring),
		);
		alerts.push({
			msg: "Account activation successful, please login again",
			color: "green",
		});
		auth.forgetToken();
		routing.set({
			destination: "#/auth/local/login",
			params: {},
			overwriteParams: true,
		});
	} catch (err: unknown) {
		let errorMsg = "Unknown error";
		if (err instanceof BackendCommError) {
			errorMsg = err.message;
		}
		alerts.push({
			msg: `Error occured during account activation: ${errorMsg}`,
			color: "red",
		});
		routing.set({ destination: "#/", params: {}, overwriteParams: true });
	}
}
</script>

{#await activate()}
  <Waiting/>
{/await}
