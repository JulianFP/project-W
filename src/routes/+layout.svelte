<script lang="ts">
import "../app.css";
import { PUBLIC_BACKEND_BASE_URL } from "$env/static/public";
import { routing } from "$lib/utils/global_state.svelte";
import { alerts, auth } from "$lib/utils/global_state.svelte";
import type { components } from "$lib/utils/schema";
import {
	Alert,
	Avatar,
	Banner,
	DarkMode,
	Dropdown,
	DropdownDivider,
	DropdownItem,
	Footer,
	FooterBrand,
	FooterCopyright,
	FooterLink,
	FooterLinkGroup,
	NavBrand,
	NavHamburger,
	NavLi,
	NavUl,
	Navbar,
} from "flowbite-svelte";
import {
	AdjustmentsHorizontalSolid,
	BullhornSolid,
	GithubSolid,
	InfoCircleSolid,
	LockSolid,
	UserEditSolid,
} from "flowbite-svelte-icons";
import type { Snippet } from "svelte";

let dropDownOpen = $state(false);

type Data = {
	about: components["schemas"]["AboutResponse"];
	user_info: components["schemas"]["User"];
};
interface Props {
	data: Data;
	children: Snippet;
}
let { data, children }: Props = $props();
</script>
<div class="min-h-screen flex flex-col gap-8">
  <header>
    <Navbar class="px-2 sm:px-4 py-1.5 bg-slate-300 dark:bg-slate-900">
      <NavHamburger />
      <NavBrand href="#/">
        <!--TODO add icon like this: <img src="/images/flowbite-svelte-icon-logo.svg" class="me-3 h-6 sm:h-9" alt="Flowbite Logo" />-->
        <!-- self-center: x/&y centering for flex item, whitespace-nowrap: text should not wrap, text-xl/font-semibold: font size/type-->
        <span class="self-center whitespace-nowrap text-xl font-semibold dark:text-white">Project W</span>
      </NavBrand>
      <div class="flex gap-2 sm:gap-4 md:order-2">
        <DarkMode/>
        {#if auth.loggedIn}
          <Avatar id="avatar-menu" class="cursor-pointer"/>
        {/if}
      </div>
      {#if auth.loggedIn}
        <Dropdown simple placement="bottom" triggeredBy="#avatar-menu" activeUrl={routing.location} bind:isOpen={dropDownOpen}>
          <DropdownItem href="#/account/info" onclick={() => {dropDownOpen = false}}><UserEditSolid class="inline mr-2"/>Account</DropdownItem>
          <DropdownItem href="#/account/security" onclick={() => {dropDownOpen = false}}><LockSolid class="inline mr-2"/>Security</DropdownItem>
          <DropdownItem href="#/account/default_settings" onclick={() => {dropDownOpen = false}}><AdjustmentsHorizontalSolid class="inline mr-2"/>Default settings</DropdownItem>
          <DropdownDivider />
          <DropdownItem class="cursor-pointer" onclick={() => {dropDownOpen = false; auth.forgetToken()}}>Log out</DropdownItem>
        </Dropdown>
      {/if}
      <NavUl activeUrl={routing.location}>
        <NavLi href="#/">Home</NavLi>
        <NavLi href="#/about">About</NavLi>
        <NavLi href="https://github.com/JulianFP/project-W" target="_blank" rel="noopener noreferrer"><GithubSolid class="mx-auto"/></NavLi>
      </NavUl>
    </Navbar>

    {#each data.about.site_banners as banner}
      <Banner color={banner.urgency >= 200 ? "primary" : "gray"} class={`relative md:p-3 p-1.5 ${banner.urgency >= 200 ? "bg-primary-500" : ""}`} dismissable={false}>
        <div class={banner.urgency >= 100 && banner.urgency < 200 ? "text-primary-700 dark:text-primary-600" : "text-gray-900 dark:text-white"}>
          <BullhornSolid size="sm" class="inline mr-2"/>
          {@html banner.html}
        </div>
      </Banner>
    {/each}

    {#each alerts as alert}
      <Alert color={alert.color} dismissable class="m-2">
        {#snippet icon()}<InfoCircleSolid class="w-4 h-4" />{/snippet}
        {alert.msg}
      </Alert>
    {/each}
  </header>

  <main class="flex-1 flex flex-col mx-4">
    {@render children()}
  </main>

  <Footer class="mx-4 mb-4" footerType="logo">
    <div class="sm:flex sm:items-center sm:justify-between sm:gap-6">
      <FooterBrand href="#/" name="Project W"/>
      <FooterLinkGroup class="flex flex-wrap items-center gap-y-2">
        <FooterLink href="#/about">About</FooterLink>
        {#if data.about.imprint}
          <FooterLink href="#/imprint">Imprint</FooterLink>
        {/if}
        {#if Object.keys(data.about.terms_of_services).length !== 0}
          <FooterLink href="#/tos">Terms of Services</FooterLink>
        {/if}
        <FooterLink href="https://project-w.readthedocs.io" target="_blank" rel="noopener noreferrer">Docs</FooterLink>
        <FooterLink href={`${PUBLIC_BACKEND_BASE_URL}/docs`} target="_blank" rel="noopener noreferrer">API docs (Swagger)</FooterLink>
        <FooterLink href={`${PUBLIC_BACKEND_BASE_URL}/redoc`} target="_blank" rel="noopener noreferrer">API docs (Redoc)</FooterLink>
        <FooterLink href="https://github.com/JulianFP/project-W" target="_blank" rel="noopener noreferrer"><GithubSolid class="inline mr-2"/>Backend</FooterLink>
        <FooterLink href="https://github.com/JulianFP/project-W-frontend" target="_blank" rel="noopener noreferrer"><GithubSolid class="inline mr-2"/>Frontend</FooterLink>
        <FooterLink href="https://github.com/JulianFP/project-W-runner" target="_blank" rel="noopener noreferrer"><GithubSolid class="inline mr-2"/>Runner</FooterLink>
      </FooterLinkGroup>
    </div>
    <hr class="my-6 lg:my-8 border-gray-200 dark:border-gray-700"/>
    <FooterCopyright href="https://github.com/JulianFP/project-W/blob/main/COPYING.md" target="_blank" rel="noopener noreferrer" by="Julian Partanen and contributors (click to see all contributors)." year={2025}/>
  </Footer>
</div>
