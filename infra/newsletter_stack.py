from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as events_targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from aws_cdk import aws_ses as ses
from constructs import Construct

CONFIRM_TOKEN_INDEX = "confirmToken-index"
UNSUBSCRIBE_TOKEN_INDEX = "unsubscribeToken-index"
DIGEST_REPORT_EMAIL = "kyle.areanraines@gmail.com"


class NewsletterStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        root_domain: str,
        mail_subdomain: str,
        site_url: str,
        feed_url: str,
        cors_origins: list[str],
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        zone = route53.HostedZone.from_lookup(self, "Zone", domain_name=root_domain)

        # --- SES domain identity, DKIM, custom MAIL FROM, DMARC -----------------
        identity = ses.EmailIdentity(
            self,
            "MailIdentity",
            identity=ses.Identity.domain(mail_subdomain),
            mail_from_domain=f"mail.{mail_subdomain}",
        )

        for i, record in enumerate(identity.dkim_records):
            route53.CnameRecord(
                self,
                f"DkimRecord{i}",
                zone=zone,
                record_name=record.name,
                domain_name=record.value,
                ttl=Duration.hours(1),
            )

        route53.MxRecord(
            self,
            "MailFromMx",
            zone=zone,
            record_name=f"mail.{mail_subdomain}",
            values=[route53.MxRecordValue(host_name=f"feedback-smtp.{self.region}.amazonses.com", priority=10)],
        )
        route53.TxtRecord(
            self,
            "MailFromSpf",
            zone=zone,
            record_name=f"mail.{mail_subdomain}",
            values=["v=spf1 include:amazonses.com ~all"],
        )
        route53.TxtRecord(
            self,
            "Dmarc",
            zone=zone,
            record_name=f"_dmarc.{mail_subdomain}",
            values=[f"v=DMARC1; p=none; rua=mailto:{DIGEST_REPORT_EMAIL}"],
        )

        # --- Storage --------------------------------------------------------------
        subscribers_table = dynamodb.Table(
            self,
            "SubscribersTable",
            partition_key=dynamodb.Attribute(name="email", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="expiresAt",
            # Subscriber data should survive a stack teardown/rebuild.
            removal_policy=RemovalPolicy.RETAIN,
        )
        subscribers_table.add_global_secondary_index(
            index_name=CONFIRM_TOKEN_INDEX,
            partition_key=dynamodb.Attribute(name="confirmToken", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL,
        )
        subscribers_table.add_global_secondary_index(
            index_name=UNSUBSCRIBE_TOKEN_INDEX,
            partition_key=dynamodb.Attribute(name="unsubscribeToken", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        digest_state_table = dynamodb.Table(
            self,
            "DigestStateTable",
            partition_key=dynamodb.Attribute(name="stateKey", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # --- Lambda layer (shared helper code) -------------------------------------
        common_layer = _lambda.LayerVersion(
            self,
            "CommonLayer",
            code=_lambda.Code.from_asset("lambda/layer"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
        )

        api_base_url = f"https://api.{mail_subdomain}"
        from_address = f"news@{mail_subdomain}"
        base_env = {
            "SITE_URL": site_url,
            "SES_FROM_ADDRESS": from_address,
            "SES_FROM_NAME": "Computational Physics Notes",
        }

        def make_function(id_: str, handler_dir: str, env: dict, timeout: Duration, memory: int = 128):
            return _lambda.Function(
                self,
                id_,
                runtime=_lambda.Runtime.PYTHON_3_12,
                handler="handler.handler",
                code=_lambda.Code.from_asset(f"lambda/{handler_dir}"),
                layers=[common_layer],
                environment={**base_env, **env},
                timeout=timeout,
                memory_size=memory,
            )

        subscribe_fn = make_function(
            "SubscribeFunction",
            "subscribe",
            {"SUBSCRIBERS_TABLE": subscribers_table.table_name, "API_BASE_URL": api_base_url},
            timeout=Duration.seconds(10),
        )
        confirm_fn = make_function(
            "ConfirmFunction",
            "confirm",
            {"SUBSCRIBERS_TABLE": subscribers_table.table_name},
            timeout=Duration.seconds(10),
        )
        unsubscribe_fn = make_function(
            "UnsubscribeFunction",
            "unsubscribe",
            {"SUBSCRIBERS_TABLE": subscribers_table.table_name},
            timeout=Duration.seconds(10),
        )
        digest_fn = make_function(
            "DigestFunction",
            "digest",
            {
                "SUBSCRIBERS_TABLE": subscribers_table.table_name,
                "DIGEST_STATE_TABLE": digest_state_table.table_name,
                "API_BASE_URL": api_base_url,
                "FEED_URL": feed_url,
            },
            timeout=Duration.minutes(5),
            memory=256,
        )

        subscribers_table.grant_read_write_data(subscribe_fn)
        subscribers_table.grant_read_write_data(confirm_fn)
        subscribers_table.grant_read_write_data(unsubscribe_fn)
        subscribers_table.grant_read_data(digest_fn)
        digest_state_table.grant_read_write_data(digest_fn)

        ses_send_statement = iam.PolicyStatement(
            actions=["ses:SendEmail", "ses:SendRawEmail"],
            resources=[f"arn:aws:ses:{self.region}:{self.account}:identity/{mail_subdomain}"],
        )
        subscribe_fn.add_to_role_policy(ses_send_statement)
        digest_fn.add_to_role_policy(ses_send_statement)

        # --- API Gateway (HTTP API) with a stable custom domain --------------------
        api_cert = acm.Certificate(
            self,
            "ApiCertificate",
            domain_name=f"api.{mail_subdomain}",
            validation=acm.CertificateValidation.from_dns(zone),
        )
        api_domain = apigwv2.DomainName(
            self,
            "ApiDomainName",
            domain_name=f"api.{mail_subdomain}",
            certificate=api_cert,
        )
        http_api = apigwv2.HttpApi(
            self,
            "HttpApi",
            default_domain_mapping=apigwv2.DomainMappingOptions(domain_name=api_domain),
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=cors_origins,
                allow_methods=[apigwv2.CorsHttpMethod.GET, apigwv2.CorsHttpMethod.POST, apigwv2.CorsHttpMethod.OPTIONS],
                allow_headers=["Content-Type"],
                max_age=Duration.hours(1),
            ),
        )
        http_api.add_routes(
            path="/subscribe",
            methods=[apigwv2.HttpMethod.POST],
            integration=integrations.HttpLambdaIntegration("SubscribeIntegration", subscribe_fn),
        )
        http_api.add_routes(
            path="/confirm",
            methods=[apigwv2.HttpMethod.GET],
            integration=integrations.HttpLambdaIntegration("ConfirmIntegration", confirm_fn),
        )
        http_api.add_routes(
            path="/unsubscribe",
            methods=[apigwv2.HttpMethod.GET, apigwv2.HttpMethod.POST],
            integration=integrations.HttpLambdaIntegration("UnsubscribeIntegration", unsubscribe_fn),
        )

        route53.ARecord(
            self,
            "ApiAliasRecord",
            zone=zone,
            record_name=f"api.{mail_subdomain}",
            target=route53.RecordTarget.from_alias(
                targets.ApiGatewayv2DomainProperties(api_domain.regional_domain_name, api_domain.regional_hosted_zone_id)
            ),
        )

        # --- Weekly digest schedule -------------------------------------------------
        digest_rule = events.Rule(
            self,
            "WeeklyDigestSchedule",
            schedule=events.Schedule.cron(minute="0", hour="13", week_day="MON"),
        )
        digest_rule.add_target(events_targets.LambdaFunction(digest_fn))

        CfnOutput(self, "ApiBaseUrl", value=api_base_url)
        CfnOutput(self, "SubscribersTableName", value=subscribers_table.table_name)
        CfnOutput(self, "SesIdentityArn", value=f"arn:aws:ses:{self.region}:{self.account}:identity/{mail_subdomain}")
