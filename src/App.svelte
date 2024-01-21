<script lang="ts">
  import { Navbar, NavBrand, NavHamburger, NavUl, NavLi, DarkMode, Label, Input, Button } from 'flowbite-svelte';
  import GithubIcon from 'flowbite-svelte-icons/GithubSolid.svelte'
  let names = [ "a", "b" ];
</script>
<div class="min-h-screen bg-white dark:bg-slate-950">
  <Navbar  >
    <NavBrand href="/">
      <!--TODO add icon like this: <img src="/images/flowbite-svelte-icon-logo.svg" class="me-3 h-6 sm:h-9" alt="Flowbite Logo" />-->
      <span class="self-center whitespace-nowrap text-xl font-semibold dark:text-white">Project W</span>
    </NavBrand>
    <NavHamburger  />
    <NavUl >
      <NavLi href="/">Home</NavLi>
      <NavLi href="/about">About</NavLi>
      <NavLi href="/docs/components/navbar">Navbar</NavLi>
      <NavLi href="/pricing">Contact</NavLi>
      <NavLi href="/contact">Github</NavLi>
      <Button color="alternative">
        Github <GithubIcon />
      </Button>
    </NavUl>
  </Navbar>
  <main class="w-full mx-auto">
    <DarkMode />
    <form>
      <div class="mb-6">
        <Label for="email" class="mb-2">Email address</Label>
        <Input type="email" id="email" placeholder="alice@example.com" required />
      </div>
      <div class="mb-6">
        <Label for="password" class="mb-2">Password</Label>
        <Input type="password" id="password" placeholder="••••••••••••" required />
      </div>
      <Button type="submit">Login</Button>
    </form>
    {#each names as name}
      <p class="text-base text-gray-900 dark:text-white">{name}</p>
    {/each}
  </main>
</div>
