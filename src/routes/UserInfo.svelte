<script lang="ts">
import { Spinner, P } from "flowbite-svelte";

import { get } from "./../utils/httpRequests";
import { authHeader } from "../utils/stores";

let response: Promise<{[key: string]: any}> = get("userinfo", $authHeader);
</script>

{#await response}
  <P><Spinner class="me-3" size="4"/>Loading ...</P>
{:then responseC} 
  {#if !responseC.ok}
    <P>Error: {responseC.message}</P>
    {console.log(responseC)}
  {:else}
    <P>email address: {responseC.email}</P>
    <P>is admin: {responseC.is_admin}</P>
    <P>is activated: {responseC.activated}</P>
  {/if}
{/await}
