
import boto3
from botocore.exceptions import ClientError

from Email.base import Mailer
from Email.config import (
    AWS_PROFILE,
    AWS_REGION,
    SES_CONFIGURATION_SET,
    SES_FROM_EMAIL,
    SES_REPLY_TO,
)


class SESMailer(Mailer):
    """Send email using Amazon SES v2."""

    def __init__(self):
        if AWS_PROFILE:
            session = boto3.Session(
                profile_name=AWS_PROFILE,
                region_name=AWS_REGION,
            )
            self.client = session.client("sesv2")
        else:
            self.client = boto3.client(
                "sesv2",
                region_name=AWS_REGION,
            )

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        token: str = None,
        from_email: str = None,
        reply_to: str = None,
        **kwargs,
    ) -> str:
        sender = from_email or kwargs.get("from_email") or SES_FROM_EMAIL
        reply = reply_to or kwargs.get("reply_to") or sender or SES_REPLY_TO
        disp_name = kwargs.get("display_name")

        from Email.tracking_utils import prepare_tracked_email_bodies
        html_body, text_body = prepare_tracked_email_bodies(
            body=body,
            token=token,
            sender_email=sender,
        )

        from_header = f'"{disp_name}" <{sender}>' if disp_name else sender

        send_params = {
            "FromEmailAddress": from_header,
            "Destination": {"ToAddresses": [to_email]},
            "Content": {
                "Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": text_body, "Charset": "UTF-8"},
                        "Html": {"Data": html_body, "Charset": "UTF-8"},
                    },
                }
            },
        }

        if reply:
            send_params["ReplyToAddresses"] = [reply]

        if SES_CONFIGURATION_SET:
            send_params["ConfigurationSetName"] = SES_CONFIGURATION_SET

        try:
            response = self.client.send_email(**send_params)
            return response["MessageId"]
        except ClientError:
            # Let the existing campaign worker record the failure.
            raise
