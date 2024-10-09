import { querystring, location, push, replace } from "svelte-spa-router";
import { derived, get, writable } from "svelte/store";
import type { Readable, Writable } from "svelte/store";

const loggedInWrit: Writable<boolean> = writable(false);
function createAuthHeaderStore() {
	const { subscribe, set }: Writable<Record<string, string>> = writable({});

	return {
		subscribe,
		setToken: (token: string): void => {
			set({ Authorization: `Bearer ${token}` });
			loggedInWrit.set(true);
			localStorage.setItem("authHeader", token);
		},
		forgetToken: (): void => {
			set({});
			loggedInWrit.set(false);
			localStorage.removeItem("authHeader");
		},
	};
}

function createAlertsStore() {
	const {
		subscribe,
		update,
	}: Writable<
		{
			msg: string;
			color: "dark" | "gray" | "red" | "yellow" | "green" | "orange";
		}[]
	> = writable([]);

	return {
		subscribe,
		add: (
			msg: string,
			color: "dark" | "gray" | "red" | "yellow" | "green" | "orange" = "dark",
		): void => {
			update((alerts) => alerts.concat({ msg: msg, color: color }));
		},
	};
}

export type RoutingObjectType = {
	destination?: string;
	params?: Record<string, string> | null;
	overwriteParams?: boolean;
	removeParams?: string[];
	history?: boolean;
	ensureLoggedIn?: boolean;
};
function createRoutingStore() {
	const derivedQueryString: Readable<{
		location: string;
		querystring: URLSearchParams;
	}> = derived([location, querystring], ([$location, $querystring]) => {
		return {
			location: $location,
			querystring: new URLSearchParams($querystring),
		};
	});

	return {
		subscribe: derivedQueryString.subscribe,
		set: ({
			destination = get(derivedQueryString).location,
			params = null,
			overwriteParams = false,
			removeParams = [],
			history = false,
			ensureLoggedIn = false,
		}: RoutingObjectType): void => {
			if (!ensureLoggedIn || get(loggedIn)) {
				let newParams: URLSearchParams;

				if (params == null)
					newParams = get(derivedQueryString).querystring; //preserve current querystring
				else if (overwriteParams) {
					//overwrite old querystring with new querystring
					newParams = new URLSearchParams(params);
					newParams.sort();
				} else {
					//overlay new querystring on top of old querystring (don't touch keys that were not in params)
					newParams = get(derivedQueryString).querystring;
					for (const key in params) {
						newParams.set(key, params[key]);
					}
					newParams.sort();
				}

				for (const key of removeParams) {
					newParams.delete(key);
				}

				if (history) push(`${destination}?${newParams.toString()}`);
				else replace(`${destination}?${newParams.toString()}`);
			}
		},
	};
}

export const authHeader = createAuthHeaderStore();
export const loggedIn = { subscribe: loggedInWrit.subscribe };

export const alerts = createAlertsStore();

export const routing = createRoutingStore();
