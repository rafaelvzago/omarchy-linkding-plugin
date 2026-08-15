# 04 — Add resilience and connectivity states

**What to build:** A resilient search experience that reports service health in the bar, handles partial active/archived failures honestly, retries only transient failures, and gives users bounded, actionable feedback for network and configuration problems.

**Blocked by:** 02 — Search and merge all Linkding bookmarks.

**Status:** done

- [x] The bar polls unauthenticated `/health` at startup and approximately every 60 seconds, backs off while unavailable, and refreshes after interactive requests.
- [x] The icon visibly represents healthy, checking, and unavailable states without sending the API token to the health endpoint.
- [x] Connect and total request timeouts are bounded.
- [x] Network, timeout, server, and `429` failures retry with capped backoff and `Retry-After` support; authentication and permanent `4xx` failures do not retry automatically.
- [x] If only one bookmark stream succeeds, the picker marks results incomplete and offers retry instead of presenting partial data as all bookmarks.
- [x] Malformed JSON, unreachable hosts, authentication failures, and configuration failures produce distinct actionable states without secret leakage.
- [x] Tests cover health transitions, timeout/retry policy, partial failures, stale requests, `401/403`, `429`, `5xx`, malformed responses, and unreachable hosts.
