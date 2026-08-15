#!/usr/bin/env python3
"""Small, secret-safe command boundary for the Linkding Search Plugin."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import getpass
import json
import os
import random
import stat
import sys
import tempfile
import time
from email.utils import parsedate_to_datetime
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


APP_DIR = "linkding-search-plugin"
CONFIG_NAME = "config.json"


class ValidationError(Exception):
    """A safe, user-facing validation failure without secret material."""


class SameOriginRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Permit redirects only when they stay on the configured origin."""

    def redirect_request(self, request, new_url, code, msg, headers, fp):
        old = urllib.parse.urlparse(request.full_url)
        new = urllib.parse.urlparse(new_url)
        if (old.scheme, old.netloc) != (new.scheme, new.netloc):
            raise ValidationError("cross-origin-redirect")
        return super().redirect_request(request, new_url, code, msg, headers, fp)


def config_dir() -> Path:
    root = os.environ.get("XDG_CONFIG_HOME")
    return Path(root).expanduser() / APP_DIR if root else Path.home() / ".config" / APP_DIR


def config_path() -> Path:
    return config_dir() / CONFIG_NAME


def _safe_mode(path: Path, expected: int) -> bool:
    try:
        return stat.S_IMODE(path.stat().st_mode) == expected
    except FileNotFoundError:
        return False


def _validate_url(base_url: str) -> str:
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValidationError("invalid-url")
    value = base_url.strip().rstrip("/")
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValidationError("invalid-url")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValidationError("invalid-url")
    return value


def _read_config() -> dict[str, str]:
    path = config_path()
    if config_dir().is_symlink() or path.is_symlink():
        raise ValidationError("unsafe-path")
    if not path.exists():
        raise ValidationError("missing")
    if not _safe_mode(config_dir(), 0o700) or not _safe_mode(path, 0o600):
        raise ValidationError("unsafe-permissions")
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValidationError("malformed") from None
    if not isinstance(data, dict) or not isinstance(data.get("baseUrl"), str) or not isinstance(data.get("apiToken"), str):
        raise ValidationError("malformed")
    if not data["apiToken"].strip():
        raise ValidationError("malformed")
    return {"baseUrl": _validate_url(data["baseUrl"]), "apiToken": data["apiToken"]}


def config_status() -> dict[str, bool | str]:
    try:
        _read_config()
    except ValidationError as error:
        return {"ok": False, "reason": str(error)}
    return {"ok": True}


def validate_connection(base_url: str, api_token: str, timeout: float = 10.0) -> bool:
    url = _validate_url(base_url) + "/api/user/profile/"
    if not isinstance(api_token, str) or not api_token.strip():
        raise ValidationError("invalid-token")
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Token {api_token}"},
        method="GET",
    )
    try:
        opener = urllib.request.build_opener(SameOriginRedirectHandler)
        with opener.open(request, timeout=timeout) as response:
            if response.status < 200 or response.status >= 300:
                raise ValidationError("authentication-failed")
            payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValidationError("invalid-response")
    except ValidationError:
        raise
    except urllib.error.HTTPError as error:
        if error.code in {401, 403}:
            raise ValidationError("authentication-failed") from None
        raise ValidationError("validation-failed") from None
    except json.JSONDecodeError:
        raise ValidationError("invalid-response") from None
    except (OSError, ValueError, UnicodeError):
        raise ValidationError("validation-failed") from None
    return True


def write_config(base_url: str, api_token: str) -> None:
    normalized_url = _validate_url(base_url)
    if not isinstance(api_token, str) or not api_token.strip():
        raise ValidationError("invalid-token")
    directory = config_dir()
    if directory.is_symlink() or config_path().is_symlink():
        raise ValidationError("unsafe-path")
    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    payload = json.dumps({"baseUrl": normalized_url, "apiToken": api_token}, separators=(",", ":")) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{CONFIG_NAME}.", dir=directory)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, config_path())
    except Exception:
        try:
            temporary.unlink(missing_ok=True)
        finally:
            raise


def setup_connection(base_url: str, api_token: str) -> None:
    validate_connection(base_url, api_token)
    write_config(base_url, api_token)


