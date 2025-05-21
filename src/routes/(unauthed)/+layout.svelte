<script lang="ts">
import { auth, routing } from "$lib/utils/global_state.svelte";
import { Heading, Span } from "flowbite-svelte";

$effect(() => {
	if (auth.loggedIn) {
		let destination: string | null = localStorage.getItem("dest");
		localStorage.removeItem("dest");

		if (!destination) {
			destination = "#/";
		}

		routing.set({ destination: destination, removeParams: ["token"] });
	}
});

let { children } = $props();
</script>
<div class="flex flex-col w-full h-full justify-evenly items-center">
  <Heading tag="h1" class="w-fit text-2xl text-center font-extrabold sm:text-4xl md:text-5xl lg:text-6xl">
    Welcome to <Span gradient="skyToEmerald">Project W</Span>!
  </Heading>

  <div class="w-full">
    {@render children?.()}
  </div>
</div>
