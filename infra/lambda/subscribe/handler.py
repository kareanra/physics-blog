import json
import os

from newsletter_common import db
from newsletter_common.email import send as send_email
from newsletter_common.http import json_response
from newsletter_common.tokens import is_valid_email, new_token

API_BASE_URL = os.environ["API_BASE_URL"]


def handler(event, _context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return json_response(event, 400, {"error": "invalid JSON body"})

    email = (body.get("email") or "").strip().lower()
    if not is_valid_email(email):
        return json_response(event, 400, {"error": "enter a valid email address"})

    existing = db.get_subscriber(email)
    if existing and existing.get("status") == db.STATUS_CONFIRMED:
        return json_response(event, 200, {"status": "already-subscribed"})

    confirm_token = new_token()
    unsubscribe_token = (existing or {}).get("unsubscribeToken") or new_token()
    db.put_pending(email, confirm_token, unsubscribe_token)

    confirm_url = f"{API_BASE_URL}/confirm?token={confirm_token}"
    send_email(
        to_address=email,
        subject="Confirm your subscription to Computational Physics Notes",
        text_body=(
            "Someone (hopefully you) requested email updates from Computational "
            "Physics Notes.\n\nConfirm your subscription:\n"
            f"{confirm_url}\n\n"
            "If you didn't request this, just ignore this email."
        ),
        html_body=(
            "<p>Someone (hopefully you) requested email updates from "
            "<strong>Computational Physics Notes</strong>.</p>"
            f'<p><a href="{confirm_url}">Confirm your subscription</a></p>'
            "<p>If you didn't request this, just ignore this email.</p>"
        ),
    )

    return json_response(event, 202, {"status": "confirmation-sent"})
