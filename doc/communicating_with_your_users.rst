Communicating with your users
=============================

As already discussed in :doc:`example_configs` Project-W provides the ability to set an imprint and terms of services. These are meant to be quite static in their contents. They are of course allowed to change (Project-W even explicitly provides mechanisms to update the terms of services), however changing them requires adjusting the config file and restarting the backend to reload it's contents and in general the imprint or tos isn't the best place to give your users weekly or monthly status updates or maintenance notices.

For use cases like that Project-W provides the following two functionalities:

Site banners
------------

You can add a banner to the frontend which will be shown to all users across all pages (similarly to Gitlab's broadcast messages). This banner can contain arbitrary html set by you (although it's contents shouldn't be too long, use anchors/links to an external page for very long content). There is no limit for how many banners can exist at any given time, however in practice having more than 2 or 3 banners on the frontend doesn't result in a very good user experience. Each banner also has an urgency value attached to it which serves two purposes:

1. Banners are sorted by urgency when shown to users, i.e. banners with higher urgency will be shown first regardless of when the banner was created.

2. There are two urgency thresholds: Banners with an urgency of 100 or higher will have their text highlighted, and banners with an urgency of 200 or higher will have their background highlighted. Use this to draw the attention of your users to very important messages.

Creating a banner
``````````````````

To create a new site banner, login as an admin (refer to :ref:`login_with_admin_privileges` for that) and use the ``/api/admins/add_site_banner`` route. After a successful call of this route the new banner will be stored in the database and will be displayed on the frontend to all users (you might have to refresh the site first). If you don't want to use the Swagger UI of your Project-W instance here is the curl command for that:

   .. code-block:: console

      curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" https://<backend url>/api/admins/add_site_banner -d '{"html": "Project-W will be down for maintenance tomorrow between 3 and 5 PM. <a href=\"https://example.org" target=\"_blank\" rel=\"noopener noreferrer\">Click here for our full maintenance schedules.</a>", "urgency": 100}'

Deleting a banner
``````````````````

To delete an existing runner you first need the ID of the banner you want to delete. The ``/api/admins/add_site_banner`` route returned this id when you called it to create the banner. If you forgot it you can also use the ``/api/about`` route to get a list of all banners including their ids.

Now you can call the ``/api/admins/delete_site_banner`` route. With curl this looks like this:

   .. code-block:: console

      curl -X DELETE -H "Authorization: Bearer $TOKEN" https://<backend url>/api/admins/delete_site_banner?banner_id=<banner id>

Sending emails to your users
----------------------------

As an alternative to site banners you can also choose to send an email to all your users. This will reach every user that ever logged in to your instance, not only the active users that regularly visit the website. You might want to do this in conjunction with changing the terms of services, or if your instance got breached and you want to inform your users about their data being stolen (let's just hope this never ever happens. But if it does you now don't have an excuse for not telling your users about it :D).

To do this, login as an admin (refer to :ref:`login_with_admin_privileges` for that) and use the ``/api/admins/send_email_to_all_users`` route. If you don't want to use the Swagger UI of your Project-W instance here is the curl command for that:

   .. code-block:: console

      curl -X POST https://<backend url>/api/admins/send_email_to_all_users -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"subject": "Project-W: Notice about change of the terms of services", "body": "Our Data Privacy Agreement changed\nHere is an overview of all the changes\n\nblabla"}'
