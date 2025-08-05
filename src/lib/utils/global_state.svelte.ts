import { goto } from "$app/navigation";
import { page } from "$app/state";

class AuthManager {
	//set logged in by default so that it tries to use authenticated route first before failing and logging out
	#first_load = true;
	loggedIn = $state<boolean>(true);

	login() {
		this.loggedIn = true;
	}

	logout(detail: string | null = null) {
		if (detail != null && !this.#first_load) {
			alerts.push({
				msg: `You have been logged out: ${detail}`,
				color: "red",
			});
			this.#first_load = false;
		}
		this.loggedIn = false;
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
