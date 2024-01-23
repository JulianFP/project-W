<script lang="ts">
  import type { ComponentType } from "svelte";
  import { Navbar, NavBrand, NavHamburger, NavUl, NavLi, DarkMode } from "flowbite-svelte";
  import { GithubSolid } from "flowbite-svelte-icons";

  import Router from "svelte-spa-router";
  import Login from "./routes/Login.svelte";
  import About from "./routes/About.svelte";
  import UserInfo from "./routes/UserInfo.svelte";

  export const routes: {[key: string]: ComponentType} = {
    "/": Login,
    "/about": About,
    "/userinfo": UserInfo
  };
</script>

<!--fixed: position is relative to browser window, w-full: full width, z-20: 3d pos (closer)-->
<header class="fixed w-full z-20 top-0 start-0">
  <!--px/py: padding in x/y direction (one small screens: larger x padding for touch)-->
  <Navbar class="px-2 sm:px-4 py-1.5 bg-slate-300 dark:bg-slate-900">
    <NavBrand href="#/">
      <!--TODO add icon like this: <img src="/images/flowbite-svelte-icon-logo.svg" class="me-3 h-6 sm:h-9" alt="Flowbite Logo" />-->
      <!-- self-center: x/&y centering for flex item, whitespace-nowrap: text should not wrap, text-xl/font-semibold: font size/type-->
      <span class="self-center whitespace-nowrap text-xl font-semibold dark:text-white">Project W</span>
    </NavBrand>
    <div class="flex md:order-2">
      <DarkMode/>
      <NavHamburger />
    </div>
    <NavUl >
      <NavLi href="#/" active={true}>Home</NavLi>
      <NavLi href="#/about">About</NavLi>
      <NavLi href="#/userinfo">User info</NavLi>
      <NavLi href="#/contact">Contact</NavLi>
      <NavLi href="https://github.com/JulianFP/project-W"><GithubSolid class="mx-auto"/></NavLi>
    </NavUl>
  </Navbar>
</header>

<!--flex: required for h-full of chield to work, w-screen: width to screen width min-h-dvh: dynamic viewport height -->
<main class="flex w-screen min-h-dvh bg-slate-200 dark:bg-slate-950">
  <!--overflow-scroll: adds scroll bar if overflow happens (under navbar), w-full: width to parent width, min-h-full: height to parent width (always), px-4: padding to left/right of screen, mx-auto: center horizontally, mt-16: margin to top (this will be "under" navbar)-->
  <div class="overflow-scroll w-full min-h-full px-4 mt-16">
    <Router {routes}/>
  </div>
</main>

