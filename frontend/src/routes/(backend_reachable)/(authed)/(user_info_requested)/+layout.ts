import { error as svelte_error } from "@sveltejs/kit";
import { usersInfo } from "$lib/generated";
import { auth } from "$lib/utils/global_state.svelte";
import { get_error_msg } from "$lib/utils/http_utils";
import type { LayoutLoad } from "./$types";

export const load: LayoutLoad = async ({ fetch, depends }) => {
	depends("app:user_info");
	if (auth.awaitLoggedIn != null) {
		await auth.awaitLoggedIn;
	}
	const user_info_from_check = auth.getUserDataFromCheck();
	if (user_info_from_check != null) {
		return { user_info: user_info_from_check };
	}
	if (auth.loggedIn) {
		const { data, error, response } = await usersInfo({
			fetch: (input, init) => fetch(input, { ...init, credentials: "include" }),
		});
		if (error) svelte_error(response.status, get_error_msg(error));
		return { user_info: data };
	}
};
