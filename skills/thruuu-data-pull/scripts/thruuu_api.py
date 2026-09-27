"""Minimal read-only client for the thruuu v2 REST API (stdlib only).

Reads the API key from THRUUU_API_KEY and the base URL from THRUUU_API_BASE.
Never prints the key. GET by default; `request` also sends POST for thruuu-content-pipeline, which asks the user first.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE = "https://api.thruuu.com"

ERROR_HELP = {
    401: "401 Unauthorized: THRUUU_API_KEY is missing, wrong or revoked. Create a key in thruuu under Settings > API.",
    403: "403 Forbidden: the account plan does not include API access (Professional or Agency plan required).",
    404: "404 Not found: the id does not exist or belongs to another account. Run `pull.py list` to see valid ids.",
}


class ApiError(Exception):
    def __init__(self, status, path, body, method="GET"):
        self.status = status
        self.path = path
        self.body = body
        self.method = method
        hint = ERROR_HELP.get(status, "")
        super().__init__(f"HTTP {status} on {method} {path}. {hint} Body: {body[:300]}")

    def json(self):
        try:
            return json.loads(self.body)
        except ValueError:
            return {}


class Client:
    def __init__(self, base=None, key=None, max_retries=5):
        self.key = key or os.environ.get("THRUUU_API_KEY", "").strip()
        if not self.key:
            sys.exit(
                "THRUUU_API_KEY is not set. Export it first, for example:\n"
                "  export THRUUU_API_KEY=\"$(cat path/to/key-file)\"\n"
                "The key is in thruuu under Settings > API. Never paste it into a skill file."
            )
        self.base = (base or os.environ.get("THRUUU_API_BASE") or DEFAULT_BASE).rstrip("/")
        self.max_retries = max_retries
        self.calls = 0

    def get(self, path, params=None):
        return self.request("GET", path, params)

    def request(self, method, path, params=None, body=None, raw=False):
        """JSON by default; raw=True returns (bytes, headers) for file downloads."""
        query = ""
        if params:
            query = "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{self.base}/api/v2{path}{query}"
        headers = {"Authorization": f"Bearer {self.key}", "Accept": "*/*" if raw else "application/json", "User-Agent": "thruuu-skills/1.0"}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        for attempt in range(self.max_retries + 1):
            try:
                self.calls += 1
                with urllib.request.urlopen(req, timeout=60) as resp:
                    payload = resp.read()
                    return (payload, dict(resp.headers)) if raw else json.loads(payload.decode("utf-8"))
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "replace")
                if e.code == 429 and attempt < self.max_retries:
                    reset = e.headers.get("RateLimit-Reset") or e.headers.get("Retry-After") or "2"
                    try:
                        wait = max(1.0, float(reset))
                    except ValueError:
                        wait = 2.0
                    time.sleep(min(wait, 15))
                    continue
                raise ApiError(e.code, path + query, body, method)
            except urllib.error.URLError as e:
                if attempt < 2:
                    time.sleep(2)
                    continue
                sys.exit(f"Cannot reach {self.base}: {e.reason}. Check THRUUU_API_BASE and your network.")
        raise ApiError(429, path, "rate limit retries exhausted")

    def paginate(self, path, list_key, per_page, params=None):
        """Yield all rows of a paginated list endpoint until `total` is reached."""
        page, seen, total = 1, 0, None
        while True:
            p = dict(params or {})
            p.update({"page": page, "itemsPerPage": per_page})
            data = self.get(path, p)
            rows = data.get(list_key) or []
            total = data.get("total", 0)
            for r in rows:
                yield r
            seen += len(rows)
            if not rows or seen >= total:
                return
            page += 1
