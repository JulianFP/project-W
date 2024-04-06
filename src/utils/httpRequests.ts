import { loggedIn, authHeader, alerts } from "./stores";

export async function get(route: string, args: {[key: string]: string} = {}, headers: {[key: string]: string} = {}): Promise<{[key: string]: any}> {
  const argsObj: URLSearchParams = new URLSearchParams(args);

  let returnObj: {[key: string]: any};

  try {
    const response: Response = await fetch(import.meta.env.VITE_BACKEND_BASE_URL + "/api/" + route + "?" + argsObj.toString(), {
      method: "GET",
      headers: headers
    });
    const contentType = response.headers.get("content-type");
    if(!contentType || !contentType.includes("application/json")) {
      returnObj = {
        ok: false,
        status: response.status,
        msg: "Response not in JSON format. HTTP status code " + response.status.toString()
      }
    }
    else{
      const responseContent: {[key: string]: any} = await response.json();
      returnObj = Object.assign(response, responseContent);
    }
  }
  catch (error: unknown) {
    returnObj = {
      ok: false,
      status: 404,
      msg: error.message
    };
  }

  //401: Token expired, 422: Token was invalidated 
  if (returnObj.status === 401){
    authHeader.forgetToken();
    alerts.add("You have been logged out: " + returnObj.msg, "red");
  } 
  else if (returnObj.status === 422 && returnObj.msg === "Signature verification failed"){
    authHeader.forgetToken();
    alerts.add("You have been logged out: Token was invalidated", "red");
  }
  return returnObj;
}

export async function getLoggedIn(route: string, args: {[key: string]: string} = {}): Promise<{[key: string]: any}> {
  let loggedInVal: boolean = false;
  const loggedInUnsubscribe = loggedIn.subscribe((value) => {
    loggedInVal = value;
  });
  let authHeaderVal: {[key: string]: string} = {};
  const authHeaderUnsubscribe = authHeader.subscribe((value) => {
    authHeaderVal = value;
  });

  let returnObj: {[key: string]: any};
  if(loggedInVal) returnObj = get(route, args, authHeaderVal);
  else returnObj = {
    ok: false,
    status: 401,
    msg: "not logged in"
  }

  loggedInUnsubscribe();
  authHeaderUnsubscribe();
  return returnObj;
}

export async function post(route: string, form: {[key: string]: string|File} = {}, headers: {[key: string]: string} = {}): Promise<{[key: string]: any}> {
  const formObj: FormData = new FormData();
  for (let key in form) {
    formObj.set(key, form[key]);
  }

  let returnObj: {[key: string]: any};

  try {
    const response: Response = await fetch(import.meta.env.VITE_BACKEND_BASE_URL + "/api/" + route, {
      method: "POST",
      body: formObj,
      headers: headers
    });

    const contentType = response.headers.get("content-type");

    //catch http 413 error to display an understandable error message to user
    if(response.status === 413){
      returnObj = {
        ok: false,
        status: 413,
        msg: "Submitted file is too large. Please use smaller files."
      }
    }
    else if(!contentType || !contentType.includes("application/json")) {
      returnObj = {
        ok: false,
        status: response.status,
        msg: "Response not in JSON format. HTTP status code " + response.status.toString()
      }
    }
    else{
      const responseContent: {[key: string]: any} = await response.json();
      returnObj = Object.assign(response, responseContent);
    }
  }
  catch (error: unknown) {
    returnObj = {
      ok: false,
      status: 404,
      msg: error.message
    };
  }

  //401: Token expired, 422: Token was invalidated 
  if (returnObj.status === 401){
    authHeader.forgetToken();
    alerts.add("You have been logged out: " + returnObj.msg, "red");
  } 
  else if (returnObj.status === 422 && returnObj.msg === "Signature verification failed"){
    authHeader.forgetToken();
    alerts.add("You have been logged out: Token was invalidated", "red");
  }
  return returnObj;
}

export async function postLoggedIn(route: string, form: {[key: string]: string|File} = {}): Promise<{[key: string]: any}> {
  let loggedInVal: boolean = false;
  const loggedInUnsubscribe = loggedIn.subscribe((value) => {
    loggedInVal = value;
  });
  let authHeaderVal: {[key: string]: string} = {};
  const authHeaderUnsubscribe = authHeader.subscribe((value) => {
    authHeaderVal = value;
  });

  let returnObj: {[key: string]: any};
  if(loggedInVal) returnObj = post(route, form, authHeaderVal);
  else returnObj = {
    ok: false,
    status: 401,
    msg: "not logged in"
  }

  loggedInUnsubscribe();
  authHeaderUnsubscribe();
  return returnObj;
}
