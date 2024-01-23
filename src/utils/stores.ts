import { writable } from "svelte/store";

function createAuthHeaderStore() {
  const { subscribe, set, update} = writable({});

  return {
    subscribe,
    setToken: function(token: string): void { set({"Authorization": "Bearer " + token}) },
    forgetToken: function(): void { set({}) }
  }
}

export const authHeader = createAuthHeaderStore();
