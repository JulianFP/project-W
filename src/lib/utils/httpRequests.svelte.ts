import { PUBLIC_BACKEND_BASE_URL } from "$env/static/public";
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
	fetch_method: () => Promise<Response>,
): Promise<ResponseType> {
	try {
		const response = await fetch_method();
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
		return await response.json();
	} catch (err: unknown) {
		if (err instanceof TypeError) {
			throw new BackendCommError(500, err.message);
		}
		throw new BackendCommError(500, "Unknown error");
	}
}

export async function get<ResponseType>(
	route: string,
	args: Record<string, string> | string[][] = {},
	headers: Record<string, string> = {},
	fetch = window.fetch,
	include_credentials = false,
): Promise<ResponseType> {
	const argsObj: URLSearchParams = new URLSearchParams(args);
	const fetch_method = () => {
		return fetch(
			`${PUBLIC_BACKEND_BASE_URL}/api/${route}?${argsObj.toString()}`,
			{
				method: "GET",
				headers: headers,
				credentials: include_credentials ? "include" : "omit",
			},
		);
	};
	return await response_parser<ResponseType>(fetch_method);
}

export async function post<ResponseType>(
	route: string,
	body = {},
	body_as_form_url_encoded = false,
	args: Record<string, string> | string[][] = {},
	headers: Record<string, string> = {},
	fetch = window.fetch,
	include_credentials = false,
): Promise<ResponseType> {
	let fetch_method: () => Promise<Response>;
	const argsObj: URLSearchParams = new URLSearchParams(args);
	if (body_as_form_url_encoded) {
		const formData = new URLSearchParams(body);
		fetch_method = () => {
			return fetch(
				`${PUBLIC_BACKEND_BASE_URL}/api/${route}?${argsObj.toString()}`,
				{
					method: "POST",
					headers: {
						"Content-Type": "application/x-www-form-urlencoded",
						...headers,
					},
					body: formData,
					credentials: include_credentials ? "include" : "omit",
				},
			);
		};
	} else {
		fetch_method = () => {
			return fetch(
				`${PUBLIC_BACKEND_BASE_URL}/api/${route}?${argsObj.toString()}`,
				{
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						...headers,
					},
					body: JSON.stringify(body),
					credentials: include_credentials ? "include" : "omit",
				},
			);
		};
	}
	return await response_parser<ResponseType>(fetch_method);
}

export async function delet<ResponseType>(
	route: string,
	body = {},
	args: Record<string, string> | string[][] = {},
	headers: Record<string, string> = {},
	fetch = window.fetch,
	include_credentials = false,
): Promise<ResponseType> {
	const argsObj: URLSearchParams = new URLSearchParams(args);
	const fetch_method = () => {
		return fetch(
			`${PUBLIC_BACKEND_BASE_URL}/api/${route}?${argsObj.toString()}`,
			{
				method: "DELETE",
				headers: {
					"Content-Type": "application/json",
					...headers,
				},
				body: JSON.stringify(body),
				credentials: include_credentials ? "include" : "omit",
			},
		);
	};
	return await response_parser<ResponseType>(fetch_method);
}
