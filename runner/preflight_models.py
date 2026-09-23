"""Send a 1-token request to each candidate model ID with the key from .env and report which ones answer.

    .venv/bin/python -m runner.preflight_models
The key is read from .env inside this process only; it is never exported to the shell.
"""

import json
import ssl
import sys
import urllib.error
import urllib.request

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()

from agent.harness import load_prod_key

MODELS = ["claude-fable-5-1", "claude-fable-5", "claude-opus-5", "claude-haiku-4-5-20251001"]


def ping(model: str, key: str) -> tuple[bool, str]:
    body = json.dumps({"model": model, "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]}).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body, method="POST",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as r:
            d = json.loads(r.read())
            return True, f"ok (served as {d.get('model')})"
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read()).get("error", {}).get("message", "")
        except Exception:
            msg = ""
        return False, f"HTTP {e.code} {msg[:120]}"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def main() -> int:
    key = load_prod_key()
    ok = []
    for m in MODELS:
        good, msg = ping(m, key)
        print(f"{'CALLABLE ' if good else 'NOT      '} {m:<30} {msg}")
        if good:
            ok.append(m)
    print("callable:", " ".join(ok) or "none")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
