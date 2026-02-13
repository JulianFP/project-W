import { PUBLIC_BACKEND_BASE_URL } from "$env/static/public";
import type { CreateClientConfig } from "../generated/client.gen";

export const createClientConfig: CreateClientConfig = (config) => ({
	...config,
	baseUrl: PUBLIC_BACKEND_BASE_URL,
	fetch: (input, init) => {
		return window.fetch(input, {
			...init,
			credentials: "include", //always send cookies
		});
	},
});
