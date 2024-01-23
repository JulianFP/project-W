<script lang="ts">
  import { Heading, Span, Label, Input, Button, Spinner, Helper } from "flowbite-svelte";
  import { EyeOutline, EyeSlashOutline } from "flowbite-svelte-icons";
  import { push } from "svelte-spa-router";

  import { post } from "../utils/httpRequests";
  import { authHeader } from "../utils/stores";

  let passwordShow: boolean = false;
  let response: {[key: string]: any}
  let waitingForPromise: boolean = false;
  let error: boolean = false;
  let email: string, password: string;

  async function postLogin(event: Event): Promise<void> {
    waitingForPromise = true; //show loading button
    event.preventDefault(); //disable page reload after form submission

    //send post request and wait for response
    response = await post("login", {"email": email, "password": password});

    if (response.status === 200) {
      authHeader.setToken(response.access_token)
      //if it was successfull, forward to different page
      push("/userinfo")
    }
    else {
      error = true; //display error message
      waitingForPromise = false;
    }
  }

  function disableError(): void {
    error = false
  }
</script>


<div class="flex flex-col w-full h-full justify-evenly items-center">
  <Heading tag="h1" class="w-fit" customSize="text-2xl text-center font-extrabold md:text-5xl lg:text-6xl">
    Welcome to <Span gradient>Project W</Span>!
  </Heading>

  <div class="w-full">
    <form class="mx-auto max-w-lg" on:submit={postLogin}>
      <div class="mb-6">
        <Label for="email" color={error ? "red" : "gray"} class="mb-2">Email address</Label>
        <Input type="email" id="email" color={error ? "red" : "base"} placeholder="alice@example.com" required bind:value={email} on:input={disableError}/>
      </div>

      <div class="mb-6">
        <Label for="password" color={error ? "red" : "gray"} class="mb-2">Password</Label>
        <Input type={passwordShow ? "text" : "password"} id="password" color={error ? "red" : "base"} placeholder={passwordShow ? "alice's password" : "••••••••••••••••"} required bind:value={password} on:input={disableError}>
          <button type="button" slot="right" on:click={() => (passwordShow = !passwordShow)} class="bg-transparent">
            {#if passwordShow}
              <EyeOutline class="w-6 h-6" />
            {:else}
              <EyeSlashOutline class="w-6 h-6" />
            {/if}
          </button>
        </Input>
      </div>

      {#if waitingForPromise}
        <Button type="submit" disabled>
          <Spinner class="me-3" size="4" color="white" />Loading ...
        </Button>
      {:else}
        <Button type="submit">Login</Button>
      {/if}

      {#if error}
        <Helper class="mt-2" color="red"><span class="font-medium">Login failed!</span> {response.msg}</Helper>
      {/if}
    </form>
  </div>
</div>
