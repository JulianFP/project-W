<script lang="ts">
import { Heading } from "flowbite-svelte";

interface Props {
	title: string;
	limitWidth?: boolean;
	children?: import("svelte").Snippet;
}

let { title, limitWidth = true, children }: Props = $props();
</script>

<div class={`flex flex-col gap-8 mx-auto w-full ${(limitWidth ? "max-w-screen-md" : "max-w-full lg:mx-24")}`}>
  <Heading tag="h2" class="w-fit">
    {title}
  </Heading>

  {@render children?.()}
</div>
