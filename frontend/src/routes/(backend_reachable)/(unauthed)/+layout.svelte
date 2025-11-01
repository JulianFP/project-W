<script lang="ts">
	import { Heading, Span } from "flowbite-svelte";
	import WaitingForGoto from "$lib/components/waitingForGoto.svelte";
	import { auth, routing } from "$lib/utils/global_state.svelte";

	$effect(() => {
		if (auth.loggedIn && auth.loggedInSettled) {
			routing.login_forward();
		}
	});

	let { children } = $props();
</script>
{#await auth.awaitLoggedIn}
  <WaitingForGoto/>
{:then}
  {#if auth.loggedIn}
    {#await routing.login_forward()}
      <WaitingForGoto/>
    {/await}
  {:else}
    <div class="flex-1 flex flex-col gap-8 w-full justify-evenly items-center">
      <Heading tag="h1" class="w-fit text-2xl text-center font-extrabold sm:text-4xl md:text-5xl lg:text-6xl">
        Welcome to <Span gradient="skyToEmerald">Project W</Span>!
      </Heading>
      <div class="w-full">
        {@render children?.()}
      </div>
    </div>
  {/if}
{/await}
