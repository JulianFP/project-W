import { PUBLIC_BACKEND_BASE_URL } from "$env/static/public";
import { alerts, auth } from "./global_state.svelte";
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

export async function getLoggedIn<ResponseType>(
	route: string,
	args: Record<string, string> = {},
	fetch = window.fetch,
): Promise<ResponseType> {
	if (auth.loggedIn) {
		try {
			return await get<ResponseType>(route, args, auth.getAuthHeader(), fetch);
		} catch (error: unknown) {
			if (error instanceof BackendCommError && error.status === 401) {
				auth.forgetToken();
				alerts.push({
					msg: `You have been logged out: ${error.message}`,
					color: "red",
				});
			}
			throw error;
		}
	} else {
		throw new BackendCommError(401, "Not logged in");
	}
}

export async function post<ResponseType>(
	route: string,
	body: Record<string, string> = {},
	body_as_form_url_encoded = false,
	headers: Record<string, string> = {},
	fetch = window.fetch,
): Promise<ResponseType> {
	let response: Response;
	if (body_as_form_url_encoded) {
		const formData = new URLSearchParams(body);
		response = await fetch(`${PUBLIC_BACKEND_BASE_URL}/api/${route}`, {
			method: "POST",
			headers: {
				"Content-Type": "application/x-www-form-urlencoded",
				...headers,
			},
			body: formData,
		});
	} else {
		response = await fetch(`${PUBLIC_BACKEND_BASE_URL}/api/${route}`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				...headers,
			},
			body: JSON.stringify(body),
		});
	}
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

export async function postLoggedIn<ResponseType>(
	route: string,
	body: Record<string, string> = {},
	body_as_form_url_encoded = false,
	fetch = window.fetch,
): Promise<ResponseType> {
	if (auth.loggedIn) {
		try {
			return await post<ResponseType>(
				route,
				body,
				body_as_form_url_encoded,
				auth.getAuthHeader(),
				fetch,
			);
		} catch (error: unknown) {
			if (error instanceof BackendCommError && error.status === 401) {
				auth.forgetToken();
				alerts.push({
					msg: `You have been logged out: ${error.message}`,
					color: "red",
				});
			}
			throw error;
		}
	} else {
		throw new BackendCommError(401, "Not logged in");
	}
}
