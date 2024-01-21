<script lang="ts">
  import { Navbar, NavBrand, NavHamburger, NavUl, NavLi, DarkMode, Label, Input, Button } from "flowbite-svelte";
  import {GithubSolid, EyeOutline, EyeSlashOutline} from "flowbite-svelte-icons";
  let passwordShow: boolean = false;
</script>

<!--fixed: position is relative to browser window, w-full: full width, z-20: 3d pos (closer)-->
<header class="fixed w-full z-20 top-0 start-0">
  <!--px/py: padding in x/y direction (one small screens: larger x padding for touch)-->
  <Navbar class="px-2 sm:px-4 py-1.5 bg-slate-300 dark:bg-slate-900">
    <NavBrand href="/">
      <!--TODO add icon like this: <img src="/images/flowbite-svelte-icon-logo.svg" class="me-3 h-6 sm:h-9" alt="Flowbite Logo" />-->
      <!-- self-center: x/&y centering for flex item, whitespace-nowrap: text should not wrap, text-xl/font-semibold: font size/type-->
      <span class="self-center whitespace-nowrap text-xl font-semibold dark:text-white">Project W</span>
    </NavBrand>
    <div class="flex md:order-2">
      <DarkMode/>
      <NavHamburger />
    </div>
    <NavUl >
      <NavLi href="/" active={true}>Home</NavLi>
      <NavLi href="/about">About</NavLi>
      <NavLi href="/docs/components/navbar">Navbar</NavLi>
      <NavLi href="/contact">Contact</NavLi>
      <NavLi href="https://github.com/JulianFP/project-W"><GithubSolid class="mx-auto"/></NavLi>
    </NavUl>
  </Navbar>
</header>

<main class="overflow-scroll w-screen min-h-screen flex bg-slate-200 dark:bg-slate-950">
  <!--mt-8: margin to top (this will be "under" navbar), p-2: padding, mx-auto: center, max-w-lg: max width to width of lg-->
  <form class="mt-16 px-4 mx-auto place-self-center flex-initial basis-[42rem]">
    <div class="mb-6">
      <Label for="email" class="mb-2">Email address</Label>
      <Input type="email" id="email" placeholder="alice@example.com" required />
    </div>
    <div class="mb-6">
      <Label for="password" class="mb-2">Password</Label>
      <Input type={passwordShow ? "text" : "password"} id="password" placeholder={passwordShow ? "alice's password" : "••••••••••••••••"} required>
        <button type="button" slot="right" on:click={() => (passwordShow = !passwordShow)} class="bg-transparent">
          {#if passwordShow}
            <EyeOutline class="w-6 h-6" />
          {:else}
            <EyeSlashOutline class="w-6 h-6" />
          {/if}
        </button>
      </Input>
    </div>
    <Button type="submit">Login</Button>
  </form>
</main>