def _api_json(base_url: str, api_token: str, endpoint: str, query: dict[str, object]) -> dict[str, Any]:
    params = urllib.parse.urlencode(query, doseq=True)
    url = _validate_url(base_url) + endpoint + (f"?{params}" if params else "")
    request = urllib.request.Request(url, headers={"Authorization": f"Token {api_token}"}, method="GET")
    opener = urllib.request.build_opener(SameOriginRedirectHandler)
    payload = None
    deadline = time.monotonic() + 10.0

    def retry_delay(response_headers=None, attempt=0):
        retry_after = response_headers.get("Retry-After") if response_headers else None
        if isinstance(retry_after, str) and retry_after:
            if retry_after.isdigit():
                return min(float(retry_after), 8.0)
            try:
                return max(0.0, min((parsedate_to_datetime(retry_after).timestamp() - time.time()), 8.0))
            except (TypeError, ValueError, OverflowError):
                pass
        return min(8.0, (2**attempt) + random.uniform(0, 0.25))

    for attempt in range(3):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValidationError("timeout")
        try:
            with opener.open(request, timeout=min(10.0, remaining)) as response:
                if response.status in {401, 403}:
                    raise ValidationError("authentication-failed")
                if response.status == 429 or 500 <= response.status < 600:
                    if attempt < 2:
                        delay = retry_delay(response.headers, attempt)
                        time.sleep(min(delay, max(0.0, deadline - time.monotonic())))
                        continue
                    raise ValidationError("rate-limited" if response.status == 429 else "server-failed")
                if response.status < 200 or response.status >= 300:
                    raise ValidationError("request-failed")
                payload = json.loads(response.read().decode("utf-8"))
            break
        except ValidationError:
            raise
        except urllib.error.HTTPError as error:
            if error.code in {401, 403}:
                raise ValidationError("authentication-failed") from None
            if (error.code == 429 or 500 <= error.code < 600) and attempt < 2:
                delay = retry_delay(error.headers, attempt)
                time.sleep(min(delay, max(0.0, deadline - time.monotonic())))
                continue
            raise ValidationError("rate-limited" if error.code == 429 else "server-failed" if error.code >= 500 else "request-failed") from None
        except json.JSONDecodeError:
            raise ValidationError("invalid-response") from None
        except UnicodeError:
            raise ValidationError("invalid-response") from None
        except urllib.error.URLError as error:
            reason = str(error.reason).lower()
            failure = "timeout" if "timed out" in reason or "timeout" in reason else "unreachable"
            if attempt < 2:
                time.sleep(min(retry_delay(attempt=attempt), max(0.0, deadline - time.monotonic())))
                continue
            raise ValidationError(failure) from None
        except TimeoutError:
            if attempt < 2:
                time.sleep(min(retry_delay(attempt=attempt), max(0.0, deadline - time.monotonic())))
                continue
            raise ValidationError("timeout") from None
        except OSError:
            if attempt < 2:
                time.sleep(min(retry_delay(attempt=attempt), max(0.0, deadline - time.monotonic())))
                continue
            raise ValidationError("unreachable") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise ValidationError("invalid-response")
    return payload


def health_status(base_url: str, timeout: float = 5.0) -> dict[str, object]:
    url = _validate_url(base_url) + "/health"
    request = urllib.request.Request(url, method="GET")
    try:
        opener = urllib.request.build_opener(SameOriginRedirectHandler)
        with opener.open(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
            healthy = response.status == 200 and isinstance(payload, dict) and payload.get("status") == "healthy"
            return {"ok": healthy, "state": "healthy" if healthy else "unavailable"}
    except (OSError, ValueError, UnicodeError, ValidationError):
        return {"ok": False, "state": "unavailable"}


def _bookmark_date(value: object) -> datetime.datetime:
    if not isinstance(value, str) or not value:
        return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)


def _normalize_bookmark(item: object) -> dict[str, object]:
    if not isinstance(item, dict):
        raise ValidationError("invalid-response")
    url = item.get("url") if isinstance(item.get("url"), str) else ""
    title = item.get("title") if isinstance(item.get("title"), str) else ""
    tags = item.get("tag_names")
    if not isinstance(tags, list):
        tags = []
    return {
        "id": item.get("id"),
        "url": url,
        "title": title or url,
        "domain": urllib.parse.urlparse(url).netloc,
        "description": item.get("description") if isinstance(item.get("description"), str) else "",
        "notes": item.get("notes") if isinstance(item.get("notes"), str) else "",
        "tag_names": [str(tag) for tag in tags],
        "is_archived": bool(item.get("is_archived", False)),
        "date_added": item.get("date_added") if isinstance(item.get("date_added"), str) else "",
    }


def merge_bookmarks(active: list[object], archived: list[object]) -> list[dict[str, object]]:
    merged: dict[object, dict[str, object]] = {}
    for raw in [*active, *archived]:
        bookmark = _normalize_bookmark(raw)
        key = bookmark["id"] if bookmark["id"] is not None else bookmark["url"]
        if key not in merged:
            merged[key] = bookmark
    return sorted(merged.values(), key=lambda item: _bookmark_date(item["date_added"]), reverse=True)


