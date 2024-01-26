import { location, querystring, push, replace } from "svelte-spa-router";

export function loginForward(): void {
  let locationVal: string;
  const unsubscribe = location.subscribe((value) => {
    locationVal = value;
  });

  if(locationVal && locationVal !== "/"){
    replace("/login?dest=" + locationVal);
  }
  else{
    replace("/login");
  }

  unsubscribe();
}

export function destForward(): void {
  let querystringVal: string;
  const unsubscribe = querystring.subscribe((value) => {
    querystringVal = value;
  });

  const params = new URLSearchParams(querystringVal);
  const destination: string|null = params.get("dest");
  if(destination) push(destination);
  else push("/");

  unsubscribe();
}
