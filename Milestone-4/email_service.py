import os
import smtplib

from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# Load variables from .env
load_dotenv()


class EmailService:

    def __init__(self):

        self.smtp_server = os.getenv(
            "SMTP_SERVER",
            "smtp.gmail.com"
        ).strip()

        self.smtp_port = int(
            os.getenv(
                "SMTP_PORT",
                "587"
            )
        )

        self.email = os.getenv(
            "SMTP_EMAIL",
            ""
        ).strip()

        # Remove spaces from Google App Password
        self.password = os.getenv(
            "SMTP_PASSWORD",
            ""
        ).replace(" ", "").strip()

        # Safe debugging - password is NOT printed
        print("=" * 60)
        print("EMAIL CONFIGURATION")
        print("=" * 60)
        print("SMTP SERVER:", self.smtp_server)
        print("SMTP PORT:", self.smtp_port)
        print("SMTP EMAIL:", repr(self.email))
        print("SMTP PASSWORD LOADED:", bool(self.password))
        print("=" * 60)


    def is_configured(self):

        return bool(
            self.email
            and
            self.password
        )


    def send_email(
        self,
        recipient,
        subject,
        body
    ):

        if not self.is_configured():

            return {
                "success": False,
                "configured": False,
                "message":
                    "Email integration is not configured."
            }


        if not recipient:

            return {
                "success": False,
                "configured": True,
                "message":
                    "Recipient email is missing."
            }


        try:

            message = MIMEMultipart()

            message["From"] = self.email
            message["To"] = recipient
            message["Subject"] = subject

            message.attach(
                MIMEText(
                    str(body),
                    "plain",
                    "utf-8"
                )
            )


            print(
                "Sending email to:",
                recipient
            )


            with smtplib.SMTP(
                self.smtp_server,
                self.smtp_port,
                timeout=30
            ) as server:

                server.ehlo()

                server.starttls()

                server.ehlo()

                server.login(
                    self.email,
                    self.password
                )

                server.sendmail(
                    self.email,
                    [recipient],
                    message.as_string()
                )


            print(
                "EMAIL SENT SUCCESSFULLY:",
                recipient
            )


            return {
                "success": True,
                "configured": True,
                "message":
                    "Resolution email sent successfully."
            }


        except smtplib.SMTPAuthenticationError as error:

            print(
                "EMAIL AUTHENTICATION ERROR:",
                error
            )

            return {
                "success": False,
                "configured": True,
                "message":
                    "Gmail authentication failed. "
                    "Check your Google App Password."
            }


        except Exception as error:

            print(
                "EMAIL SERVICE ERROR:",
                repr(error)
            )

            return {
                "success": False,
                "configured": True,
                "message":
                    str(error)
            }


    def send_resolution_email(
        self,
        ticket_data,
        result
    ):

        if not isinstance(ticket_data, dict):
            ticket_data = {}

        if not isinstance(result, dict):
            result = {}

        recipient = str(
            ticket_data.get("email") or ""
        ).strip()

        ticket_id = ticket_data.get("id", "")
        title = ticket_data.get("title", "Support Ticket")

        resolution = result.get("resolution", {})
        if isinstance(resolution, dict):
            resolution_text = (
                resolution.get("response")
                or resolution.get("resolution")
                or resolution.get("answer")
                or ""
            )
        else:
            resolution_text = str(resolution)

        if not resolution_text:
            resolution_text = (
                "Your support ticket has been resolved by SupportPilot AI."
            )

        subject = f"[SupportPilot #{ticket_id}] Resolution: {title}"

        body = (
            f"Hello,\n\n"
            f"Here is the AI-generated resolution for your support ticket #{ticket_id} ({title}):\n\n"
            f"{resolution_text}\n\n"
            f"If you have further questions or if your issue persists, please reply or request human support.\n\n"
            f"Best regards,\n"
            f"SupportPilot AI Support Team"
        )

        return self.send_email(
            recipient=recipient,
            subject=subject,
            body=body
        )