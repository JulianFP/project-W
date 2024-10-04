import { querystring, location, push, replace } from "svelte-spa-router";
import { getStoreStringValue } from "./helperFunctions";

export function loginForward(): void {
	const params = new URLSearchParams(getStoreStringValue(querystring));
	const locationVal: string = getStoreStringValue(location);

	if (locationVal && locationVal !== "/") {
		params.set("dest", locationVal);
	}
	let newQueryString = "";
	if (params.size > 0) newQueryString = `?${params.toString()}`;

	replace(`/login${newQueryString}`);
}

export function destForward(): void {
	const params = new URLSearchParams(getStoreStringValue(querystring));

	const destination: string | null = params.get("dest");
	params.delete("dest");

	let newQueryString = "";
	if (params.size > 0) newQueryString = `?${params.toString()}`;

	if (destination) push(destination + newQueryString);
	else push(`/${newQueryString}`);
}

export function preserveQuerystringForward(route: string): void {
	const params = new URLSearchParams(getStoreStringValue(querystring));
	if (params.size > 0) push(`${route}?${params.toString()}`);
	else push(route);
}
