import { BackendCommError, get } from "$lib/utils/httpRequests.svelte";
import type { components } from "$lib/utils/schema";
import { error } from "@sveltejs/kit";
import type { PageLoad } from "./$types";

type AboutResponse = components["schemas"]["AboutResponse"];

export const load: PageLoad = async ({ fetch }) => {
	try {
		const about = await get<AboutResponse>("about", {}, {}, fetch);
		return { about: about };
	} catch (err: unknown) {
		if (err instanceof BackendCommError) {
			error(err.status, err.message);
		} else {
			error(400, "Unknown error occured while getting about info from backend");
		}
	}
};
