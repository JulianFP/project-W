<script lang="ts">
import { Heading, Span } from "flowbite-svelte";
interface Props {
	children?: import("svelte").Snippet;
}

let { children }: Props = $props();
</script>

<div class="flex flex-col w-full h-full justify-evenly items-center">
  <Heading tag="h1" class="w-fit text-2xl text-center font-extrabold md:text-5xl lg:text-6xl">
    Welcome to <Span gradient="skyToEmerald">Project W</Span>!
  </Heading>

  <div class="w-full">
    {@render children?.()}
  </div>
</div>
