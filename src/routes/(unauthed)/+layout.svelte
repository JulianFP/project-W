<script lang="ts">
import { auth, routing } from "$lib/utils/global_state.svelte";
import { Heading, Span } from "flowbite-svelte";

$effect(() => {
	if (auth.loggedIn) {
		const destination: string | null = routing.querystring.get("dest");

		if (destination)
			routing.set({ destination: destination, removeParams: ["dest"] });
		else routing.set({ destination: "#/" });
	}
});

let { children } = $props();
</script>
<div class="flex flex-col w-full h-full justify-evenly items-center">
  <Heading tag="h1" class="w-fit text-2xl text-center font-extrabold md:text-5xl lg:text-6xl">
    Welcome to <Span gradient="skyToEmerald">Project W</Span>!
  </Heading>

  <div class="w-full">
    {@render children?.()}
  </div>
</div>
