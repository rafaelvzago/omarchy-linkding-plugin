import importlib.util
import json
import os
import stat
import tempfile
import unittest
import urllib.parse
import urllib.error
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).parents[1] / "linkding_helper.py"
SPEC = importlib.util.spec_from_file_location("linkding_helper", MODULE_PATH)
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


class FakeResponse:
    def __init__(self, payload, status=200, headers=None):
        self.payload = payload
        self.status = status
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


class FakeOpener:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def open(self, *_args, **_kwargs):
        if self.error:
            raise self.error
        return self.response


class LinkdingHelperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config_home = Path(self.tmp.name) / "config"
        self.env = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.config_home)}, clear=False)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_missing_config_is_reported_without_secret_data(self):
        result = helper.config_status()
        self.assertEqual(result, {"ok": False, "reason": "missing"})

    def test_valid_config_requires_restrictive_directory_and_file_modes(self):
        helper.write_config("https://linkding.example", "secret-token")
        result = helper.config_status()
        self.assertEqual(result, {"ok": True})
        self.assertEqual(stat.S_IMODE(helper.config_dir().stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(helper.config_path().stat().st_mode), 0o600)

    def test_permissive_config_is_rejected_without_echoing_token(self):
        helper.write_config("https://linkding.example", "secret-token")
        helper.config_path().chmod(0o644)
        result = helper.config_status()
        self.assertEqual(result, {"ok": False, "reason": "unsafe-permissions"})
        self.assertNotIn("secret-token", json.dumps(result))

    def test_malformed_config_is_rejected(self):
        helper.config_dir().mkdir(parents=True, mode=0o700)
        helper.config_path().write_text("not json")
        helper.config_path().chmod(0o600)
        result = helper.config_status()
        self.assertEqual(result, {"ok": False, "reason": "malformed"})

    @mock.patch.object(helper.urllib.request, "build_opener")
    def test_validate_connection_uses_profile_endpoint_and_token_header_with_spy(self, build_opener):
        opener = mock.Mock()
        opener.open.return_value = FakeResponse({"username": "rafael"})
        build_opener.return_value = opener
        self.assertTrue(helper.validate_connection("https://linkding.example/", "secret-token"))
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, "https://linkding.example/api/user/profile/")
        self.assertEqual(request.get_header("Authorization"), "Token secret-token")

    @mock.patch.object(helper.urllib.request, "build_opener")
    def test_failed_validation_does_not_replace_existing_config(self, build_opener):
        helper.write_config("https://old.example", "old-token")
        build_opener.return_value = FakeOpener(error=OSError("offline"))
        with self.assertRaises(helper.ValidationError):
            helper.setup_connection("https://new.example", "new-token")
        self.assertEqual(json.loads(helper.config_path().read_text())["baseUrl"], "https://old.example")

    def test_unsupported_url_and_empty_token_are_rejected(self):
        with self.assertRaises(helper.ValidationError):
            helper.write_config("ftp://linkding.example", "token")
        with self.assertRaises(helper.ValidationError):
            helper.write_config("https://linkding.example", " ")

    def test_http_connection_is_rejected_as_requiring_https(self):
        with self.assertRaisesRegex(helper.ValidationError, "^https-required$"):
            helper.write_config("http://linkding.example", "secret-token")

    def test_stored_http_connection_fails_closed_without_exposing_secrets(self):
        helper.config_dir().mkdir(parents=True, mode=0o700)
        helper.config_path().write_text(
            json.dumps({"baseUrl": "http://linkding.example", "apiToken": "secret-token"})
        )
        helper.config_path().chmod(0o600)

        result = helper.config_status()

        self.assertEqual(result, {"ok": False, "reason": "https-required"})
        self.assertNotIn("secret-token", json.dumps(result))
        self.assertNotIn("linkding.example", json.dumps(result))

    @mock.patch.object(helper.urllib.request, "build_opener")
    def test_http_connection_never_reaches_authenticated_network_operations(self, build_opener):
        with self.assertRaisesRegex(helper.ValidationError, "^https-required$"):
            helper.validate_connection("http://linkding.example", "secret-token")

        result = helper.search_bookmarks("http://linkding.example", "secret-token")

        self.assertFalse(result["ok"])
        self.assertEqual(
            result["errors"],
            [
                {"stream": "active", "reason": "https-required"},
                {"stream": "archived", "reason": "https-required"},
            ],
        )
        build_opener.assert_not_called()

    @mock.patch.object(helper.urllib.request, "build_opener")
    def test_atomic_write_failure_preserves_existing_config(self, build_opener):
        helper.write_config("https://old.example", "old-token")
        build_opener.return_value = FakeOpener(FakeResponse({"username": "rafael"}))
        with mock.patch.object(helper.os, "replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                helper.setup_connection("https://new.example", "new-token")
        self.assertEqual(json.loads(helper.config_path().read_text())["baseUrl"], "https://old.example")

    def test_cross_origin_redirect_handler_rejects_new_origin(self):
        request = helper.urllib.request.Request("https://linkding.example/api/user/profile/")
        with self.assertRaises(helper.ValidationError):
            helper.SameOriginRedirectHandler().redirect_request(
                request, "https://evil.example/capture", 302, "redirect", {}, None
            )

    def test_redirect_handler_rejects_same_host_https_downgrade(self):
        request = helper.urllib.request.Request("https://linkding.example/api/user/profile/")
        with self.assertRaises(helper.ValidationError):
            helper.SameOriginRedirectHandler().redirect_request(
                request, "http://linkding.example/api/user/profile/", 302, "redirect", {}, None
            )

    def test_merge_bookmarks_deduplicates_sorts_and_falls_back_to_url(self):
        active = [
            {"id": 2, "url": "https://older.example", "title": "Older", "date_added": "2024-01-01T00:00:00Z"},
            {"id": 1, "url": "https://new.example", "title": "", "date_added": "2024-02-01T00:00:00Z"},
        ]
        archived = [
            {"id": 1, "url": "https://new.example", "title": "Duplicate", "date_added": "2024-02-01T00:00:00Z"},
            {"id": 3, "url": "https://archived.example", "title": "Archived", "date_added": "2024-03-01T00:00:00Z"},
        ]
        result = helper.merge_bookmarks(active, archived)
        self.assertEqual([item["id"] for item in result], [3, 1, 2])
        self.assertEqual(result[1]["title"], "https://new.example")

    @mock.patch.object(helper.urllib.request, "build_opener")
    def test_search_queries_active_and_archived_and_returns_next_offsets(self, build_opener):
        requests = []

        def open_request(request, **_kwargs):
            requests.append(request)
            parsed = urllib.parse.urlparse(request.full_url)
            if parsed.path.endswith("/archived/"):
                payload = {"count": 12, "next": "https://linkding.example/api/bookmarks/archived/?limit=10&offset=10", "results": [
                    {"id": 2, "url": "https://archived.example", "title": "Archived", "date_added": "2024-02-01T00:00:00Z"}
                ]}
            else:
                payload = {"count": 12, "next": "https://linkding.example/api/bookmarks/?limit=10&offset=10", "results": [
                    {"id": 1, "url": "https://active.example", "title": "Active", "date_added": "2024-03-01T00:00:00Z"}
                ]}
            return FakeResponse(payload)

        opener = mock.Mock()
        opener.open.side_effect = open_request
        build_opener.return_value = opener
        result = helper.search_bookmarks("https://linkding.example", "secret-token", "#work notes", limit=10)
        self.assertEqual([item["id"] for item in result["results"]], [1, 2])
        self.assertEqual(result["next"], {"activeOffset": 10, "archivedOffset": 10})
        self.assertEqual(len(requests), 2)
        for request in requests:
            self.assertEqual(request.get_header("Authorization"), "Token secret-token")
            self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlparse(request.full_url).query)["q"], ["#work notes"])

    @mock.patch.object(helper.time, "sleep")
    @mock.patch.object(helper.urllib.request, "build_opener")
    def test_transient_server_failure_retries_then_succeeds(self, build_opener, _sleep):
        attempts = {"count": 0}

        def open_request(_request, **_kwargs):
            attempts["count"] += 1
            if attempts["count"] == 1:
                return FakeResponse({}, status=503)
            return FakeResponse({"results": [], "next": None})

        opener = mock.Mock()
        opener.open.side_effect = open_request
        build_opener.return_value = opener
        result = helper._api_json("https://linkding.example", "secret-token", "/api/bookmarks/", {"limit": 20})
        self.assertEqual(result["results"], [])
        self.assertEqual(attempts["count"], 2)

    @mock.patch.object(helper.time, "sleep")
    @mock.patch.object(helper.urllib.request, "build_opener")
    def test_rate_limit_retries_and_honors_retry_after(self, build_opener, _sleep):
        attempts = {"count": 0}

        def open_request(_request, **_kwargs):
            attempts["count"] += 1
            if attempts["count"] == 1:
                return FakeResponse({}, status=429, headers={"Retry-After": "1"})
            return FakeResponse({"results": [], "next": None})

        opener = mock.Mock()
        opener.open.side_effect = open_request
        build_opener.return_value = opener
        self.assertEqual(helper._api_json("https://linkding.example", "token", "/api/bookmarks/", {})["results"], [])
        self.assertEqual(attempts["count"], 2)
        self.assertEqual(_sleep.call_args.args[0], 1.0)

    @mock.patch.object(helper.time, "sleep")
    @mock.patch.object(helper.urllib.request, "build_opener")
    def test_malformed_json_is_distinct_and_not_retried(self, build_opener, sleep):
        response = mock.Mock(status=200, headers={})
        response.__enter__ = lambda value: value
        response.__exit__ = lambda *_args: False
        response.read.return_value = b"not-json"
        opener = mock.Mock()
        opener.open.return_value = response
        build_opener.return_value = opener
        with self.assertRaisesRegex(helper.ValidationError, "invalid-response"):
            helper._api_json("https://linkding.example", "token", "/api/bookmarks/", {})
        sleep.assert_not_called()

    @mock.patch.object(helper.urllib.request, "build_opener")
    def test_authentication_failure_is_not_retried(self, build_opener):
        opener = mock.Mock()
        build_opener.return_value = opener
        for status in (401, 403):
            with self.subTest(status=status):
                opener.reset_mock()
                opener.open.return_value = FakeResponse({}, status=status)
                with self.assertRaisesRegex(helper.ValidationError, "authentication-failed"):
                    helper._api_json("https://linkding.example", "token", "/api/bookmarks/", {})
                self.assertEqual(opener.open.call_count, 1)

    @mock.patch.object(helper.time, "sleep")
    @mock.patch.object(helper.urllib.request, "build_opener")
    def test_timeout_is_retried_and_reported_distinctly(self, build_opener, sleep):
        opener = mock.Mock()
        opener.open.side_effect = urllib.error.URLError(TimeoutError("timed out"))
        build_opener.return_value = opener
        with self.assertRaisesRegex(helper.ValidationError, "timeout"):
            helper._api_json("https://linkding.example", "token", "/api/bookmarks/", {})
        self.assertEqual(opener.open.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    @mock.patch.object(helper.urllib.request, "build_opener")
    def test_health_probe_is_unauthenticated(self, build_opener):
        opener = mock.Mock()
        opener.open.return_value = FakeResponse({"status": "healthy"})
        build_opener.return_value = opener
        result = helper.health_status("https://linkding.example")
        self.assertEqual(result, {"ok": True, "state": "healthy"})
        request = opener.open.call_args.args[0]
        self.assertIsNone(request.get_header("Authorization"))

    @mock.patch.object(helper.urllib.request, "build_opener")
    def test_health_probe_transitions_to_unavailable(self, build_opener):
        opener = mock.Mock()
        build_opener.return_value = opener
        opener.open.return_value = FakeResponse({"status": "starting"}, status=503)
        self.assertEqual(helper.health_status("https://linkding.example"), {"ok": False, "state": "unavailable"})

    @mock.patch.object(helper.urllib.request, "build_opener")
    def test_search_reports_partial_stream_failure(self, build_opener):
        def open_request(request, **_kwargs):
            if "/archived/" in request.full_url:
                raise OSError("archived unavailable")
            return FakeResponse({
                "results": [{"id": 1, "url": "https://active.example", "title": "Active"}],
                "next": None,
            })

        opener = mock.Mock()
        opener.open.side_effect = open_request
        build_opener.return_value = opener
        result = helper.search_bookmarks("https://linkding.example", "secret-token")
        self.assertTrue(result["ok"])
        self.assertFalse(result["complete"])
        self.assertEqual(result["errors"][0]["stream"], "archived")

    @mock.patch.object(helper.urllib.request, "build_opener")
    def test_list_tags_filters_prefix_and_strips_hash(self, build_opener):
        opener = mock.Mock()
        opener.open.return_value = FakeResponse({
            "results": [
                {"name": "work"},
                {"name": "Workshop"},
                {"name": "home"},
                {"name": ""},
                "skip",
                {"id": 1},
            ],
            "next": None,
        })
        build_opener.return_value = opener
        result = helper.list_tags("https://linkding.example", "secret-token", query="#wo")
        self.assertEqual(result, {"ok": True, "results": [{"name": "work"}, {"name": "Workshop"}]})
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Token secret-token")
        self.assertTrue(request.full_url.startswith("https://linkding.example/api/tags/"))

    @mock.patch.object(helper.urllib.request, "build_opener")
    def test_list_tags_paginates_until_cap_or_end(self, build_opener):
        pages = [
            FakeResponse({
                "results": [{"name": f"tag-{index}"} for index in range(100)],
                "next": "https://linkding.example/api/tags/?limit=100&offset=100",
            }),
            FakeResponse({
                "results": [{"name": "last"}],
                "next": None,
            }),
        ]
        opener = mock.Mock()
        opener.open.side_effect = pages
        build_opener.return_value = opener
        result = helper.list_tags("https://linkding.example", "secret-token")
        self.assertEqual(len(result["results"]), 101)
        self.assertEqual(result["results"][-1], {"name": "last"})
        self.assertEqual(opener.open.call_count, 2)

    @mock.patch.object(helper.urllib.request, "build_opener")
    def test_list_tags_rejects_invalid_token_without_request(self, build_opener):
        with self.assertRaisesRegex(helper.ValidationError, "invalid-token"):
            helper.list_tags("https://linkding.example", "   ")
        build_opener.assert_not_called()

    @mock.patch.object(helper.urllib.request, "build_opener")
    def test_list_tags_malformed_payload_is_distinct(self, build_opener):
        opener = mock.Mock()
        opener.open.return_value = FakeResponse({"results": "nope"})
        build_opener.return_value = opener
        with self.assertRaisesRegex(helper.ValidationError, "invalid-response"):
            helper.list_tags("https://linkding.example", "token")


if __name__ == "__main__":
    unittest.main()
