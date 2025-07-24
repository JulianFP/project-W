import { auth } from "$lib/utils/global_state.svelte";
import { BackendCommError, getLoggedIn } from "$lib/utils/httpRequests.svelte";
import type { components } from "$lib/utils/schema";
import { error } from "@sveltejs/kit";
import type { PageLoad } from "./$types";

type TokenInfo = components["schemas"]["TokenSecretInfo"];

export const load: PageLoad = async ({ fetch, depends }) => {
	depends("app:token_info");
	if (auth.loggedIn) {
		try {
			const token_info = await getLoggedIn<TokenInfo[]>(
				"users/get_all_token_info",
				{},
				fetch,
			);
			return { token_info: token_info };
		} catch (err: unknown) {
			if (err instanceof BackendCommError) {
				error(err.status, err.message);
			} else {
				error(
					400,
					"Unknown error occured while querying all token infos from the backend",
				);
			}
		}
	}
};
