"""Private upstream transport configuration, image CDN URL builders, and channel alias resolution.

Never exported from the public `betscout_sdk` entrypoint.
"""

from __future__ import annotations

from typing import Any, Sequence
from urllib.parse import quote

DEFAULT_UPSTREAM_BASE_URL = "https://stats.fn.sportradar.com"
DEFAULT_UPSTREAM_IMAGE_BASE_URL = "https://img.sportradar.com"
DEFAULT_UPSTREAM_PROTOCOL = "gismo"

_CHANNEL_MAP: dict[str, str] = {
    "global": "sportradar",
    "eu-retail": "tipico",
    "neutral": "common",
    "common": "common",
    "sportradar": "sportradar",
    "tipico": "tipico",
}

_UK_HOME_NATION_SVG_MAP: dict[str, str] = {
    "en": "gb-eng",
    "s": "gb-sct",
    "n": "gb-nir",
    "w": "gb-wls",
}


def resolve_upstream_channel(channel: str | None = None) -> str:
    if not channel:
        return "sportradar"
    normalized = str(channel).strip().lower()
    return _CHANNEL_MAP.get(normalized, normalized)


def build_upstream_feed_url(
    base_url: str,
    channel: str | None,
    language: str,
    timezone: str,
    endpoint: str,
    params: str | int | Sequence[Any] | None = None,
    token: str | None = None,
) -> str:
    clean_base = base_url.rstrip("/")
    clean_endpoint = endpoint.strip("/")
    resolved_channel = resolve_upstream_channel(channel)

    param_path = ""
    if isinstance(params, (list, tuple)):
        parts = [
            str(p).strip("/")
            for p in params
            if p is not None and str(p).strip("/") != ""
        ]
        param_path = "/".join(parts)
    elif params is not None and str(params).strip("/") != "":
        param_path = str(params).strip("/")

    suffix = f"{clean_endpoint}/{param_path}" if param_path else clean_endpoint
    url = f"{clean_base}/{resolved_channel}/{language}/{timezone}/{DEFAULT_UPSTREAM_PROTOCOL}/{suffix}"
    if token:
        return f"{url}?T={quote(token)}"
    return url


def build_upstream_team_logo_url(
    team_id: int | str,
    size: str = "big",
    ncaa: bool = False,
    ncaa_size: str = "ap250x188ut",
    image_base_url: str | None = None,
) -> str:
    base = (image_base_url or DEFAULT_UPSTREAM_IMAGE_BASE_URL).rstrip("/")
    if ncaa:
        return f"{base}/ls/teams/{ncaa_size}/{team_id}.png"
    return f"{base}/ls/crest/{size}/{team_id}.png"


def build_upstream_country_flag_url(
    country_iso2: str,
    fmt: str = "svg",
    ratio: str = "4x3",
    size: str = "medium",
    image_base_url: str | None = None,
) -> str:
    base = (image_base_url or DEFAULT_UPSTREAM_IMAGE_BASE_URL).rstrip("/")
    clean_iso = str(country_iso2 or "").strip().lower()
    if fmt == "svg":
        mapped = _UK_HOME_NATION_SVG_MAP.get(clean_iso, clean_iso)
        return f"{base}/ls/crest/{ratio}/{mapped}.svg"
    return f"{base}/ls/crest/{size}/{clean_iso}.png"
