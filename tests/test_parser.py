"""Tests for the log parser."""

from monitor.parser import parse_log_line


def test_parse_valid_log_line():
    line = "2026-06-30 12:31:05 ERROR Login Failed user=admin ip=192.168.1.20"
    parsed = parse_log_line(line)
    assert parsed is not None
    assert parsed["username"] == "admin"
    assert parsed["status"] == "failed"


def test_parse_valid_log_line_with_microseconds():
    line = "2026-06-30 12:31:05.123456 ERROR Login Failed user=admin ip=192.168.1.20 source=built-in-portal"
    parsed = parse_log_line(line)
    assert parsed is not None
    assert parsed["source"] == "built-in-portal"
    assert parsed["timestamp"].microsecond == 123456


def test_parse_log_line_with_metadata():
    line = (
        "2026-06-30 12:31:05 INFO Login Success user=amay.namdev "
        "ip=203.0.113.10 source=portal meta={\"public_ip\":\"203.0.113.10\",\"private_ip\":\"192.168.1.20\",\"ip_version\":\"IPv4\"}"
    )
    parsed = parse_log_line(line)
    assert parsed is not None
    assert parsed["public_ip"] == "203.0.113.10"
    assert parsed["private_ip"] == "192.168.1.20"
    assert parsed["ip_version"] == "IPv4"


def test_parse_invalid_log_line():
    assert parse_log_line("invalid line") is None
