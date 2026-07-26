import json

# CORS is handled entirely by the HTTP API's own cors_preflight config (see
# newsletter_stack.py), which adds Access-Control-Allow-Origin to real
# responses too, not just OPTIONS preflight -- doing it again here would
# risk a duplicate header that browsers reject.


def json_response(_event: dict, status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
