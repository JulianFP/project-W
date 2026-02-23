import { error as svelte_error } from "@sveltejs/kit";
import { generalAbout } from "$lib/generated";
import { get_error_msg } from "$lib/utils/http_utils";
import type { LayoutLoad } from "./$types";

export const load: LayoutLoad = async ({ fetch }) => {
	const { data, error, response } = await generalAbout({ fetch: fetch });
	if (error) svelte_error(response.status, get_error_msg(error));
	return { about: data };
};
