import { apiURL } from "./backendConfig"

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
  catch (error) {
    returnObj = {
      ok: false,
      status: 404,
      msg: error.message
    }
  }
  return returnObj;
}

export async function post(route: string, params: {[key: string]: string}, headers: {[key: string]: string} = {}) {
  const form: FormData = new FormData();
  for (let key: string in params) {
    form.set(key, params[key]);
  };

  let returnObj: {[key: string]: any};

  try {
    const response: {[key: string]: any} = await fetch(apiURL + route, {
      method: "POST",
      body: form,
      header: headers
    });
    const responseContent: {[key: string]: any} = await response.json();
    returnObj = Object.assign(response, responseContent);
  }
  catch (error) {
    returnObj = {
      ok: false,
      status: 404,
      msg: error.message
    }
  }
  return returnObj;
}
