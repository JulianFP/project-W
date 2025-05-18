class AuthManager {
	#authHeader = $state<Record<string, string>>({});
	loggedIn = $derived<boolean>("Authorization" in this.#authHeader);

	constructor() {
		//on application start: check localStorage for authHeader and login if it is there
		const returnVal: string | null = localStorage.getItem("authHeader");
		this.#authHeader = { Authorization: `Bearer ${returnVal}` };
	}

	setToken(token: string) {
		this.#authHeader = { Authorization: `Bearer ${token}` };
		localStorage.setItem("authHeader", token);
	}

	forgetToken() {
		this.#authHeader = {};
		localStorage.removeItem("authHeader");
	}

	getAuthHeader() {
		return this.#authHeader;
	}
}

export const auth = new AuthManager();

export const alerts = $state<
	{
		msg: string;
		color: "primary" | "gray" | "red" | "yellow" | "green" | "orange";
	}[]
>([]);
