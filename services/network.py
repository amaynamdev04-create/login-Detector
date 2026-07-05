"""Request IP and geolocation helpers."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import current_app

LOGGER = logging.getLogger(__name__)

UNKNOWN = "Unknown"


@dataclass(frozen=True)
class ClientNetwork:
    """Structured client network details."""

    public_ip: str
    private_ip: str | None = None
    ip_version: str | None = None


@dataclass(frozen=True)
class GeoDetails:
    """Structured geolocation metadata."""

    country: str = UNKNOWN
    country_code: str = UNKNOWN
    region: str = UNKNOWN
    city: str = UNKNOWN
    timezone: str = UNKNOWN
    isp: str = UNKNOWN
    latitude: float | None = None
    longitude: float | None = None

    def to_record(self) -> dict[str, Any]:
        return {
            "country": self.country,
            "country_code": self.country_code,
            "region": self.region,
            "city": self.city,
            "timezone": self.timezone,
            "isp": self.isp,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


def normalize_ip(raw: str | None) -> str:
    """Normalize IP addresses for consistent storage and matching."""
    if not raw:
        return "127.0.0.1"
    candidate = raw.strip()
    if ":" in candidate and candidate.count(":") == 1 and candidate.split(":")[-1].isdigit():
        candidate = candidate.rsplit(":", 1)[0]
    try:
        address = ipaddress.ip_address(candidate)
    except ValueError:
        return candidate

    if address.version == 6 and getattr(address, "ipv4_mapped", None):
        return str(address.ipv4_mapped)
    if address.version == 6 and address.is_loopback:
        return "::1"
    return str(address)


def parse_ip_version(ip_address: str) -> str | None:
    try:
        return f"IPv{ipaddress.ip_address(ip_address).version}"
    except ValueError:
        return None


def is_public_ip(ip_address: str) -> bool:
    try:
        address = ipaddress.ip_address(ip_address)
    except ValueError:
        return False
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def resolve_client_network(request, private_ip: str | None = None) -> ClientNetwork:
    """Resolve the best available client IP metadata."""
    header_candidates = (
        request.headers.get("X-Vercel-Forwarded-For", ""),
        request.headers.get("X-Forwarded-For", ""),
        request.headers.get("X-Real-IP", ""),
    )
    for header_value in header_candidates:
        if header_value:
            public_ip = normalize_ip(header_value.split(",")[0].strip())
            break
    else:
        public_ip = normalize_ip(request.remote_addr or "127.0.0.1")

    normalized_private_ip = normalize_ip(private_ip) if private_ip else None
    return ClientNetwork(
        public_ip=public_ip,
        private_ip=normalized_private_ip,
        ip_version=parse_ip_version(public_ip),
    )


def resolve_geo_details(ip_address: str, request=None) -> GeoDetails:
    """Resolve geolocation using trusted platform headers first, then provider lookup."""
    header_geo = _vercel_geo_from_headers(request) if request is not None else None
    if header_geo and _is_geo_useful(header_geo):
        provider_geo = _lookup_geoip(ip_address)
        return _merge_geo_details(provider_geo, header_geo)
    provider_geo = _lookup_geoip(ip_address)
    return provider_geo


def _vercel_geo_from_headers(request) -> GeoDetails:
    country_code = _clean_header(request.headers.get("X-Vercel-IP-Country"))
    region = _clean_header(request.headers.get("X-Vercel-IP-Country-Region"))
    city = _clean_header(request.headers.get("X-Vercel-IP-City"))
    timezone = _clean_header(request.headers.get("X-Vercel-IP-Timezone"))
    latitude = _parse_float(request.headers.get("X-Vercel-IP-Latitude"))
    longitude = _parse_float(request.headers.get("X-Vercel-IP-Longitude"))
    return GeoDetails(
        country_code=country_code or UNKNOWN,
        region=region or UNKNOWN,
        city=city or UNKNOWN,
        timezone=timezone or UNKNOWN,
        latitude=latitude,
        longitude=longitude,
    )


def _lookup_geoip(ip_address: str) -> GeoDetails:
    if not is_public_ip(ip_address):
        return GeoDetails()

    url = current_app.config["GEOIP_PROVIDER_URL"].format(ip=ip_address)
    params = {}
    token = current_app.config.get("GEOIP_API_TOKEN", "").strip()
    if token:
        params["key"] = token
    if params:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{urlencode(params)}"

    request = Request(url, headers={"Accept": "application/json", "User-Agent": "login-attempt-monitor/2.0"})
    try:
        with urlopen(request, timeout=current_app.config["GEOIP_TIMEOUT_SECONDS"]) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        LOGGER.warning("GeoIP lookup failed for %s: %s", ip_address, exc)
        return GeoDetails()

    if payload.get("error"):
        reason = payload.get("reason") or payload.get("error")
        LOGGER.warning("GeoIP lookup rejected for %s: %s", ip_address, reason)
        return GeoDetails()

    return GeoDetails(
        country=_clean_header(payload.get("country_name")) or UNKNOWN,
        country_code=_clean_header(payload.get("country_code")) or UNKNOWN,
        region=_clean_header(payload.get("region")) or UNKNOWN,
        city=_clean_header(payload.get("city")) or UNKNOWN,
        timezone=_clean_header(payload.get("timezone")) or UNKNOWN,
        isp=_clean_header(payload.get("org")) or UNKNOWN,
        latitude=_parse_float(payload.get("latitude")),
        longitude=_parse_float(payload.get("longitude")),
    )


def _merge_geo_details(primary: GeoDetails, fallback: GeoDetails) -> GeoDetails:
    return GeoDetails(
        country=primary.country if primary.country != UNKNOWN else fallback.country,
        country_code=primary.country_code if primary.country_code != UNKNOWN else fallback.country_code,
        region=primary.region if primary.region != UNKNOWN else fallback.region,
        city=primary.city if primary.city != UNKNOWN else fallback.city,
        timezone=primary.timezone if primary.timezone != UNKNOWN else fallback.timezone,
        isp=primary.isp if primary.isp != UNKNOWN else fallback.isp,
        latitude=primary.latitude if primary.latitude is not None else fallback.latitude,
        longitude=primary.longitude if primary.longitude is not None else fallback.longitude,
    )


def _is_geo_useful(details: GeoDetails) -> bool:
    return any(
        value not in {None, UNKNOWN, ""}
        for value in (
            details.country,
            details.country_code,
            details.region,
            details.city,
            details.timezone,
            details.latitude,
            details.longitude,
        )
    )


def _clean_header(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
