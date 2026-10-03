"""Structured-ish logging. Secrets are never logged."""
import logging
import os
import sys

_configured = False
_REDACT = ("key", "token", "secret", "password", "authorization")


def setup():
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    root = logging.getLogger("codeforge")
    root.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    root.handlers = [handler]
    _configured = True


def get_logger(name: str) -> logging.Logger:
    setup()
    return logging.getLogger("codeforge." + name)


def safe_args(args: dict) -> dict:
    """Strip anything that looks like a credential before logging tool arguments."""
    out = {}
    for k, v in (args or {}).items():
        if any(word in k.lower() for word in _REDACT):
            out[k] = "[redacted]"
        elif isinstance(v, str) and len(v) > 120:
            out[k] = v[:120] + "...[%d chars]" % len(v)
        else:
            out[k] = v
    return out
