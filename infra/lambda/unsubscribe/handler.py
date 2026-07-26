from newsletter_common import db
from newsletter_common.pages import invalid_token_page, unsubscribed_page


def handler(event, _context):
    method = (event.get("requestContext") or {}).get("http", {}).get("method", "GET")
    token = (event.get("queryStringParameters") or {}).get("token")

    if not token:
        return invalid_token_page() if method == "GET" else {"statusCode": 400, "body": ""}

    item = db.find_by_index(db.UNSUBSCRIBE_TOKEN_INDEX, "unsubscribeToken", token)
    if not item:
        return invalid_token_page() if method == "GET" else {"statusCode": 400, "body": ""}

    if item.get("status") != db.STATUS_UNSUBSCRIBED:
        db.mark_unsubscribed(item["email"])

    # RFC 8058 one-click unsubscribe: mail clients POST here with no UI, just
    # want a bare 200 back. Only render the confirmation page for a real click.
    if method == "POST":
        return {"statusCode": 200, "body": ""}
    return unsubscribed_page()
