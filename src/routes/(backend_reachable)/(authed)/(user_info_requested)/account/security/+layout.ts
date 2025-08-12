import { error } from "@sveltejs/kit";
import { BackendCommError, get } from "$lib/utils/httpRequests.svelte";
import type { components } from "$lib/utils/schema";
import type { LayoutLoad } from "./$types";

type AuthSettings = components["schemas"]["AuthSettings"];

export const load: LayoutLoad = async ({ fetch }) => {
	try {
		const auth_settings = await get<AuthSettings>(
			"auth_settings",
			{},
			{},
			fetch,
		);
		return { auth_settings: auth_settings };
	} catch (err: unknown) {
		if (err instanceof BackendCommError) {
			error(err.status, err.message);
		} else {
			error(
				400,
				"Unknown error occured while querying all auth settings from the backend",
			);
		}
	}
};
