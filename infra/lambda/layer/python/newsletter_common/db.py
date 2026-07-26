import os
import time
from datetime import timedelta

import boto3

_dynamodb = boto3.resource("dynamodb")

SUBSCRIBERS_TABLE = os.environ.get("SUBSCRIBERS_TABLE", "")
DIGEST_STATE_TABLE = os.environ.get("DIGEST_STATE_TABLE", "")
CONFIRM_TOKEN_INDEX = "confirmToken-index"
UNSUBSCRIBE_TOKEN_INDEX = "unsubscribeToken-index"
PENDING_TTL_SECONDS = int(timedelta(weeks=1).total_seconds())

STATUS_PENDING = "PENDING"
STATUS_CONFIRMED = "CONFIRMED"
STATUS_UNSUBSCRIBED = "UNSUBSCRIBED"

DIGEST_STATE_KEY = "sent-links"


def subscribers_table():
    return _dynamodb.Table(SUBSCRIBERS_TABLE)


def digest_state_table():
    return _dynamodb.Table(DIGEST_STATE_TABLE)


def get_subscriber(email: str):
    resp = subscribers_table().get_item(Key={"email": email})
    return resp.get("Item")


def put_pending(email: str, confirm_token: str, unsubscribe_token: str) -> None:
    now = int(time.time())
    subscribers_table().put_item(
        Item={
            "email": email,
            "status": STATUS_PENDING,
            "confirmToken": confirm_token,
            "unsubscribeToken": unsubscribe_token,
            "createdAt": now,
            "expiresAt": now + PENDING_TTL_SECONDS,
        }
    )


def find_by_index(index_name: str, key_name: str, key_value: str):
    resp = subscribers_table().query(
        IndexName=index_name,
        KeyConditionExpression=f"{key_name} = :v",
        ExpressionAttributeValues={":v": key_value},
        Limit=1,
    )
    items = resp.get("Items", [])
    return items[0] if items else None


def mark_confirmed(email: str) -> None:
    now = int(time.time())
    subscribers_table().update_item(
        Key={"email": email},
        UpdateExpression="SET #s = :confirmed, confirmedAt = :now REMOVE expiresAt",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":confirmed": STATUS_CONFIRMED, ":now": now},
    )


def mark_unsubscribed(email: str) -> None:
    now = int(time.time())
    subscribers_table().update_item(
        Key={"email": email},
        UpdateExpression="SET #s = :unsub, unsubscribedAt = :now",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":unsub": STATUS_UNSUBSCRIBED, ":now": now},
    )


def list_confirmed_subscribers():
    table = subscribers_table()
    items = []
    kwargs = {
        "FilterExpression": "#s = :confirmed",
        "ExpressionAttributeNames": {"#s": "status"},
        "ExpressionAttributeValues": {":confirmed": STATUS_CONFIRMED},
    }
    while True:
        resp = table.scan(**kwargs)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key
    return items


def get_sent_links() -> set:
    resp = digest_state_table().get_item(Key={"stateKey": DIGEST_STATE_KEY})
    item = resp.get("Item")
    if not item:
        return set()
    return set(item.get("sentLinks", []))


def add_sent_links(links: set) -> None:
    if not links:
        return
    existing = get_sent_links()
    merged = existing | links
    digest_state_table().put_item(
        Item={
            "stateKey": DIGEST_STATE_KEY,
            "sentLinks": list(merged),
            "updatedAt": int(time.time()),
        }
    )
