import type { ValidationError } from "$lib/generated";

export type HTTPErrorObject = {
	detail: string | ValidationError[];
};

export function get_error_msg(error: unknown): string {
	if (
		error &&
		typeof error === "object" &&
		"detail" in error &&
		typeof error.detail === "string"
	) {
		return error.detail;
	} else {
		return "Unknown backend communication error";
	}
}
