API
===

This page is of interest to developers of Project-W, but also to people who want to write custom clients for it (like bash or python scripts or anything else). If the latter is the case then focus on the client-facing routes and ignore the runner-facing ones.

.. note::
   If you want to develop a client that is intended to replace the current frontend (not just as an addition) then make sure that is has an ``/local/activate``, an ``/auth/local/reset-password`` and an ``/auth/oidc-accept`` route! The backend expects that the client has these since it puts them into the emails it sends to the users and forwards the user the the last one for the OIDC login flow. The first two routes should accept a ``token`` as a query string that contains the activation/password reset token.

.. _general-label:

General
-------

The REST API of the backend is divided into these sections:

1. /api/jobs/*
2. /api/users/*
3. /api/local-account/*
4. /api/oidc/*
5. /api/ldap/*
6. /api/runners/*
7. /api/admins/*

The section 1 to 5 as well as info routes that are in none of these sections should be of interest to you if you want to write your own client. We will call them client-facing routes from now on. The sixth section should be used by runners only (runner-facing), and the seventh is only for administration purposes.

We made the following design decision regarding when to use GET, POST or PUT routes:

- **GET**: Requests are both safe and idempotent
- **PUT**: Requests are not safe but idempotent
- **POST**: Requests are neither safe nor idempotent
- **DELETE**: Like POST but it will always result in a deletion of a resource (while POSTs generally result in a creation of a new resource)

A safe operation is one that doesn't cause a write to the database (only read). An idempotent request is one that returns the same data regardless of how often you request it (e.g. the returned data of the 10th request will be the same as the one of the 1st).

We make use of Pydantic to validate all input and output models of our API. These models are also part of the OpenAPI documentation so that you can use the to craft HTTP requests more easily.

If a route is not successful (http status code not in the 200 range) and the error was created by the backend code (and not the application framework, proxies in between, ...) it will return an ``ErrorResponse`` object which contains a detail with more information about the error (e.g. an error message or a list of inputs that didn't pass type validation)

OpenAPI docs
------------

   We would recommend to visit the OpenAPI docs UI (formerly known as Swagger UI) under `/docs` of a hosted Project-W instance. Alternatively if you prefer every Project-W instance also comes with a Redoc UI under `/redoc`. The API reference below should only be considered as a quick overview, the OpenAPI and Redoc UIs are far superior to this documentation.

Quick overview
--------------

   .. openapi:: ./openapi.json
      :examples:
      :group:
      :format: markdown
