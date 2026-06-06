
from __future__ import annotations

import ipaddress
import re


def is_valid_ipv4(value: str) -> bool:
    try:
        ipaddress.IPv4Address(value)
        return True
    except ValueError:
        return False


def is_valid_ipv6(value: str) -> bool:
    try:
        ipaddress.IPv6Address(value)
        return True
    except ValueError:
        return False


_DNS_LABEL_RE = re.compile(
    r"^(?:[a-zA-Z0-9]"
    r"(?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?"
    r"\.)*"
    r"[a-zA-Z0-9]"
    r"(?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$"
)


def is_valid_dns_name(value: str) -> bool:

    if value == "@":
        return True
    stripped = value.lstrip("*.")
    if not stripped:
        return False
    if len(value) > 253:
        return False
    return bool(_DNS_LABEL_RE.match(stripped))



def is_valid_ttl(value: str) -> bool:

    try:
        ttl = int(value)
    except ValueError:
        return False
    return ttl == 1 or (60 <= ttl <= 86400)


def parse_ttl(value: str) -> int:

    return int(value)


def is_valid_priority(value: str) -> bool:

    try:
        p = int(value)
    except ValueError:
        return False
    return 0 <= p <= 65535


def is_valid_cname_target(value: str) -> bool:
    return is_valid_dns_name(value.rstrip("."))


def is_valid_txt_content(value: str) -> bool:
    return 0 < len(value) <= 2048



def is_valid_srv_port(value: str) -> bool:
    try:
        p = int(value)
    except ValueError:
        return False
    return 0 <= p <= 65535


def is_valid_srv_weight(value: str) -> bool:
    try:
        w = int(value)
    except ValueError:
        return False
    return 0 <= w <= 65535


def validate_record_content(record_type: str, content: str) -> tuple[bool, str]:
    t = record_type.upper()
    if t == "A":
        if not is_valid_ipv4(content):
            return False, "❌ Invalid IPv4 address.  Example: 1.2.3.4"
    elif t == "AAAA":
        if not is_valid_ipv6(content):
            return False, "❌ Invalid IPv6 address.  Example: 2001:db8::1"
    elif t == "CNAME":
        if not is_valid_cname_target(content):
            return False, "❌ Invalid CNAME target.  Example: target.example.com"
    elif t == "TXT":
        if not is_valid_txt_content(content):
            return False, "❌ TXT content must be 1–2048 characters."
    elif t == "MX":
        pass
    elif t == "SRV":
        pass 
    return True, ""