def _continuation_offset(payload: dict[str, Any], base_url: str, endpoint: str) -> int | None:
    next_url = payload.get("next")
    if not next_url:
        return None
    parsed = urllib.parse.urlparse(str(next_url))
    base = urllib.parse.urlparse(_validate_url(base_url))
    if (parsed.scheme, parsed.netloc) != (base.scheme, base.netloc) or not parsed.path.endswith(endpoint):
        return None
    values = urllib.parse.parse_qs(parsed.query).get("offset", [])
    try:
        return int(values[0]) if values else None
    except (TypeError, ValueError):
        return None


def search_bookmarks(
    base_url: str,
    api_token: str,
    query: str = "",
    limit: int = 20,
    active_offset: int = 0,
    archived_offset: int = 0,
) -> dict[str, object]:
    if not isinstance(api_token, str) or not api_token.strip():
        raise ValidationError("invalid-token")
    total_limit = max(1, int(limit))
    page_limit = total_limit
    common = {"limit": page_limit, "q": query}
    active_payload = {"results": [], "next": None}
    archived_payload = {"results": [], "next": None}
    requests = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        if active_offset >= 0:
            requests["active"] = executor.submit(
                _api_json, base_url, api_token, "/api/bookmarks/", {**common, "offset": active_offset}
            )
        if archived_offset >= 0:
            requests["archived"] = executor.submit(
                _api_json, base_url, api_token, "/api/bookmarks/archived/", {**common, "offset": archived_offset}
            )
        errors = []
        for stream, payload in (("active", active_payload), ("archived", archived_payload)):
            if stream not in requests:
                continue
            try:
                if stream == "active":
                    active_payload = requests[stream].result()
                else:
                    archived_payload = requests[stream].result()
            except ValidationError as error:
                errors.append({"stream": stream, "reason": str(error)})
    active = active_payload["results"]
    archived = archived_payload["results"]
    result = {
        "ok": not errors or len(errors) < len(requests),
        "complete": not errors,
        "results": merge_bookmarks(active, archived)[:total_limit],
        "next": {
            "activeOffset": _continuation_offset(active_payload, base_url, "/api/bookmarks/"),
            "archivedOffset": _continuation_offset(archived_payload, base_url, "/api/bookmarks/archived/"),
        },
    }
    if errors:
        result["errors"] = errors
    return result


def _setup_interactive() -> int:
    try:
        base_url = input("Linkding URL: ")
        api_token = getpass.getpass("Linkding API token: ")
        setup_connection(base_url, api_token)
    except (EOFError, KeyboardInterrupt):
        print("Setup cancelled.", file=sys.stderr)
        return 130
    except ValidationError as error:
        print(f"Setup failed: {error}", file=sys.stderr)
        return 1
    print(f"Linkding Connection saved to {config_path()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Linkding Search Plugin API Helper")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("setup", help="prompt for and validate a Linkding Connection")
    subparsers.add_parser("status", help="report safe configuration status")
    subparsers.add_parser("validate", help="validate the stored Linkding Connection")
    recent_parser = subparsers.add_parser("recent", help="fetch the newest merged bookmarks")
    recent_parser.add_argument("--limit", type=int, default=20)
    recent_parser.add_argument("--query", default="")
    recent_parser.add_argument("--active-offset", type=int, default=0)
    recent_parser.add_argument("--archived-offset", type=int, default=0)
    search_parser = subparsers.add_parser("search", help="search active and archived bookmarks")
    search_parser.add_argument("--query", default="")
    search_parser.add_argument("--limit", type=int, default=20)
    search_parser.add_argument("--active-offset", type=int, default=0)
    search_parser.add_argument("--archived-offset", type=int, default=0)
    subparsers.add_parser("health", help="check Linkding reachability without sending the token")
    args = parser.parse_args(argv)
    if args.command == "setup":
        return _setup_interactive()
    if args.command == "status":
        print(json.dumps(config_status(), separators=(",", ":")))
        return 0
    if args.command in {"recent", "search"}:
        try:
            config = _read_config()
            result = search_bookmarks(
                config["baseUrl"],
                config["apiToken"],
                query=getattr(args, "query", ""),
                limit=args.limit,
                active_offset=getattr(args, "active_offset", 0),
                archived_offset=getattr(args, "archived_offset", 0),
            )
        except ValidationError as error:
            print(json.dumps({"ok": False, "reason": str(error)}, separators=(",", ":")))
            return 1
        print(json.dumps(result, separators=(",", ":")))
        return 0
    if args.command == "health":
        try:
            config = _read_config()
            result = health_status(config["baseUrl"])
        except ValidationError as error:
            result = {"ok": False, "state": "unavailable", "reason": str(error)}
        print(json.dumps(result, separators=(",", ":")))
        return 0 if result["ok"] else 1
    try:
        config = _read_config()
        validate_connection(config["baseUrl"], config["apiToken"])
    except ValidationError as error:
        print(json.dumps({"ok": False, "reason": str(error)}, separators=(",", ":")))
        return 1
    print('{"ok":true}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
