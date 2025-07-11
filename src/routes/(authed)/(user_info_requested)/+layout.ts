import { auth } from "$lib/utils/global_state.svelte";
import { BackendCommError, getLoggedIn } from "$lib/utils/httpRequests.svelte";
import type { components } from "$lib/utils/schema";
import { error } from "@sveltejs/kit";
import type { LayoutLoad } from "./$types";

type User = components["schemas"]["User"];

export const load: LayoutLoad = async ({ fetch, depends }) => {
	depends("app:user_info");
	if (auth.loggedIn) {
		try {
			const user_info = await getLoggedIn<User>("users/info", {}, fetch);
			return { user_info: user_info };
		} catch (err: unknown) {
			if (err instanceof BackendCommError) {
				error(err.status, err.message);
			} else {
				error(
					400,
					"Unknown error occured while querying user info from backend",
				);
			}
		}
	}
};
