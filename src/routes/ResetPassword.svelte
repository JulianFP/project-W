<script lang="ts">
  import { Helper } from "flowbite-svelte";
  import { push } from "svelte-spa-router";

  import GreetingPage from "../components/greetingPage.svelte";
  import PasswordWithRepeatField from "../components/passwordWithRepeatField.svelte";
  import WaitingButton from "../components/waitingSubmitButton.svelte";

  import { post } from "../utils/httpRequests";
  import { loggedIn, alerts } from "../utils/stores";
  import { getParams } from "../utils/helperFunctions";

  $: if($loggedIn) push("/");

  let response: {[key: string]: any};
  let waitingForPromise: boolean = false;
  let newPassword: string;

  let passwordError: boolean = false;
  let generalError: boolean = false;
  let anyError: boolean;
  let errorMessage: string;
  $: anyError = passwordError || generalError;

  async function resetPassword(event: Event): Promise<void> {
    waitingForPromise = true; //show loading button
    event.preventDefault(); //disable page reload after form submission

    response = await post("user/resetPassword", Object.assign({"newPassword": newPassword}, getParams()));

    if (response.status === 200){
      alerts.add(response.msg, "green");
      push("/");
    }
    else {
      errorMessage = response.msg;
      if(response.errorType === "password") passwordError = true;
      else generalError = true;
      waitingForPromise = false;
    }
  }
</script>

<GreetingPage>
  <form class="mx-auto max-w-lg" on:submit={resetPassword}>
    <PasswordWithRepeatField bind:value={newPassword} bind:error={passwordError} otherError={generalError} bind:errorMessage={errorMessage} tabindex="1"/>

    {#if anyError}
      <Helper class="mt-2" color="red"><span class="font-medium"></span> {errorMessage}</Helper>
    {/if}

    <div class="my-2">
      <WaitingButton waiting={waitingForPromise} disabled={anyError} tabindex="3">Reset Password</WaitingButton>
    </div>

  </form>
</GreetingPage>
