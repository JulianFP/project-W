import { Writable, writable } from "svelte/store";
import { getNoJWT } from "./httpRequests.ts"

function createTokenStore() {
  const { subscribe, set, update} = writable(0);

  return {
    subscribe,
    login: async function(username: string, password: string): void {
      return getNoJWT("login")
    },
    forgetToken: function(): void { set(0) }
  }
}

export const token = createTokenStore();

