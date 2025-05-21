<script lang="ts">
import { auth, routing } from "$lib/utils/global_state.svelte";
import { error } from "@sveltejs/kit";

const token = routing.querystring.get("token");
if (token) {
	auth.setToken(token);
} else {
	error(400, "Didn't receive a token as querystring");
}
</script>
