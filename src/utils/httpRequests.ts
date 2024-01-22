import { apiURL } from "./backendConfig"

async function getNoJWT(route: string) {
  const response = await fetch(apiURL + route);
  const responseObject = await response.json();
  return responseObject;
}

export async function postNoJWT(route: string, params: {[key: string]: string}) {
  const form: FormData = new FormData();
  for (let key: string in params) {
    form.set(key, params[key]);
  };

  let returnObj: {[key: string]: any};

  try {
    const response: {[key: string]: any} = await fetch(apiURL + route, {
      method: "POST",
      body: form,
      credentials: "same-origin"
    });
    const responseContent: {[key: string]: any} = await response.json();
    returnObj = Object.assign(response, responseContent);
  }
  catch (error) {
    returnObj = {
      ok: false,
      status: 404,
      message: error.message
    }
  }
  return returnObj;
}
