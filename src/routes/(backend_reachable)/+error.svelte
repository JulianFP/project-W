<script>
import { page } from "$app/state";
import CenterPage from "$lib/components/centerPage.svelte";
import { P } from "flowbite-svelte";
</script>

<CenterPage title={`${page.status}: ${page.error !== null ? page.error.message : "Unknown error"}`}>
  <div>
    <P>Oops! You must have taken the wrong turn somewhere...</P>
  </div>
</CenterPage>
