import { browser } from "$app/environment";
import { goto } from "$app/navigation";
import { page } from "$app/state";
import type { UserResponse } from "$lib/generated";
import { usersInfo } from "$lib/generated";
import { type Client, createClient } from "$lib/generated/client";
import { client } from "$lib/generated/client.gen";

class AuthManager {
	//set logged in by default so that it tries to use authenticated route first before failing and logging out
	#userDataFromCheck: UserResponse | null = null;
	#client: Client;
	loggedIn = $state<boolean>(false);
	loggedInSettled = $state<boolean>(false);
	awaitLoggedIn: Promise<void> | null = null;

	async checkLoggedIn(): Promise<void> {
		//check with its own client because the global client has the login forward interceptor
		const { data, error, response } = await usersInfo({ client: this.#client });
		if (!error && response.status !== 401) {
			this.#userDataFromCheck = data;
			this.loggedIn = true;
		}
		this.loggedInSettled = true;
	}

	constructor() {
		this.#client = createClient({
			...client.getConfig(),
		});
		if (browser) {
			this.awaitLoggedIn = this.checkLoggedIn();
		}
	}

	login() {
		this.loggedIn = true;
	}

	logout(detail: string | null = null) {
		if (detail != null) {
			alerts.push({
				msg: `You have been logged out: ${detail}`,
				color: "red",
			});
		}
		this.loggedIn = false;
	}

	getUserDataFromCheck(): UserResponse | null {
		const userData = this.#userDataFromCheck;
		this.#userDataFromCheck = null;
		return userData;
	}
}

export type RoutingObjectType = {
	destination?: string;
	params?: Record<string, string> | null;
	overwriteParams?: boolean;
	removeParams?: string[];
	history?: boolean;
};

class RoutingManager {
	location = $derived<string>(page.url.hash.split("?")[0]);
	querystring = $derived<URLSearchParams>(
		new URLSearchParams(page.url.hash.split("?")[1]),
	);

	async set({
		destination = this.location,
		params = null,
		overwriteParams = false,
		removeParams = [],
		history = false,
	}: RoutingObjectType): Promise<void> {
		let newParams: URLSearchParams;

		if (params == null)
			newParams = this.querystring; //preserve current querystring
		else if (overwriteParams) {
			//overwrite old querystring with new querystring
			newParams = new URLSearchParams(params);
			newParams.sort();
		} else {
			//overlay new querystring on top of old querystring (don't touch keys that were not in params)
			newParams = this.querystring;
			for (const key in params) {
				newParams.set(key, params[key]);
			}
			newParams.sort();
		}

		for (const key of removeParams) {
			newParams.delete(key);
		}

		const paramString = newParams.toString();
		if (paramString) {
			await goto(`${destination}?${paramString}`, { replaceState: !history });
		} else {
			await goto(`${destination}`, { replaceState: !history });
		}
	}

	async dest_forward() {
		const locationVal: string = this.location;
		if (locationVal && locationVal !== "#/")
			localStorage.setItem("dest", locationVal);
		await this.set({ destination: "#/auth" });
	}

	async login_forward() {
		let destination: string | null = localStorage.getItem("dest");
		localStorage.removeItem("dest");

		if (!destination) {
			destination = "#/";
		}

		await this.set({ destination: destination, removeParams: ["token"] });
	}
}

export const auth = new AuthManager();

export const alerts = $state<
	{
		msg: string;
		color: "primary" | "gray" | "red" | "yellow" | "green" | "orange";
	}[]
>([]);

export const routing = new RoutingManager();
