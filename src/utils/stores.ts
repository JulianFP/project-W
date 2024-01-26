import { writable } from "svelte/store";

function createAuthHeaderStore() {
  const { subscribe, set, update} = writable({});

  return {
    subscribe,
    setToken: function(token: string): void { 
      set({"Authorization": "Bearer " + token});
      loggedIn.set(true);
    },
    forgetToken: function(): void { 
      set({});
      loggedIn.set(false);
    }
  }
}

export const authHeader = createAuthHeaderStore();

export const loggedIn = writable(false);
