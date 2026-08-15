# Linkding Search Plugin — Implementation Specification

Status: ready-for-agent

## Problem Statement

Omarchy users cannot quickly find a saved Linkding bookmark from the desktop bar. They must leave their current context, open another interface, search manually, and then copy or open the saved URL. The user wants a reusable Omarchy Plugin that makes Linkding bookmarks available from a clickable bar icon while keeping the API token user-owned and protected.

## Solution

Build a Quattro schema-1 `bar-widget` Plugin with a compact command-palette Bookmark Picker. Clicking the bar icon opens a focused search field and immediately loads the newest bookmarks from both Linkding active and archived collections. Typing sends debounced, Linkding-native searches to both collections; results are merged, deduplicated, sorted newest-first, and paginated lazily.

The selected Bookmark Action is explicit: `Enter` opens the saved URL through Omarchy's default-browser launcher, while `Ctrl+C` or the visible copy action copies the URL and closes the picker. A narrow API Helper owns configuration, validation, health checks, and Linkding requests so QML does not handle credential policy directly. A user-run setup helper validates the Linkding Connection and atomically stores it in a protected XDG configuration file.

## User Stories

1. As an Omarchy user, I want a persistent Linkding icon in the bar, so that bookmark search is always one click away.
2. As an Omarchy user, I want the icon to open a native keyboard panel, so that the Plugin feels integrated with the shell.
3. As a user searching bookmarks, I want the search field focused on open, so that I can type immediately.
4. As a user opening the Bookmark Picker, I want recent bookmarks to load immediately, so that the empty state does not feel stalled.
5. As a user, I want active and archived bookmarks included, so that I can find every saved bookmark.
6. As a user, I want result rows to show title, domain, description, and tags, so that I can identify the right bookmark quickly.
7. As a user, I want titleless bookmarks to remain identifiable by their URL, so that no result is unusable.
8. As a user, I want typing to search Linkding after a short debounce, so that results update quickly without sending a request for every keystroke.
9. As a user, I want Linkding's native search syntax preserved, so that quoted phrases, boolean operators, tags, and special terms behave as they do elsewhere in Linkding.
10. As a user, I want results from active and archived collections merged and deduplicated, so that the picker presents one coherent list.
11. As a user, I want newest bookmarks first, so that the most relevant recent saves appear at the top.
12. As a user with many bookmarks, I want more results loaded only as I reach the end, so that opening and searching remain responsive.
13. As a user, I want stale responses discarded when I change the query, so that an older search cannot replace newer results.
14. As a user, I want arrow keys to move through results, so that I can operate the picker without a mouse.
15. As a user, I want `Enter` to open the selected URL in my configured default browser, so that I do not need to copy and paste it manually.
16. As a user, I want a visible copy action and `Ctrl+C`, so that I can place a bookmark URL in another application.
17. As a user, I want copying to close the picker and confirm success briefly, so that I know the action completed without extra cleanup.
18. As a user, I want `Escape` to close the picker, so that I can cancel without changing anything.
19. As a user, I want loading, empty, unavailable, and configuration-error states explained in the picker, so that I know what happened and what action is available.
20. As a user, I want partial active/archived failures marked incomplete, so that I am not misled into believing I saw every bookmark.
21. As a user, I want transient failures retried safely, so that temporary network or proxy problems recover without manual repetition.
22. As a user, I want authentication failures to remain actionable without exposing my token, so that I can fix configuration safely.
23. As a user, I want the bar icon to show healthy, checking, and unavailable connectivity states, so that I can understand service reachability before searching.
24. As a user, I want health polling to avoid sending my token, so that routine status checks minimize credential exposure.
25. As a first-time user, I want a setup helper to prompt for the Linkding URL and token, so that configuration does not require hand-authoring a file.
26. As a first-time user, I want setup to validate the connection before saving, so that I do not install a broken configuration.
27. As a user maintaining configuration, I want to edit the Linkding Connection manually after setup, so that advanced users retain control.
28. As a user, I want unsafe file permissions rejected, so that another local user cannot casually read my token.
29. As a user, I want failed configuration writes to preserve the previous valid file, so that a bad update does not break an existing setup.
30. As a user evaluating a third-party Plugin, I want prominent unsandboxed-execution disclosure, so that I understand the permissions I am granting.
31. As an Omarchy maintainer, I want a stable API Helper boundary, so that UI behavior can be tested without coupling tests to HTTP implementation details.
32. As a Plugin maintainer, I want dependencies and lifecycle commands documented, so that users can install, validate, update, move, and remove the Plugin predictably.
33. As a Plugin maintainer, I want the package constrained to Quattro and schema 1, so that compatibility claims remain accurate.
34. As a Plugin maintainer, I want automated and manual acceptance checks, so that releases are judged by observable behavior rather than implementation assumptions.

## Implementation Decisions

