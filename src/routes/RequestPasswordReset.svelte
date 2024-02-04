<script lang="ts">
  import { Helper } from "flowbite-svelte";
  import { push } from "svelte-spa-router";

  import GreetingPage from "../components/greetingPage.svelte";
  import EmailField from "../components/emailField.svelte";
  import WaitingButton from "../components/waitingSubmitButton.svelte";

  import { post } from "../utils/httpRequests";
  import { loggedIn, alerts } from "../utils/stores";

  $: if($loggedIn) push("/");

  let error: boolean = false;
  let response: {[key: string]: any};
  let waitingForPromise: boolean = false;
  let email: string;

  async function postRequestPasswordReset(event: Event): Promise<void> {
    waitingForPromise = true; //show loading button
    event.preventDefault(); //disable page reload after form submission

    response = await post("requestPasswordReset", {"email": email})

    if (response.status === 200) {
      alerts.add(response.msg, "green");
      push("/");
    }
    else {
      error = true;
      waitingForPromise = false;
    }
  }

</script>

<GreetingPage>
  <form class="mx-auto max-w-lg" on:submit={postRequestPasswordReset}>
    <EmailField bind:value={email} bind:error={error} tabindex="1"/>

    {#if error}
      <Helper class="mt-2" color="red"><span class="font-medium">Sending request for password reset failed!</span> {response.msg}</Helper>
    {/if}

    <div class="my-2">
      <WaitingButton bind:waiting={waitingForPromise} bind:disabled={error} tabindex="2">Request Password Reset Email</WaitingButton>
    </div>

  </form>
</GreetingPage>
