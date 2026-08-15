# Research the Linkding bookmark search API contract

Type: research
Status: resolved
Blocked by:

## Question

According to official Linkding documentation and source, how must the Plugin authenticate, validate a Linkding Connection, fetch recent bookmarks, search across every bookmark including archived entries, paginate results, interpret searchable fields, handle failures and rate or performance constraints, and perform lightweight connectivity checks without exposing the API token?

## Comments

## Answer

Use `Authorization: Token <token>` and validate setup with the authenticated `GET /api/user/profile/`. Search active and archived bookmarks through their separate, independently paginated endpoints, merge them client-side, and preserve Linkding's native search semantics. Use unauthenticated `GET /health` for conservative icon reachability polling; it does not validate credentials. The stock project documents limit/offset pagination (default 100) but no rate limit, so debounce, cancel stale requests, paginate lazily, and handle proxy-supplied 429 responses safely. Never put the token in URLs, process arguments, logs, or notifications.

Full findings and inline first-party sources: [Linkding API contract for bookmark search](../research/linkding-api-contract.md).
