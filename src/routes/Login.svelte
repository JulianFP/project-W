<script lang="ts">
  import { Button, Spinner, Helper } from "flowbite-svelte";

  import GreetingPage from "../components/greetingPage.svelte";
  import PasswordField from "../components/passwordField.svelte";
  import EmailField from "../components/emailField.svelte";

  import { post } from "../utils/httpRequests";
  import { authHeader } from "../utils/stores";
  import { destForward, preserveQuerystringForward } from "../utils/navigation";

  let error = false;
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
    <EmailField bind:value={email} bind:error={error}/>
    <PasswordField bind:value={password} bind:error={error}/>

    <div class="flex max-w-lg justify-between items-center">
      {#if waitingForPromise}
        <Button type="submit" disabled>
          <Spinner class="me-3" size="4" color="white" />Loading ...
        </Button>
      {:else}
        <Button type="submit">Login</Button>
      {/if}
      <Button color="alternative" type="button" on:click={() => {preserveQuerystringForward("/signup")}}>Signup instead</Button>
    </div>

    {#if error}
      <Helper class="mt-2" color="red"><span class="font-medium">Login failed!</span> {response.msg}</Helper>
    {/if}
  </form>
</GreetingPage>
