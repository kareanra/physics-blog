import os
from email.message import EmailMessage

import boto3

_ses = boto3.client("sesv2")

FROM_ADDRESS = os.environ.get("SES_FROM_ADDRESS", "")
FROM_NAME = os.environ.get("SES_FROM_NAME", "Computational Physics Notes")


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
        Destination={"ToAddresses": [to_address]},
        Content={"Raw": {"Data": msg.as_bytes()}},
    )
