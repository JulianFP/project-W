<script>
import { P } from "flowbite-svelte";

import { loggedIn } from "../utils/stores";
import { loginForward } from "../utils/navigation";

$: if(!$loggedIn) loginForward();
</script>
<div>
  <P>this is a placeholder and will be replaced with a list of jobs</P>
</div>