- Package the Plugin as `io.github.rafaelvzago.linkding`, licensed under MIT, with a schema-1 `bar-widget` entry point and one allowed instance in the right bar section by default.
- Use Omarchy's native `BarWidget`, `WidgetButton`, `Panel`, `KeyboardPanel`, and `PanelKeyCatcher` primitives. Do not launch a second shell or introduce Walker/Rofi for the picker.
- Keep QML responsible for bar/picker presentation, focus, selection, loading state, action dispatch, and status display.
- Introduce one narrow API Helper boundary with purpose-built operations equivalent to `validate`, `recent`, `search`, and `health`. The helper reads the Linkding Connection, enforces permissions, performs bounded requests, and returns structured success/error data without exposing the token.
- Store one Linkding Connection outside Omarchy shell settings in an XDG user configuration directory. It contains the Linkding installation base URL and API token. Normalize only the trailing slash and preserve deployment context paths.
- The setup helper prompts interactively with token input hidden, requires HTTP(S) and a host, validates with authenticated `GET /api/user/profile/`, creates a `0700` directory, and atomically writes a `0600` configuration file. Manual edits remain supported. Invalid or unsafe configuration is rejected at runtime and reported with the setup command, never with raw secrets or command output.
- Authenticate with `Authorization: Token <token>`. Never place the token in URLs, query strings, process arguments where avoidable, logs, notifications, clipboard contents, or user-visible errors. Do not forward credentials across untrusted redirects.
- Load the newest 20 total results by requesting up to 20 from both active and archived bookmark endpoints, merging by bookmark ID, and sorting by `date_added` descending.
- Search by sending the unchanged, URL-encoded query to both active and archived endpoints after a 200 ms debounce. Preserve Linkding-native query semantics instead of reimplementing matching locally.
- Keep independent pagination state for active and archived streams. Follow same-origin, expected-path continuation links and load more lazily at the end of the result list.
- Cancel obsolete requests or tag them with a query generation and discard stale responses. Fetch active and archived streams in parallel.
- If one stream fails, show an incomplete-result state with retry; never silently label partial data as all bookmarks.
- Use bounded connection and total request timeouts. Retry only transient network, timeout, server, and `429` failures with capped exponential backoff and `Retry-After` support. Do not automatically retry authentication or other permanent `4xx` failures.
- Poll unauthenticated `GET /health` at startup and approximately every 60 seconds, back off while unavailable, and refresh after interactive requests. Display healthy, checking, and unavailable icon states. Reserve `/api/user/profile/` for setup and explicit revalidation.
- Use the compact command-palette interaction selected in the prototype: a single-column surface with focused search, rich result rows, visible copy actions, keyboard navigation, and in-place loading/empty/error states. The prototype's layout is a primary interaction reference, not production code.
- Open URLs with `omarchy-launch-browser` so the configured system default browser is respected. Copy through `wl-copy`, preferably by sending the URL on stdin. Close the picker after a copy process starts successfully.
- Document runtime dependencies—Omarchy Quattro/Quickshell, `curl`, `wl-copy`, `omarchy-launch-browser`, and standard shell utilities—rather than installing them silently.
- Document add, inspection, setup, enable, rescan, move, update, validate, troubleshooting, and remove flows. Explicitly disclose that Omarchy Plugins execute unsandboxed with user permissions and can access configured network, browser, clipboard, and protected configuration resources.

## Testing Decisions

Tests should assert externally observable behavior at the highest available seam. API Helper tests should use HTTP fixtures and protected temporary configuration; they must not assert private parsing helpers or command construction details. QML tests should assert visible states, focus, selection, keyboard/mouse actions, and emitted helper requests rather than internal property layout. A real Quattro smoke test is required because manifest discovery, bar placement, panel lifecycle, browser launching, and clipboard integration depend on the shell runtime.

The API Helper test matrix must cover profile validation before save, permission enforcement, atomic-write failure preservation, token redaction, active/archived merging, duplicate removal, newest-first ordering, both-endpoint search, independent lazy pagination, stale-response protection, partial failure, bounded timeouts, transient retry, `Retry-After`, and distinct `401/403`, `429`, `5xx`, malformed JSON, timeout, and unreachable-host outcomes.

The UI test matrix must cover bar open/focus, immediate recent results, 200 ms debounced search, keyboard navigation, Enter-to-open, visible and shortcut copy, copy-and-close confirmation, Escape close, loading, empty, incomplete, unavailable, and configuration-error states, plus healthy/checking/unavailable connectivity transitions.

Package and smoke verification must cover schema-1 manifest validation, the permanent plugin ID, Quattro compatibility, documented dependencies, add/enable/rescan/move/update/remove lifecycle, and runtime troubleshooting visibility. Prior art is the first-party Omarchy weather, Tailscale, network, and clock plugin patterns for bounded `Process` calls, panel lifecycle, browser launching, and clipboard use.

## Out of Scope

- Implementing bookmark creation, editing, deletion, or tag management.
- Multiple Linkding Connections or profiles.
- Local bookmark caching or offline search.
- Browser-extension behavior.
- A separate launcher application, Walker/Rofi integration, or a second Quickshell instance.
- Silent dependency installation.
- Publishing or distributing the Plugin as part of this specification.

## Further Notes

The primary research notes and prototype remain linked in the Wayfinder effort directory. The Linkding API has separate active and archived endpoints and no documented stock rate limit, so the client must remain conservative for self-hosted deployments and reverse proxies. This specification is ready to be split into implementation tickets; each ticket should preserve the single API Helper seam and the acceptance matrix above.
