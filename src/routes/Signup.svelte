<script lang="ts">
  import { Button,  Helper } from "flowbite-svelte";

  import GreetingPage from "../components/greetingPage.svelte";
  import PasswordWithRepeatField from "../components/passwordWithRepeatField.svelte";
  import EmailField from "../components/emailField.svelte";
  import WaitingButton from "../components/waitingSubmitButton.svelte";

  import { post } from "../utils/httpRequests";
  import { authHeader, loggedIn, alerts } from "../utils/stores";
  import { destForward, preserveQuerystringForward } from "../utils/navigation";

  $: if($loggedIn) destForward();

  let email: string, password: string;

  let emailError: boolean = false;
  let passwordError: boolean = false;
  let generalError: boolean = false;
  let errorMessage: string;
  $: anyError = emailError || passwordError || generalError;

  let Signupresponse: {[key: string]: any}
  let waitingForPromise: boolean = false;

  async function postSignup(event: Event): Promise<void> {
    waitingForPromise = true; //show loading button
    event.preventDefault(); //disable page reload after form submission

    //send post request and wait for response
    Signupresponse = await post("users/signup", {"email": email, "password": password});

    if (Signupresponse.status === 200) {
      //login user 
      let loginResponse = await post("users/login", {"email": email, "password": password})
    
      if (loginResponse.status === 200) {
        authHeader.setToken(loginResponse.access_token)
        //if it was successfull, show alert and forward to different page
        alerts.add(Signupresponse.msg, "green");
        destForward();
      }
      else {
        generalError = true; //display error message
        errorMessage = "Account created, however automatic login failed: " + loginResponse.msg;
      }
    }
    else {
      errorMessage = Signupresponse.msg;
      if(Signupresponse.errorType === "email"){
        emailError = true;
        const allowedDomains: String[] = Signupresponse.allowedEmailDomains;
        if(allowedDomains) errorMessage += ". Allowed email domains: " + allowedDomains.join(", ");
      }
      else if(Signupresponse.errorType === "password") passwordError = true;
      else generalError = true;
    }

    waitingForPromise = false;
  }
</script>

<GreetingPage>
  <form class="mx-auto max-w-lg" on:submit={postSignup}>
    <EmailField bind:value={email} bind:error={emailError} tabindex="1"/>
    <PasswordWithRepeatField bind:value={password} bind:error={passwordError} otherError={generalError} bind:errorMessage={errorMessage} tabindex="2"/>

    {#if anyError}
      <Helper class="mt-2" color="red"><span class="font-medium"></span> {errorMessage}</Helper>
    {/if}

    <div class="flex max-w-lg justify-between items-center my-2">
      <WaitingButton waiting={waitingForPromise} disabled={anyError} tabindex="3">Signup</WaitingButton>
      <Button color="alternative" type="button" on:click={() => {preserveQuerystringForward("/login")}} tabindex="4">Login instead</Button>
    </div>
  </form>
</GreetingPage>
