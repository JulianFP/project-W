import { PUBLIC_BACKEND_BASE_URL } from "$env/static/public";
import type { components } from "$lib/utils/schema";
import { error } from "@sveltejs/kit";

type AuthSettings = components["schemas"]["AuthSettings"];

export async function load({ fetch }) {
	const response: Response = await fetch(
		`${PUBLIC_BACKEND_BASE_URL}/api/auth_settings`,
	);
	const contentType = response.headers.get("content-type");
	if (
		!response.ok ||
		!contentType ||
		!contentType.includes("application/json")
	) {
		error(response.status, {
			message: "Error getting auth settings from backend",
		});
	} else {
		const auth_settings: AuthSettings = await response.json();
		return { auth_settings: auth_settings };
	}
}
