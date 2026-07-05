"""Tests for client IP normalization helpers."""

from flask import Flask, request

from services.network import normalize_ip, parse_ip_version, resolve_client_network


def test_normalize_ip_handles_ipv4_mapped_and_ports():
    assert normalize_ip("::ffff:127.0.0.1") == "127.0.0.1"
    assert normalize_ip("127.0.0.1:5000") == "127.0.0.1"


def test_parse_ip_version_supports_ipv4_and_ipv6():
    assert parse_ip_version("203.0.113.10") == "IPv4"
    assert parse_ip_version("2001:db8::1") == "IPv6"


def test_resolve_client_network_prefers_forwarded_for_header():
    app = Flask(__name__)
    with app.test_request_context(
        "/",
        headers={
            "X-Forwarded-For": "198.51.100.10, 10.0.0.10",
            "X-Client-Private-IP": "192.168.1.10",
        },
        environ_base={"REMOTE_ADDR": "10.0.0.10"},
    ):
        network = resolve_client_network(request, private_ip="192.168.1.10")
        assert network.public_ip == "198.51.100.10"
        assert network.private_ip == "192.168.1.10"
        assert network.ip_version == "IPv4"
