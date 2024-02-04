<script lang="ts">
  import { replace, querystring } from "svelte-spa-router";

  import Waiting from "../components/waiting.svelte";
  import { alerts } from "../utils/stores";
  import { get } from "../utils/httpRequests";

  let response: {[key: string]: any}

  async function activate(): Promise<void> {
    //send get request and wait for response
    response = await get("activate?" + $querystring);

    if (response.status === 200) {
      alerts.add("Account activation successful", "green");
    }
    else {
      alerts.add("Error during account activation: " + response.msg, "red");
    }
    replace("/");
  }
</script>

{#await activate()}
  <Waiting/>
{/await}
