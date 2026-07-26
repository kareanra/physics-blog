from pydantic import AnyHttpUrl, BaseModel, TypeAdapter, field_validator

_url_adapter = TypeAdapter(AnyHttpUrl)


def _check_url(v: str) -> str:
    # Validate shape only -- deliberately return the original string rather
    # than the parsed/reserialized URL, since pydantic normalizes bare
    # domains with a trailing slash (e.g. "https://x.com" -> "https://x.com/"),
    # which would silently break exact-match CORS origin comparisons.
    _url_adapter.validate_python(v)
    return v


class NewsletterConfig(BaseModel):
    """Validated stack inputs, checked at `cdk synth` time -- not deployed to Lambda.

    Kept out of the Lambda runtime deliberately: pydantic-core is a compiled
    dependency, and pulling it into the handler code would force Docker-based
    bundling for what are otherwise plain, dependency-free zip assets.
    """

    root_domain: str
    mail_subdomain: str
    site_url: str
    feed_url: str
    cors_origins: list[str]

    @field_validator("mail_subdomain")
    @classmethod
    def mail_subdomain_must_be_under_root(cls, v: str, info) -> str:
        root_domain = info.data.get("root_domain")
        if root_domain and not v.endswith(f".{root_domain}"):
            raise ValueError(f"mail_subdomain {v!r} must be a subdomain of root_domain {root_domain!r}")
        return v

    @field_validator("site_url", "feed_url")
    @classmethod
    def must_be_https_url(cls, v: str) -> str:
        return _check_url(v)

    @field_validator("cors_origins")
    @classmethod
    def origins_must_be_https_urls(cls, v: list[str]) -> list[str]:
        for origin in v:
            _check_url(origin)
        return v
