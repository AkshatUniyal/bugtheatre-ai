from __future__ import annotations

from utils.security import redact_secrets


def test_no_secrets_unchanged():
    result = redact_secrets("Just a plain debug log with nothing sensitive.")
    assert result.findings == []
    assert "plain debug log" in result.text


def test_redacts_aws_key():
    text = "Key: AKIAIOSFODNN7EXAMPLE"
    result = redact_secrets(text)
    assert "aws access key" in result.findings
    assert "AKIAIOSFODNN7EXAMPLE" not in result.text


def test_redacts_private_key():
    text = "-----BEGIN RSA PRIVATE KEY-----\nABCDEF\n-----END RSA PRIVATE KEY-----"
    result = redact_secrets(text)
    assert "private key" in result.findings
    assert "RSA PRIVATE KEY" not in result.text


def test_redacts_database_url():
    text = "DATABASE_URL=postgres://user:s3cr3t@db.host/mydb"
    result = redact_secrets(text)
    assert "database url" in result.findings


def test_redacts_bearer_token():
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    result = redact_secrets(text)
    assert "bearer token" in result.findings


def test_redacts_jwt():
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36P"
    result = redact_secrets(jwt)
    assert "jwt token" in result.findings
    assert jwt not in result.text


def test_redacts_github_token():
    token = "ghp_" + "A" * 36
    result = redact_secrets(token)
    assert "github token" in result.findings
    assert token not in result.text


def test_redacts_slack_token():
    # Construct the token at runtime so GitHub push-protection doesn't flag this test file
    token = "-".join(["xoxb", "000000000000", "TESTTOKENVALUE"])
    result = redact_secrets(token)
    assert "slack token" in result.findings


def test_multiple_secrets_all_redacted():
    text = f"key=AKIAIOSFODNN7EXAMPLE url=postgres://u:p@h/d"
    result = redact_secrets(text)
    assert "aws access key" in result.findings
    assert "database url" in result.findings
    assert "AKIAIOSFODNN7EXAMPLE" not in result.text
