<script lang="ts">
  import type { ComponentType } from "svelte";
  import { Navbar, NavBrand, NavHamburger, NavUl, NavLi, Avatar, Dropdown, DropdownItem, DarkMode, Alert } from "flowbite-svelte";
  import { GithubSolid, InfoCircleSolid } from "flowbite-svelte-icons";

  import { location } from "svelte-spa-router";

  import Router from "svelte-spa-router";
  import Login from "./routes/Login.svelte";
  import Signup from "./routes/Signup.svelte";
  import Activate from "./routes/Activate.svelte";
  import RequestPasswordReset from "./routes/RequestPasswordReset.svelte";
  import About from "./routes/About.svelte";
  import UserInfo from "./routes/UserInfo.svelte";
  import JobList from "./routes/JobList.svelte";
  import NotFound from "./routes/NotFound.svelte";

  import { loggedIn, authHeader, alerts } from "./utils/stores";

  export const routes: {[key: string]: ComponentType} = {
    "/": JobList,
    "/login": Login,
    "/signup": Signup,
    "/activate": Activate,
    "/requestPasswordReset": RequestPasswordReset,
    "/about": About,
    "/userinfo": UserInfo,
    "*": NotFound
  };

  //on application start: check localStorage for authHeader and login if it is there
  const returnVal: string|null = localStorage.getItem("authHeader");
  if(returnVal) authHeader.setToken(returnVal);

  let dropDownOpen = false;
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
      {#if $loggedIn}
        <Avatar id="avatar-menu" class="cursor-pointer"/>
      {/if}
    </div>
    {#if $loggedIn}
      <Dropdown placement="bottom" triggeredBy="#avatar-menu" activeUrl={"#" + $location} bind:open={dropDownOpen}>
        <!-- TODO: get userinfo for this/>
        <DropdownHeader>
          <span class="block text-sm">Bonnie Green</span>
          <span class="block truncate text-sm font-medium">name@flowbite.com</span>
        </DropdownHeader>
        </!-->
        <DropdownItem href="#/userinfo" on:click={() => {dropDownOpen = false}}>Settings</DropdownItem>
        <DropdownItem slot="footer" on:click={() => {dropDownOpen = false; authHeader.forgetToken()}}>Log out</DropdownItem>
      </Dropdown>
    {/if}
    <NavUl>
      <NavLi href="#/" active={true}>Home</NavLi>
      <NavLi href="#/about">About</NavLi>
      <NavLi href="#/contact">Contact</NavLi>
      <NavLi href="https://github.com/JulianFP/project-W"><GithubSolid class="mx-auto"/></NavLi>
    </NavUl>
  </Navbar>

  {#each $alerts as alert}
    <Alert color={alert.color} dismissable class="m-2">
      <InfoCircleSolid slot="icon" class="w-4 h-4" />
      {alert.msg}
    </Alert>
  {/each}
</header>


<!--flex: required for h-full of chield to work, w-screen: width to screen width min-h-dvh: dynamic viewport height -->
<main class="flex w-screen min-h-dvh bg-slate-200 dark:bg-slate-950">
  <!--overflow-scroll: adds scroll bar if overflow happens (under navbar), w-full: width to parent width, min-h-full: height to parent width (always), px-4: padding to left/right of screen, mx-auto: center horizontally, mt-16: margin to top (this will be "under" navbar)-->
  <div class="overflow-scroll w-full min-h-full px-4 mt-16">
    <Router {routes}/>
  </div>
</main>

