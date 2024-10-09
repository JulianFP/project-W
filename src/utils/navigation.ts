import { get } from "svelte/store";
import { routing } from "./stores";

export function loginForward(): void {
	const locationVal: string = get(routing).location;
	let newParams: Record<string, string> | null = null;

	if (locationVal && locationVal !== "/") newParams = { dest: locationVal };

	routing.set({ destination: "/login", params: newParams });
}

export function destForward(): void {
	const destination: string | null = get(routing).querystring.get("dest");
	console.log(`destForward called with destination ${destination}`);

	if (destination)
		routing.set({ destination: destination, removeParams: ["dest"] });
	else routing.set({ destination: "/" });
}
