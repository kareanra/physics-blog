import os

SITE_URL = os.environ.get("SITE_URL", "https://areanraines.com")

_SHELL = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 34rem; margin: 4rem auto; padding: 0 1.5rem; color: #212529; }}
    h1 {{ font-size: 1.4rem; }}
    a {{ color: #0d6efd; }}
  </style>
</head>
<body>
  <h1>{heading}</h1>
  <p>{message}</p>
  <p><a href="{site_url}">&larr; Back to Computational Physics Notes</a></p>
</body>
</html>"""


def _html_response(status_code: int, title: str, heading: str, message: str) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "text/html; charset=utf-8"},
        "body": _SHELL.format(title=title, heading=heading, message=message, site_url=SITE_URL),
    }


def confirmed_page() -> dict:
    return _html_response(
        200,
        "Subscribed",
        "You're subscribed!",
        "You'll get a weekly email with new posts.",
    )


def already_confirmed_page() -> dict:
    return _html_response(
        200,
        "Already subscribed",
        "You're already subscribed",
        "This link has already been used — you're all set.",
    )


def invalid_token_page() -> dict:
    return _html_response(
        400,
        "Link expired",
        "This link is no longer valid",
        "It may have expired or already been used. You can subscribe again from the site.",
    )


def unsubscribed_page() -> dict:
    return _html_response(
        200,
        "Unsubscribed",
        "You've been unsubscribed",
        "You won't receive any more emails from this list.",
    )
