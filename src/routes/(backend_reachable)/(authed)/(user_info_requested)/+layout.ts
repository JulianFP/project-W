import { auth } from "$lib/utils/global_state.svelte";
import { BackendCommError } from "$lib/utils/httpRequests.svelte";
import { getLoggedIn } from "$lib/utils/httpRequestsAuth.svelte";
import type { components } from "$lib/utils/schema";
import { error } from "@sveltejs/kit";
import type { LayoutLoad } from "./$types";

type User = components["schemas"]["User"];

export const load: LayoutLoad = async ({ fetch, depends }) => {
	depends("app:user_info");
	await auth.awaitLoggedIn;
	const user_info_from_check = auth.getUserDataFromCheck();
	if (user_info_from_check != null) {
		console.log(user_info_from_check);
		return { user_info: user_info_from_check };
	}
	if (auth.loggedIn) {
		try {
			const user_info = await getLoggedIn<User>("users/info", {}, {}, fetch);
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
