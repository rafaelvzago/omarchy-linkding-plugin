# Decide the search and connectivity policy

Type: grilling
Status: resolved
Blocked by: 01, 02

## Question

Given Linkding's actual API behavior, what pagination, result cap, debounce, request-cancellation, all-bookmark inclusion, ordering, timeout, retry, error-reporting, and continuous bar-connectivity policy should the specification require?

## Comments

## Answer

The search and connectivity policy is:

- Load 20 merged initial results, requesting up to 20 from both the active and archived endpoints, merging by bookmark ID, and sorting newest-first by `date_added`.
- Debounce input by 200 ms. Cancel obsolete requests or discard responses by query generation.
- Maintain independent active and archived pagination and fetch additional pages lazily as the user reaches the end of the current results.
- Send every query unchanged to both endpoints so Linkding remains authoritative for titles, URLs, descriptions, notes, tags, quoted phrases, boolean operators, and special terms.
- If either stream fails, mark the result set incomplete and offer retry; never present partial results as “all bookmarks.”
- Retry only transient network, timeout, server, and `429` failures with bounded exponential backoff and `Retry-After` support. Never automatically retry authentication or permanent `4xx` failures.
- Use bounded connect and total request timeouts.
- Poll unauthenticated `/health` at startup and approximately every 60 seconds, back off while offline, and refresh after interactive requests. The bar exposes `healthy`, `checking`, and `unavailable` states. The token is never sent to the health endpoint; `/api/user/profile/` is reserved for setup and explicit revalidation.
