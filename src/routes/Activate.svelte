<script lang="ts">
  import { replace } from "svelte-spa-router";

  import Waiting from "../components/waiting.svelte";
  import { alerts } from "../utils/stores";
  import { post } from "../utils/httpRequests";
  import { getParams } from "../utils/helperFunctions";

  let response: {[key: string]: any}

  async function activate(): Promise<void> {
    //send get request and wait for response
    response = await post("user/activate", getParams());

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
