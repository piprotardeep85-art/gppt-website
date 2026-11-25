from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd"}


def analyze_url(url: str) -> dict:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only HTTP and HTTPS URLs are allowed.")
    if not parsed.hostname:
        raise ValueError("A valid hostname is required.")

    hostname = parsed.hostname.rstrip(".").lower()
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError("The URL hostname could not be resolved.") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError("Private, local or reserved network addresses are not allowed.")

    evidence = []
    risk = "Low Risk"
    if parsed.scheme != "https":
        evidence.append("The URL does not use HTTPS.")
        risk = "Suspicious"
    if hostname in SHORTENERS:
        evidence.append("The domain is a URL shortener.")
        risk = "Suspicious"
    if "-" in hostname or len(hostname.split(".")) > 4:
        evidence.append("The domain contains unusual structural patterns.")
        if risk == "Low Risk":
            risk = "Suspicious"

    return {
        "url": parsed.geturl(),
        "hostname": hostname,
        "https": parsed.scheme == "https",
        "risk_label": risk,
        "evidence": evidence,
        "redirects_checked": False,
        "verification_status": "Not Verified",
        "limitations": "DNS and URL structure checks do not prove company legitimacy.",
    }
