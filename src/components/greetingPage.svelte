<script lang="ts">
  import { Heading, Span } from "flowbite-svelte";
</script>

<div class="flex flex-col w-full h-full justify-evenly items-center">
  <Heading tag="h1" class="w-fit" customSize="text-2xl text-center font-extrabold md:text-5xl lg:text-6xl">
    Welcome to <Span gradient>Project W</Span>!
  </Heading>

  <div class="w-full">
    <slot />
  </div>
</div>
