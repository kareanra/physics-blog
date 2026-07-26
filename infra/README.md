# Newsletter infrastructure

AWS CDK (Python) app that provisions the backend for the blog's weekly email
subscription: SES domain identity, DynamoDB storage, four Lambda functions,
an HTTP API, and a weekly EventBridge schedule. See the architecture diagram
and rationale in the project's newsletter plan for the full picture; this
file is just the "how to actually run it" reference.

Everything here deploys into **AWS account `912946686130`** — that's where
the `areanraines.com` Route 53 hosted zone lives, and SES/DNS records need to
land in the same account as the zone. This is *not* the `default` CLI
profile on this machine (that points at a different account), so you need a
dedicated profile before doing anything below.

## One-time setup

1. Add a profile for the target account (adjust `sso_role_name` to whatever
   role you actually have there):

   ```ini
   # ~/.aws/config
   [profile areanraines]
   sso_start_url = https://d-9067d2d549.awsapps.com/start/?plugin_version=chrome_4.0.13#/?plugin_version=chrome_4.0.10&tab=accounts
   sso_region = us-east-1
   sso_account_id = 912946686130
   sso_role_name = <role you have on 912946686130>
   region = us-east-1
   output = json
   ```

2. Log in and confirm it resolves to the right account:

   ```bash
   aws sso login --profile areanraines
   aws sts get-caller-identity --profile areanraines
   ```

3. Install the CDK CLI (Node-based, even for a Python app) and the Python
   deps:

   ```bash
   npm install -g aws-cdk
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. Bootstrap the account/region once:

   ```bash
   AWS_PROFILE=areanraines cdk bootstrap aws://912946686130/us-east-1
   ```

## Deploying

Always synth first — it catches CDK API mistakes and lets you read the
generated CloudFormation before anything touches the account:

```bash
AWS_PROFILE=areanraines cdk synth
AWS_PROFILE=areanraines cdk diff
AWS_PROFILE=areanraines cdk deploy
```

This creates real, billed resources (Lambda, DynamoDB, API Gateway, an ACM
certificate, Route 53 records under `updates.areanraines.com` and
`mail.updates.areanraines.com`, and an SES domain identity). It does **not**
touch the root `areanraines.com` apex or `www` records, so it's isolated
from the separate GitHub Pages custom-domain cutover.

After deploy, confirm SES picked up the DNS records (can take a few minutes
to propagate):

```bash
AWS_PROFILE=areanraines aws sesv2 get-email-identity --email-identity updates.areanraines.com
```

Look for `"VerificationStatus": "SUCCESS"` and `"DkimStatus": "SUCCESS"`.

## SES sandbox -> production access

New SES accounts start in the **sandbox**: you can only send to addresses
you've individually verified, and volume is capped. Real subscribers won't
receive anything until you request production access (AWS console -> SES ->
Account dashboard -> "Request production access", or `aws sesv2
put-account-details`). This is a written request with a use-case
description that AWS reviews, and it's your call on the justification text
— happy to draft it with you, but you should submit it yourself.

## Testing end-to-end

1. `POST` to `https://api.updates.areanraines.com/subscribe` with
   `{"email": "you@example.com"}` (or just use the form on the live site).
2. Check the confirmation email arrives, click the link.
3. Confirm the subscriber's `status` flipped to `CONFIRMED` in the
   `SubscribersTable` (name is in the `cdk deploy` outputs).
4. Manually invoke the digest function to test a send without waiting for
   Monday:

   ```bash
   AWS_PROFILE=areanraines aws lambda invoke --function-name <DigestFunction name from outputs> /tmp/out.json && cat /tmp/out.json
   ```

   It only sends if the RSS feed has posts published in the last 7 days
   that haven't been sent before — publish or backdate a test post if you
   need to force one.

## Changing the schedule

The weekly cron (`newsletter_stack.py`, `WeeklyDigestSchedule`) is currently
Monday 13:00 UTC. Edit the `events.Schedule.cron(...)` call and redeploy.
