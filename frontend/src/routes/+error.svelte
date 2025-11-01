<script>
	import { Heading, P } from "flowbite-svelte";
	import { page } from "$app/state";
</script>

<div class="flex flex-col gap-4 m-4">
  <Heading tag="h2">
    {`${page.status}: ${page.error !== null ? page.error.message : "Unknown error"}`}
  </Heading>
  <P>You seem to have problems connecting to the Project-W backend. Please check your network connection and reload the page.</P>
</div>
