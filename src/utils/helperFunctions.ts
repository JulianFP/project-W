import { querystring, location, replace } from "svelte-spa-router";
import type { Readable } from "svelte/store";

//handles subscribe/unsubscribe to a store to reduce code reuse/boilerplate
export function getStoreStringValue(
	store: Readable<string | undefined>,
): string {
	let storeVal = "";
	const unsubscribe = store.subscribe((value) => {
		if (typeof value === "string") storeVal = value;
	});

	unsubscribe();
	return storeVal;
}

//parse a query string from the current hash based route
export function getParams(): Record<string, string> {
	const params = new URLSearchParams(getStoreStringValue(querystring));

	return Object.fromEntries(params);
}

//set a hash based querystring
export function setParams(params: Record<string, string>): void {
	const paramsObj = new URLSearchParams(getStoreStringValue(querystring));
	for (const key in params) {
		paramsObj.set(key, params[key]);
	}
	paramsObj.sort();

	const currentRoute: string = getStoreStringValue(location);
	replace(`${currentRoute}?${paramsObj.toString()}`);
}

//returns string with new params
export function paramsLoc(params: Record<string, string>): string {
	const paramsObj = new URLSearchParams(getStoreStringValue(querystring));
	for (const key in params) {
		paramsObj.set(key, params[key]);
	}
	paramsObj.sort();

	return `${getStoreStringValue(location)}?${paramsObj.toString()}`;
}
