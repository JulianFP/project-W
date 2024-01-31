import { apiURL } from "./backendConfig";
import { loggedIn, authHeader, alerts } from "./stores";

export async function get(route: string, headers: {[key: string]: string} = {}) {
  let returnObj: {[key: string]: any};

  try {
    const response: {[key: string]: any} = await fetch(apiURL + route, {
      method: "GET",
      headers: headers
    });
    const responseContent: {[key: string]: any} = await response.json();
    returnObj = Object.assign(response, responseContent);
  }
  catch (error: unknown) {
    returnObj = {
      ok: false,
      status: 404,
      msg: error.message
    };
  }

  if (returnObj.status === 401){
    authHeader.forgetToken();
    alerts.add("You have been logged out: " + returnObj.msg, "red");
  } 
  return returnObj;
}

export async function getLoggedIn(route: string) {
  let loggedInVal: boolean = false;
  const loggedInUnsubscribe = loggedIn.subscribe((value) => {
    loggedInVal = value;
  });
  let authHeaderVal: {[key: string]: string} = {};
  const authHeaderUnsubscribe = authHeader.subscribe((value) => {
    authHeaderVal = value;
  });

  let returnObj: {[key: string]: any};
  if(loggedInVal) returnObj = get(route, authHeaderVal);
  else returnObj = {
    ok: false,
    status: 401,
    msg: "not logged in"
  };

  loggedInUnsubscribe();
  authHeaderUnsubscribe();
  return returnObj;
}

export async function post(route: string, params: {[key: string]: string}, headers: {[key: string]: string} = {}) {
  const form: FormData = new FormData();
  for (let key in params) {
    form.set(key, params[key]);
  };

  let returnObj: {[key: string]: any};

  try {
    const response: {[key: string]: any} = await fetch(apiURL + route, {
      method: "POST",
      body: form,
      headers: headers
    });
    const responseContent: {[key: string]: any} = await response.json();
    returnObj = Object.assign(response, responseContent);
  }
  catch (error: unknown) {
    returnObj = {
      ok: false,
      status: 404,
      msg: error.message
    };
  }

  if (returnObj.status === 401){
    authHeader.forgetToken();
    alerts.add("You have been logged out: " + returnObj.msg, "red");
  } 
  return returnObj;
}

export async function postLoggedIn(route: string, params: {[key: string]: string}) {
  let loggedInVal: boolean = false;
  const loggedInUnsubscribe = loggedIn.subscribe((value) => {
    loggedInVal = value;
  });
  let authHeaderVal: {[key: string]: string} = {};
  const authHeaderUnsubscribe = authHeader.subscribe((value) => {
    authHeaderVal = value;
  });

  let returnObj: {[key: string]: any};
  if(loggedInVal) returnObj = post(route, params, authHeaderVal);
  else returnObj = {
    ok: false,
    status: 401,
    msg: "not logged in"
  };

  loggedInUnsubscribe();
  authHeaderUnsubscribe();
  return returnObj;
}
