import os
from email.message import EmailMessage

import boto3

_ses = boto3.client("sesv2")

FROM_ADDRESS = os.environ.get("SES_FROM_ADDRESS", "")
FROM_NAME = os.environ.get("SES_FROM_NAME", "Computational Physics Notes")
# Without this, SES authorizes ses:SendEmail against an identity derived from
# the FromEmailAddress string itself (e.g. "identity/news@sub.example.com"),
# not the verified domain identity our IAM policy actually grants -- causing
# an AccessDenied even though the domain is verified and IAM looks correct.
SES_IDENTITY_ARN = os.environ.get("SES_IDENTITY_ARN", "")


def send(
    to_address: str,
    subject: str,
    text_body: str,
    html_body: str,
    unsubscribe_url: str | None = None,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{FROM_NAME} <{FROM_ADDRESS}>"
    msg["To"] = to_address
    if unsubscribe_url:
        msg["List-Unsubscribe"] = f"<{unsubscribe_url}>, <mailto:{FROM_ADDRESS}?subject=unsubscribe>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    _ses.send_email(
        FromEmailAddress=f"{FROM_NAME} <{FROM_ADDRESS}>",
        FromEmailAddressIdentityArn=SES_IDENTITY_ARN,
        Destination={"ToAddresses": [to_address]},
        Content={"Raw": {"Data": msg.as_bytes()}},
    )
