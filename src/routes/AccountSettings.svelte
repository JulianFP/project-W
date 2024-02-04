<script lang="ts">
  import { Alert, P } from "flowbite-svelte";

  import Waiting from "../components/waiting.svelte";
  import ChangeEmailField from "../components/changeEmailField.svelte";
  import { getLoggedIn } from "./../utils/httpRequests";
  import { loggedIn } from "../utils/stores";
  import { loginForward } from "../utils/navigation";

  $: if(!$loggedIn) loginForward();
</script>

{#await getLoggedIn("userinfo")}
  <Waiting/>
{:then responseUserinfo} 
  {#if responseUserinfo.status !== 200}
    <P>Error: {responseUserinfo.msg}</P>
  {:else}
    {#if !responseUserinfo.activated}
      <Alert class="border-t-4" color="red">
        <span class="font-medium">Account not activated!</span>
        To activate your account please confirm your email address by clicking on the link in the mail you got from us.
      </Alert>
    {:else}
      <Alert class="border-t-4" color="green">
        <span class="font-medium">Account active!</span>
        Your email address is confirmed.
      </Alert>
    {/if}
    <Alert class="border-t-4" color="dark">
      {responseUserinfo.is_admin ? "This is an admin account." : "This is a non-admin account."}
    </Alert>

    <ChangeEmailField defaultValue={responseUserinfo.email}/>
  {/if}
{/await}
