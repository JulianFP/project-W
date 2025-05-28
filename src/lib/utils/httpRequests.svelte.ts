import { PUBLIC_BACKEND_BASE_URL } from "$env/static/public";
import { alerts, auth } from "./global_state.svelte";
import { routing } from "./global_state.svelte";
import type { components } from "./schema";

type ValidationError = components["schemas"]["ValidationError"];

type HTTPErrorObject = {
	detail: string | ValidationError[];
};

export class BackendCommError extends Error {
	status: number;

	constructor(status: number, detail: string) {
		super(detail);
		this.status = status;
	}
}

async function response_parser<ResponseType>(
	response: Response,
): Promise<ResponseType> {
	const contentType = response.headers.get("content-type");
	let is_json = false;
	if (contentType?.includes("application/json")) {
		is_json = true;
	}
	if (!response.ok) {
		let detail = "Unknown backend communication error";
		if (is_json) {
			const json_response: HTTPErrorObject = await response.json();
			if (typeof json_response.detail === "string") {
				detail = json_response.detail;
			} else {
				detail = "";
				for (let i = 0; i < json_response.detail.length; i++) {
					detail += `${json_response.detail[i].loc}: ${json_response.detail[i].msg}`;
					if (i + 1 < json_response.detail.length) {
						detail += "; ";
					}
				}
			}
		}
		throw new BackendCommError(response.status, detail);
	}
	if (!is_json) {
		throw new BackendCommError(
			response.status,
			"Backend returned non-json value",
		);
	}
	const result: ResponseType = await response.json();
	return result;
}

async function loggedInWrapper<ResponseType>(
	query_method: () => Promise<ResponseType>,
	depth = 0,
): Promise<ResponseType> {
	if (auth.loggedIn) {
		try {
			return await query_method();
		} catch (error: unknown) {
			if (error instanceof BackendCommError && error.status === 401) {
				//update and try again (maybe the user logged in in a different tab?)
				if (depth < 0) {
					auth.updateTokenFromStorage();
					return await loggedInWrapper(query_method, depth + 1);
				}
				auth.forgetToken();
				alerts.push({
					msg: `You have been logged out: ${error.message}`,
					color: "red",
				});
				routing.dest_forward();
			}
			throw error;
		}
	} else if (depth < 0) {
		auth.updateTokenFromStorage();
		return await loggedInWrapper(query_method, depth + 1);
	} else {
		auth.forgetToken();
		alerts.push({
			msg: "You are not logged in anymore",
			color: "red",
		});
		routing.dest_forward();
		throw new BackendCommError(401, "Not logged in");
	}
}

export async function get<ResponseType>(
	route: string,
	args: Record<string, string> = {},
	headers: Record<string, string> = {},
	fetch = window.fetch,
): Promise<ResponseType> {
	const argsObj: URLSearchParams = new URLSearchParams(args);
	const response: Response = await fetch(
		`${PUBLIC_BACKEND_BASE_URL}/api/${route}?${argsObj.toString()}`,
		{
			method: "GET",
			headers: headers,
		},
	);
	return await response_parser<ResponseType>(response);
}

export async function getLoggedIn<ResponseType>(
	route: string,
	args: Record<string, string> = {},
	fetch = window.fetch,
): Promise<ResponseType> {
	const query_method = async () => {
		return await get<ResponseType>(route, args, auth.getAuthHeader(), fetch);
	};
	return loggedInWrapper<ResponseType>(query_method);
}

export async function post<ResponseType>(
	route: string,
	body: Record<string, string> = {},
	body_as_form_url_encoded = false,
	args: Record<string, string> = {},
	headers: Record<string, string> = {},
	fetch = window.fetch,
): Promise<ResponseType> {
	let response: Response;
	const argsObj: URLSearchParams = new URLSearchParams(args);
	if (body_as_form_url_encoded) {
		const formData = new URLSearchParams(body);
		response = await fetch(
			`${PUBLIC_BACKEND_BASE_URL}/api/${route}?${argsObj.toString()}`,
			{
				method: "POST",
				headers: {
					"Content-Type": "application/x-www-form-urlencoded",
					...headers,
				},
				body: formData,
			},
		);
	} else {
		response = await fetch(
			`${PUBLIC_BACKEND_BASE_URL}/api/${route}?${argsObj.toString()}`,
			{
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					...headers,
				},
				body: JSON.stringify(body),
			},
		);
	}
	return await response_parser<ResponseType>(response);
}

export async function postLoggedIn<ResponseType>(
	route: string,
	body: Record<string, string> = {},
	body_as_form_url_encoded = false,
	args: Record<string, string> = {},
	fetch = window.fetch,
): Promise<ResponseType> {
	const query_method = async () => {
		return await post<ResponseType>(
			route,
			body,
			body_as_form_url_encoded,
			args,
			auth.getAuthHeader(),
			fetch,
		);
	};
	return await loggedInWrapper<ResponseType>(query_method);
}

export async function delet<ResponseType>(
	route: string,
	body: Record<string, string> = {},
	args: Record<string, string> = {},
	headers: Record<string, string> = {},
	fetch = window.fetch,
): Promise<ResponseType> {
	const argsObj: URLSearchParams = new URLSearchParams(args);
	const response: Response = await fetch(
		`${PUBLIC_BACKEND_BASE_URL}/api/${route}?${argsObj.toString()}`,
		{
			method: "DELETE",
			headers: {
				"Content-Type": "application/json",
				...headers,
			},
			body: JSON.stringify(body),
		},
	);
	return await response_parser<ResponseType>(response);
}

export async function deletLoggedIn<ResponseType>(
	route: string,
	body: Record<string, string> = {},
	args: Record<string, string> = {},
	fetch = window.fetch,
): Promise<ResponseType> {
	const query_method = async () => {
		return await delet<ResponseType>(
			route,
			body,
			args,
			auth.getAuthHeader(),
			fetch,
		);
	};
	return loggedInWrapper<ResponseType>(query_method);
}
