<script lang="ts">
import { replace } from "svelte-spa-router";

import Waiting from "../components/waiting.svelte";
import { getParams } from "../utils/helperFunctions";
import { type BackendResponse, post } from "../utils/httpRequests";
import { alerts } from "../utils/stores";

let response: BackendResponse;

async function activate(): Promise<void> {
	//send get request and wait for response
	response = await post("users/activate", getParams());

	if (response.ok) {
		alerts.add("Account activation successful", "green");
	} else {
		alerts.add(`Error during account activation: ${response.msg}`, "red");
	}
	replace("/");
}
</script>

{#await activate()}
  <Waiting/>
{/await}
