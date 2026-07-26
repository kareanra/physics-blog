from newsletter_common import db
from newsletter_common.pages import already_confirmed_page, confirmed_page, invalid_token_page


def handler(event, _context):
    token = (event.get("queryStringParameters") or {}).get("token")
    if not token:
        return invalid_token_page()

    item = db.find_by_index(db.CONFIRM_TOKEN_INDEX, "confirmToken", token)
    if not item:
        return invalid_token_page()

    if item.get("status") == db.STATUS_CONFIRMED:
        return already_confirmed_page()

    db.mark_confirmed(item["email"])
    return confirmed_page()
