import { writable } from "svelte/store";
import type { Writable } from "svelte/store";

const loggedInWrit: Writable<boolean> = writable(false);
function createAuthHeaderStore() {
  const { subscribe, set }: Writable<{[key: string]: string}> = writable({});

  return {
    subscribe,
    setToken: function(token: string): void { 
      set({"Authorization": "Bearer " + token});
      loggedInWrit.set(true);
    },
    forgetToken: function(): void { 
      set({});
      loggedInWrit.set(false);
    }
  }
}

function createAlertsStore() {
  const { subscribe, update }: Writable<{msg: string, color: "dark" | "gray" | "red" | "yellow" | "green" | "orange"}[]> = writable([])

  return {
    subscribe,
    add: function(msg: string, color: "dark" | "gray" | "red" | "yellow" | "green" | "orange" = "dark"): void {
      update((alerts) => alerts.concat({msg: msg, color: color}))
    }
  };
}

export const authHeader = createAuthHeaderStore();
export const loggedIn = { subscribe: loggedInWrit.subscribe };

export const alerts = createAlertsStore();
