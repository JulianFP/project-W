<script lang="ts">
  import { Button, Helper, A } from "flowbite-svelte";

  import GreetingPage from "../components/greetingPage.svelte";
  import PasswordField from "../components/passwordField.svelte";
  import EmailField from "../components/emailField.svelte";
  import WaitingButton from "../components/waitingSubmitButton.svelte";

  import { post } from "../utils/httpRequests";
  import { authHeader, loggedIn } from "../utils/stores";
  import { destForward, preserveQuerystringForward } from "../utils/navigation";

  $: if($loggedIn) destForward();

  let error: boolean = false;
  let response: {[key: string]: any}
  let waitingForPromise: boolean = false;
  let email: string, password: string;

  async function postLogin(event: Event): Promise<void> {
    waitingForPromise = true; //show loading button
    event.preventDefault(); //disable page reload after form submission

    //send post request and wait for response
    response = await post("login", {"email": email, "password": password});

    if (response.status === 200) {
      authHeader.setToken(response.access_token)
      //if it was successfull, forward to different page
      destForward();
    }
    else {
      error = true; //display error message
      waitingForPromise = false;
    }
  }
</script>

<GreetingPage>
  <form class="mx-auto max-w-lg" on:submit={postLogin}>
    <EmailField bind:value={email} bind:error={error} tabindex="1"/>
    <PasswordField bind:value={password} bind:error={error} tabindex="2">Password</PasswordField>

    {#if error}
      <Helper class="mt-2" color="red"><span class="font-medium">Login failed!</span> {response.msg}</Helper>
    {/if}

    <div class="flex max-w-lg justify-between items-center my-2">
      <WaitingButton waiting={waitingForPromise} disabled={error} tabindex="3">Login</WaitingButton>
      <Button color="alternative" type="button" on:click={() => {preserveQuerystringForward("/signup")}} tabindex="4">Signup instead</Button>
    </div>

    <A href="#/requestPasswordReset" tabindex=5>Forgot password?</A>

  </form>
</GreetingPage>
