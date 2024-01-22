<script lang="ts">
  import { Heading, Span, Label, Input, Button } from "flowbite-svelte";
  import { EyeOutline, EyeSlashOutline } from "flowbite-svelte-icons";

  let passwordShow: boolean = false;
</script>

<div class="flex flex-col w-full h-full justify-evenly items-center">
  <Heading tag="h1" class="w-fit" customSize="text-2xl text-center font-extrabold md:text-5xl lg:text-6xl">
    Welcome to <Span gradient>Project W</Span>!
  </Heading>
  <div class="w-full">
    <form class="mx-auto max-w-lg">
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
  </div>
</div>
