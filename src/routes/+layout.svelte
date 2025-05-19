<script lang="ts">
import "../app.css";

import { routing } from "$lib/utils/global_state.svelte";

import { alerts, auth } from "$lib/utils/global_state.svelte";
import {
	Alert,
	Avatar,
	DarkMode,
	Dropdown,
	DropdownDivider,
	DropdownItem,
	NavBrand,
	NavHamburger,
	NavLi,
	NavUl,
	Navbar,
} from "flowbite-svelte";
import {
	GithubSolid,
	InfoCircleSolid,
	LockSolid,
	UserEditSolid,
} from "flowbite-svelte-icons";

let dropDownOpen = $state(false);

let { children } = $props();
</script>
<!--fixed: position is relative to browser window, w-full: full width, z-20: 3d pos (closer)-->
<header class="fixed w-full z-20 top-0 start-0">
  <!--px/py: padding in x/y direction (one small screens: larger x padding for touch)-->
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
      <Dropdown placement="bottom" triggeredBy="#avatar-menu" activeUrl={routing.location} bind:isOpen={dropDownOpen}>
        <DropdownItem href="#/account" onclick={() => {dropDownOpen = false}}><UserEditSolid class="inline mr-2"/>Account</DropdownItem>
        <DropdownItem href="#/security" onclick={() => {dropDownOpen = false}}><LockSolid class="inline mr-2"/>Security</DropdownItem>
        <DropdownDivider />
        <DropdownItem onclick={() => {dropDownOpen = false; auth.forgetToken()}}>Log out</DropdownItem>
      </Dropdown>
    {/if}
    <NavUl activeUrl={routing.location}>
      <NavLi href="#/">Home</NavLi>
      <NavLi href="#/about">About</NavLi>
      <NavLi href="https://project-w.readthedocs.io" target="_blank" rel="noopener noreferrer">Docs</NavLi>
      <NavLi href="https://github.com/JulianFP/project-W" target="_blank" rel="noopener noreferrer"><GithubSolid class="mx-auto"/></NavLi>
    </NavUl>
  </Navbar>

  {#each alerts as alert}
    <Alert color={alert.color} dismissable class="m-2">
      {#snippet icon()}<InfoCircleSolid class="w-4 h-4" />{/snippet}
      {alert.msg}
    </Alert>
  {/each}
</header>


<!--flex: required for h-full of child to work, w-screen: width to screen width min-h-dvh: dynamic viewport height -->
<main class="flex w-full min-h-dvh">
  <!--overflow-auto: adds scroll bar only if overflow happens (under navbar), w-full: width to parent width, min-h-full: height to parent width (always), px-4: padding to left/right of screen, mx-auto: center horizontally, mt-16: margin to top (this will be "under" navbar)-->
  <div class="overflow-auto w-full min-h-full px-4 mt-16">
    {@render children()}
  </div>
</main>
