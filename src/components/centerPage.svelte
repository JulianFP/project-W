<script lang="ts">
import { Heading } from "flowbite-svelte";

export let title: string;
export let limitWidth = true;
</script>

<div class={`flex flex-col gap-8 mx-auto my-8 ${(limitWidth ? "max-w-screen-md" : "max-w-full lg:mx-24")}`}>
  <Heading tag="h2" class="w-fit">
    {title}
  </Heading>

  <slot />
</div>
