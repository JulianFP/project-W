import { writable } from "svelte/store";
import type { Writable } from "svelte/store";

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

export const authHeader = createAuthHeaderStore();
export const loggedIn = { subscribe: loggedInWrit.subscribe };

export const alerts = createAlertsStore();
