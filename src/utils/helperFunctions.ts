import { querystring } from "svelte-spa-router";
import type { Readable } from "svelte/store";

//handles subscribe/unsubscribe to a store to reduce code reuse/boilerplate
export function getStoreStringValue(store: Readable<string|undefined>): string {
  let storeVal: string = "";
  const unsubscribe = store.subscribe((value) => {
    if(typeof value === "string") storeVal = value;
  });

  unsubscribe();
  return storeVal;
}

//parse a query string from the current hash based route 
export function getParams(): {[key: string]: any} {
  const params = new URLSearchParams(getStoreStringValue(querystring));

  return Object.fromEntries(params);
}
