<script lang="ts">
import { Spinner } from "flowbite-svelte";

import { invalidate } from "$app/navigation";
import { alerts, routing } from "$lib/utils/global_state.svelte";
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
			msg: "Account activation successful!",
			color: "green",
		});
	} catch (err: unknown) {
		let errorMsg = "Unknown error";
		if (err instanceof BackendCommError) {
			errorMsg = err.message;
		}
		alerts.push({
			msg: `Error occurred during account activation: ${errorMsg}`,
			color: "red",
		});
	}
	await routing.set({ destination: "#/", params: {}, overwriteParams: true });
	await invalidate("app:user_info");
}
</script>

{#await activate()}
  <div class="flex flex-col w-full h-full justify-evenly items-center my-8">
    <Spinner class="me-3" size="10" />
  </div>
{/await}
