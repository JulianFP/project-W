import { auth } from "./global_state.svelte";
import { routing } from "./global_state.svelte";
import { BackendCommError, delet, get, post } from "./httpRequests.svelte";

async function login_forwarder<ResponseType>(
	request_method: () => Promise<ResponseType>,
): Promise<ResponseType> {
	try {
		return await request_method();
	} catch (err: unknown) {
		if (
			err instanceof BackendCommError &&
			err.status === 401 &&
			auth.loggedIn
		) {
			auth.logout(err.message);
			await routing.dest_forward();
		}
		throw err;
	}
}

export async function getLoggedIn<ResponseType>(
	route: string,
	args: Record<string, string> | string[][] = {},
	headers: Record<string, string> = {},
	fetch = window.fetch,
): Promise<ResponseType> {
	return await login_forwarder<ResponseType>(() =>
		get<ResponseType>(route, args, headers, fetch, true),
	);
}

export async function postLoggedIn<ResponseType>(
	route: string,
	body = {},
	body_as_form_url_encoded = false,
	args: Record<string, string> | string[][] = {},
	headers: Record<string, string> = {},
	fetch = window.fetch,
): Promise<ResponseType> {
	return await login_forwarder<ResponseType>(() =>
		post<ResponseType>(
			route,
			body,
			body_as_form_url_encoded,
			args,
			headers,
			fetch,
			true,
		),
	);
}

export async function deletLoggedIn<ResponseType>(
	route: string,
	body = {},
	args: Record<string, string> | string[][] = {},
	headers: Record<string, string> = {},
	fetch = window.fetch,
): Promise<ResponseType> {
	return await login_forwarder<ResponseType>(() =>
		delet<ResponseType>(route, body, args, headers, fetch, true),
	);
}
