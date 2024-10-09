<script lang="ts">
import Waiting from "../components/waiting.svelte";
import { type BackendResponse, post } from "../utils/httpRequests";
import { alerts, routing } from "../utils/stores";

let response: BackendResponse;

async function activate(): Promise<void> {
	//send get request and wait for response
	response = await post(
		"users/activate",
		Object.fromEntries($routing.querystring),
	);

	if (response.ok) {
		alerts.add("Account activation successful", "green");
	} else {
		alerts.add(`Error during account activation: ${response.msg}`, "red");
	}
	routing.set({ destination: "/", params: {}, overwriteParams: true });
}
</script>

{#await activate()}
  <Waiting/>
{/await}
