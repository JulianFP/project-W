<script lang="ts">
  import { Heading } from "flowbite-svelte";

  export let title: string;
</script>

<div class="flex flex-col gap-8 max-w-2xl mx-auto my-8">
  <Heading tag="h2" class="w-fit">
    {title}
  </Heading>

  <slot />
</div>
