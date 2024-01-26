<script lang="ts">
import { Spinner, P } from "flowbite-svelte";

import { getLoggedIn } from "./../utils/httpRequests";
import { loggedIn } from "../utils/stores";
import { loginForward } from "../utils/navigation";

$: if(!$loggedIn) loginForward();

let response: Promise<{[key: string]: any}> = getLoggedIn("userinfo");
</script>
{#await response}
  <P><Spinner class="me-3" size="4"/>Loading ...</P>
{:then responseC} 
  {#if !responseC.ok}
    <P>Error: {responseC.msg}</P>
  {:else}
    <P>email address: {responseC.email}</P>
    <P>is admin: {responseC.is_admin}</P>
    <P>is activated: {responseC.activated}</P>
  {/if}
{/await}
