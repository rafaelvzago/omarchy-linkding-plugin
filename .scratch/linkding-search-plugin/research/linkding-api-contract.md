# Linkding API contract for bookmark search

Research date: 2026-08-14. Sources are the official Linkding documentation and the first-party `sissbruecker/linkding` repository at commit [`b58a7bb`](https://github.com/sissbruecker/linkding/tree/b58a7bb0b8fa68fa2e1d634e0f1e9021c91da885).

## Recommended contract

### Base URL and authentication

- Treat the configured value as the Linkding installation root, including any deployment context path, normalize only its trailing slash, and append relative endpoints such as `api/user/profile/`. Do not assume Linkding is installed at the host root.
- Send the token only in the request header `Authorization: Token <token>`, as specified by the [official API authentication documentation](https://linkding.link/api/#authentication). Current first-party code also accepts `Bearer`, but `Token` is the documented, broadly compatible form; the implementation's two accepted keywords are visible in [`bookmarks/api/auth.py`](https://github.com/sissbruecker/linkding/blob/b58a7bb0b8fa68fa2e1d634e0f1e9021c91da885/bookmarks/api/auth.py#L8-L36).
- Never place the token in a URL, query string, process arguments, diagnostics, notifications, or logs. Redact the `Authorization` header in debug output. Reject or strip cross-origin redirects rather than forwarding credentials to another origin.

### Setup validation and connectivity

- Validate a configured URL and token with `GET /api/user/profile/`. It is a small authenticated resource explicitly documented as returning user preferences ([official profile endpoint](https://linkding.link/api/#user)), so a successful JSON response proves both API reachability and token validity without downloading bookmarks.
- Validate the URL before saving: require HTTP(S), a host, and a response from the expected endpoint. Use a short timeout and report TLS, DNS, connection, timeout, malformed-response, and authentication failures separately. Setup should refuse to save on any failure, matching the product decision.
- `GET /health` is an unauthenticated lightweight service/database health probe. First-party code returns JSON containing `version` and `status`, with HTTP 200 for `healthy` and HTTP 500 for `unhealthy` ([health implementation](https://github.com/sissbruecker/linkding/blob/b58a7bb0b8fa68fa2e1d634e0f1e9021c91da885/bookmarks/views/health.py#L7-L17)). It is suitable for periodic icon reachability checks but **does not validate the token**. Avoid sending the token to it.
- For a continuously updated icon, poll `/health` conservatively (for example, on startup and every 60 seconds), stop or back off while offline, and also refresh after an interactive request. Reserve `/api/user/profile/` for setup and explicit revalidation so connectivity polling does not repeatedly exercise authentication.

### Initial recent bookmarks

- Active bookmarks: `GET /api/bookmarks/?limit=<N>&offset=0`.
- Archived bookmarks: `GET /api/bookmarks/archived/?limit=<N>&offset=0`.
- The official API states the archived endpoint has the same parameters and response as the normal list endpoint ([bookmark list documentation](https://linkding.link/api/#bookmarks)). The first-party query defaults to descending `date_added`, so each first page contains the newest bookmarks for its respective set ([query ordering](https://github.com/sissbruecker/linkding/blob/b58a7bb0b8fa68fa2e1d634e0f1e9021c91da885/bookmarks/queries.py#L272-L307)).
- To show the newest `N` bookmarks across *all* Linkding bookmarks, request `N` from each endpoint in parallel, merge the results, sort by `date_added` descending, and retain the first `N`. This is sufficient because an item outside either source's first `N` cannot enter the combined first `N`.

### Searching every bookmark

- Debounced search must issue the same URL-encoded `q` to **both** `GET /api/bookmarks/` and `GET /api/bookmarks/archived/`, then merge the `results`. The route explicitly separates active and archived querysets ([API route](https://github.com/sissbruecker/linkding/blob/b58a7bb0b8fa68fa2e1d634e0f1e9021c91da885/bookmarks/api/routes.py#L58-L71)); there is no documented single “all bookmarks” endpoint.
- Search is server-side and follows the Linkding UI's search logic, per the [`q` documentation](https://linkding.link/api/#bookmarks). Ordinary terms match title, description, notes, or URL case-insensitively. In a user's `lax` tag-search mode, an ordinary term also matches a tag name exactly; explicit tag expressions match tags exactly. The current implementation also supports boolean expressions and the `unread` and `untagged` special terms ([first-party search query conversion](https://github.com/sissbruecker/linkding/blob/b58a7bb0b8fa68fa2e1d634e0f1e9021c91da885/bookmarks/queries.py#L60-L136)).
- Linkding's [official search guide](https://linkding.link/search/) documents quoted phrases, `AND`, `OR`, `NOT`, parentheses, and `#tag` syntax. An incomplete advanced expression while the user is still typing can legitimately produce zero results: current source catches a parse error and returns an empty queryset rather than a 4xx response ([query parsing behavior](https://github.com/sissbruecker/linkding/blob/b58a7bb0b8fa68fa2e1d634e0f1e9021c91da885/bookmarks/queries.py#L122-L136)). The picker should display this as an empty/intermediate search state, not a server failure.
- Do not claim that tags are always included in free-text substring search: behavior depends on the user's profile and tag matching is exact. The profile response exposes `tag_search`, so the UI can describe the server's behavior accurately ([official profile response](https://linkding.link/api/#user)).
- Display and retain at least `id`, `url`, `title`, `description`, `notes`, `tag_names`, `is_archived`, and `date_added`; these fields are shown in the [official list response](https://linkding.link/api/#bookmarks). Use `url` as the display title fallback when `title` is empty, matching Linkding's own model behavior ([first-party model](https://github.com/sissbruecker/linkding/blob/b58a7bb0b8fa68fa2e1d634e0f1e9021c91da885/bookmarks/models.py#L53-L90)).

### Pagination and merging

- Linkding uses limit/offset pagination. The documented default limit is 100 and responses contain `count`, `next`, `previous`, and `results` ([official list contract](https://linkding.link/api/#bookmarks)); first-party REST settings confirm `LimitOffsetPagination` and page size 100 ([settings](https://github.com/sissbruecker/linkding/blob/b58a7bb0b8fa68fa2e1d634e0f1e9021c91da885/bookmarks/settings/base.py#L143-L152)).
- Maintain two independent pagination states, one per active/archived endpoint. Follow each returned `next` URL until enough UI results are available or it is `null`. For safety, accept a `next` URL only if it has the configured origin and expected API path; otherwise reconstruct the next request from `limit` and `offset` without exposing the token.
- Merge pages by bookmark `id`, sort consistently (normally `date_added` descending), and expose more results incrementally. A combined total is the sum of both `count` values.
- When the query changes, cancel in-flight requests or tag them with a generation number and discard stale responses. Debounce keystrokes (roughly 150–250 ms) and do not fetch every page eagerly.

### Failure handling

- Treat 401/403 as an authentication/authorization problem and prompt the user to check the manually managed token/configuration. Do not print the token or server response headers.
- Treat 400-series query responses as client/request failures, 429 as temporary throttling (honor `Retry-After` if provided), and 500-series responses as Linkding failures. Network/TLS/DNS/timeouts are connectivity failures. Malformed JSON or missing response fields are compatibility/protocol failures.
- If one of the active/archived searches succeeds and the other fails, do not silently present the partial result as “all bookmarks”; mark it incomplete and offer retry. Setup validation requires a complete authenticated success.
- Set bounded connect and overall timeouts. Cancel obsolete searches, retry only transient failures with capped exponential backoff and jitter, and never automatically retry authentication or other permanent 4xx errors.

### Rate and performance constraints

- The official API documentation does not publish a rate limit, and the first-party REST configuration shown above defines authentication, permissions, and pagination but no DRF throttle classes. This means clients must not infer unlimited capacity: deployments are self-hosted and may add reverse-proxy limits.
- Limit interactive result pages, debounce input, cancel stale work, fetch the active and archived streams in parallel, and paginate on demand. A 429 must still be handled even though stock Linkding does not document one.
- Do not use `/api/bookmarks/check/` as a connectivity test: its documented behavior includes scraping website metadata for a supplied URL ([official check endpoint](https://linkding.link/api/#bookmarks)), making it heavier and semantically unrelated to connection validation.

## Design consequences

1. The plugin needs a two-stream search adapter; “all bookmarks” cannot be represented by one Linkding API call.
2. Setup validation and ongoing icon health have different probes: authenticated `/api/user/profile/` for the former, unauthenticated `/health` for the latter.
3. Search fields and syntax should be described as Linkding-native, not reimplemented locally. Results can be formatted locally, but server results remain authoritative.
4. The token must remain in a restrictive user-owned file and only enter the HTTP authorization header in memory.
