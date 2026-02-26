<script lang="ts">
	import { Hr, P } from "flowbite-svelte";
	import { PUBLIC_BACKEND_BASE_URL } from "$env/static/public";
	import Button from "$lib/components/button.svelte";
	import type { AuthSettingsResponse } from "$lib/generated";

	type Data = {
		auth_settings: AuthSettingsResponse;
	};

	interface Props {
		data: Data;
	}
	let { data }: Props = $props();
</script>

<div class="flex flex-col mx-auto max-w-lg">
  {#each Object.entries(data.auth_settings.oidc_providers) as [oidc_name, oidc_sett]}
    {#if !oidc_sett.hidden}
      <Button color="alternative" class="flex-none justify-start h-11 my-2" href={`${PUBLIC_BACKEND_BASE_URL}/api/oidc/login/${oidc_name.toLowerCase()}`}>
        {#if oidc_sett.icon_url !== null}
          <img src={oidc_sett.icon_url} alt="Icon of {oidc_name}" width="32" height="32" class="mr-4">
        {/if}
        Log in with {oidc_name}
      </Button>
    {/if}
  {/each}
  {#each Object.entries(data.auth_settings.ldap_providers) as [ldap_name, ldap_sett]}
    {#if !ldap_sett.hidden}
      <Button color="alternative" class="flex-none justify-start h-11 my-2" href={`#/auth/ldap-login/${ldap_name}`}>
        {#if ldap_sett.icon_url !== null}
          <img src={ldap_sett.icon_url} alt="Icon of {ldap_name}" width="32" height="32" class="mr-4">
        {/if}
        Log in with {ldap_name}
      </Button>
    {/if}
  {/each}
  {#if data.auth_settings.local_account.mode === "enabled" || data.auth_settings.local_account.mode === "no_signup"}
    {#if Object.keys(data.auth_settings.oidc_providers).length + Object.keys(data.auth_settings.ldap_providers).length > 0}
      <Hr classes={{ content: "bg-slate-200 dark:bg-slate-950", bg: "bg-primary-700 dark:bg-primary-700 "}} class="w-96 h-1 rounded"><P>or</P></Hr>
    {/if}
    <Button color="alternative" class="flex-none justify-start h-11 my-2" href="#/auth/local/login">
      <img src="/favicon.png" alt="Icon of Project-W" width="32" height="32" class="mr-4">
      Log in with Project-W account
    </Button>
    {#if data.auth_settings.local_account.mode === "enabled"}
      <Button color="alternative" class="flex-none justify-start h-11 my-2" href="#/auth/local/signup">
        <img src="/favicon.png" alt="Icon of Project-W" width="32" height="32" class="mr-4">
        Sign up for Project-W account
      </Button>
    {/if}
  {/if}
</div>
