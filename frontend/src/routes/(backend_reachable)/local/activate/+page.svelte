<script lang="ts">
	import { Spinner } from "flowbite-svelte";

	import { invalidate } from "$app/navigation";
	import { localAccountActivate } from "$lib/generated";
	import { alerts, routing } from "$lib/utils/global_state.svelte";
	import { get_error_msg } from "$lib/utils/http_utils";

	async function activate(): Promise<void> {
		//send get request and wait for response
		let errorMsg: string | undefined;
		const token = routing.querystring.get("token");
		if (token) {
			const { error } = await localAccountActivate({ query: { token: token } });
			if (error) {
				errorMsg = get_error_msg(error);
			} else {
				alerts.push({
					msg: "Account activation successful!",
					color: "green",
				});
			}
		} else {
			errorMsg = "No activation token was provided";
		}
		if (errorMsg) {
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
