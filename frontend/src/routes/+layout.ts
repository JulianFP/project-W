import { client } from "$lib/generated/client.gen";
import { auth, routing } from "$lib/utils/global_state.svelte";
import type { HTTPErrorObject } from "$lib/utils/http_utils";

client.interceptors.response.use(async (response) => {
	if (response.status === 401 && auth.loggedIn) {
		const contentType = response.headers.get("content-type");
		let detail = "Unknown backend communication error";
		if (contentType?.includes("application/json")) {
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
		auth.logout(detail);
		await routing.dest_forward();
	}
	return response;
});
