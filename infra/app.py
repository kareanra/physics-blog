#!/usr/bin/env python3
import aws_cdk as cdk

from config import NewsletterConfig
from newsletter_stack import NewsletterStack

# Pin explicitly so `cdk deploy` can never land in the wrong account.
NEWSLETTER_ACCOUNT = "912946686130"
NEWSLETTER_REGION = "us-east-1"

config = NewsletterConfig(
    root_domain="areanraines.com",
    mail_subdomain="updates.areanraines.com",
    site_url="https://areanraines.com",
    feed_url="https://areanraines.com/index.xml",
    cors_origins=["https://areanraines.com", "https://kareanra.github.io"],
)

app = cdk.App()

NewsletterStack(
    app,
    "PhysicsBlogNewsletterStack",
    env=cdk.Environment(account=NEWSLETTER_ACCOUNT, region=NEWSLETTER_REGION),
    root_domain=config.root_domain,
    mail_subdomain=config.mail_subdomain,
    site_url=config.site_url,
    feed_url=config.feed_url,
    cors_origins=config.cors_origins,
)

app.synth()
