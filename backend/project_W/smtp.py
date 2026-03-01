from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from aiosmtplib import (
    SMTP,
    SMTPRecipientRefused,
    SMTPRecipientsRefused,
    SMTPServerDisconnected,
)
from project_W_lib.models.base import EmailValidated

import project_W.dependencies as dp

from .models.setting_models import SMTPSecureEnum, SMTPServerSettings


class SmtpClient:
    client: SMTP
    starttls: bool
    smtp_settings: SMTPServerSettings

    def __init__(self, smtp_settings: SMTPServerSettings) -> None:
        self.smtp_settings = smtp_settings
        ssl = smtp_settings.secure == SMTPSecureEnum.SSL
        self.starttls = smtp_settings.secure == SMTPSecureEnum.STARTTLS
        self.client = SMTP(
            hostname=smtp_settings.hostname,
            port=smtp_settings.port,
            use_tls=ssl,
            start_tls=False,  # connection will be upgraded to starttls manually later on to enforce connection upgrade
        )

    async def open(self):
        dp.logger.info("Trying to connect to SMTP server...")
        await self.client.connect()
        if self.starttls:
            await self.client.starttls()
        if self.smtp_settings.username and self.smtp_settings.password:
            await self.client.login(
                self.smtp_settings.username, self.smtp_settings.password.get_secret_value()
            )

        dp.logger.info("Connected to SMTP server")

    async def close(self):
        dp.logger.info("Closing SMTP connection...")
        self.client.close()

    async def send_email(
        self,
        receiver: EmailValidated | list[EmailValidated],
        msg_type: str,
        msg_subject: str,
        msg_body: str,
    ):
        msg = EmailMessage()
        msg["Subject"] = msg_subject
        msg["From"] = self.smtp_settings.sender_email.root
        if isinstance(receiver, EmailValidated):
            msg["To"] = receiver.root
            receiver_logs = receiver.root
        elif type(receiver) is list:
            msg["Bcc"] = map(lambda email: email.root, receiver)
            receiver_logs = f"{len(receiver)} addresses"
        else:
            raise Exception("Invalid receiver type!")
        msg["Message-ID"] = make_msgid(
            f"Project-W.{msg_type}", self.smtp_settings.sender_email.get_domain()
        )
        msg["Date"] = formatdate(localtime=True)
        msg.set_content(msg_body)

        try:
            await self.client.send_message(msg)
        except (SMTPRecipientRefused, SMTPRecipientsRefused) as e:
            # this error is likely due to the users email becoming invalid i.e. because the mail account got deleted
            dp.logger.error(
                f"The SMTP server refused the send email to recipient {receiver_logs}: {e}"
            )
            return
        except SMTPServerDisconnected:
            # reconnect and try again
            await self.open()
            try:
                await self.client.send_message(msg)
            except (SMTPRecipientRefused, SMTPRecipientsRefused) as e:
                # this error is likely due to the users email becoming invalid i.e. because the mail account got deleted
                dp.logger.error(
                    f"The SMTP server refused the recipient email address {receiver_logs}: {e}"
                )
                return

    async def send_account_activation_email(
        self, receiver: EmailValidated, token: str, client_url: str
    ):
        url = f"{client_url}/local/activate?token={token}"
        msg_body = (
            f"To activate your Project-W account, "
            f"please confirm your email address by clicking on the following link:\n\n"
            f"{url}\n\n"
            f"This link will expire within the next 24 hours. "
            f"After this period you will have to request a new activation email over the website.\n\n"
            f"If you did not sign up for an account please disregard this email."
        )
        msg_subject = "Project-W account activation"
        await self.send_email(receiver, "activation", msg_subject, msg_body)

    async def send_confirm_email_change_email(
        self, receiver: EmailValidated, token: str, client_url: str
    ):
        url = f"{client_url}/local/activate?token={token}"
        msg_body = (
            f"To confirm the change of the email address of your Project-W account\n"
            f"to '{receiver.root}', please click on the following link:\n\n"
            f"{url}\n\n"
            f"The email change will only be performed once you click on this link.\n"
            f"Until then your old address will remain the active email address of your Project-W account.\n\n"
            f"This link will expire within the next 24 hours. "
            f"After this period you will have to re-perform the email changing procedure on the website.\n\n"
            f"If you don't have a Project-W account or didn't request your email to be changed then you can ignore this email."
        )
        msg_subject = "Project-W email address change request"
        await self.send_email(receiver, "mail-change", msg_subject, msg_body)

    async def send_password_reset_email(
        self, receiver: EmailValidated, token: str, client_url: str
    ):
        url = f"{client_url}/auth/local/reset-password?token={token}"
        msg_body = (
            f"To reset the password of your Project-W account, "
            f"please open the following link and enter a new password:\n\n"
            f"{url}\n\n"
            f"This link will expire within the next hour. "
            f"After this period you will have to request a new password reset email over the website.\n\n"
            f"If you did not request a password reset then you can disregard this email"
        )
        msg_subject = "Project-W password reset request"
        await self.send_email(receiver, "reset", msg_subject, msg_body)

    async def send_job_success_email(self, receiver: EmailValidated, job_id: int, client_url: str):
        url = f"{client_url}/"
        msg_body = (
            f"Your Project-W job with id {job_id} has finished successfully!\n"
            f"You can download the transcript under the following url "
            f"by clicking on the download button next to the listed job:\n"
            f"{url}"
        )
        msg_subject = f"Project-W: Job {job_id} finished successfully!"
        await self.send_email(receiver, "notif-success", msg_subject, msg_body)

    async def send_job_failed_email(
        self, receiver: EmailValidated, job_id: int, error_msg: str, client_url: str
    ):
        url = f"{client_url}/"
        msg_body = (
            f"Your Project-W job with id {job_id} was aborted with the following error message:\n\n"
            f"{error_msg}\n\n"
            f"You can try to re-submit your job after ensuring that your job settings are valid. "
            f"You can do so under the following url by clicking on the 'New Job' button.\n"
            f"{url}"
        )
        msg_subject = f"Project-W: Job {job_id} failed!"
        await self.send_email(receiver, "notif-failed", msg_subject, msg_body)

    async def send_account_deletion_reminder(
        self, receivers: list[EmailValidated], client_url: str, days_until_deletion: int
    ):
        url = f"{client_url}/"
        msg_body = (
            f"We noticed that you haven't used the Project-W transcription service {url} for a while.\n"
            f"If you want to keep using Project-W then please use your account within the next {days_until_deletion} days.\n"
            f"Otherwise your account including all it's data will be automatically deleted."
        )
        msg_subject = f"Project-W: {days_until_deletion} days account deletion warning"
        await self.send_email(receivers, "acc-del-warn", msg_subject, msg_body)
