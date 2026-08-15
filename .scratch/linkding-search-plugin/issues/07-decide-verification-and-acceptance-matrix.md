# Decide the verification and acceptance matrix

Type: grilling
Status: resolved
Blocked by: 03, 04, 05, 06

## Question

Given the complete architecture, interaction, search, connectivity, credential, and packaging decisions, what observable acceptance criteria and verification matrix must the implementation satisfy before the Linkding Search Plugin is considered ready for handoff to implementation?

## Comments

## Answer

The implementation must pass three verification layers: automated helper/API tests, QML/UI state and interaction tests where practical, and a manual smoke test on a real Omarchy Quattro installation.

Automated configuration/security checks must verify authenticated profile validation before saving, `0700` directory and `0600` file modes, rejection of unsafe or invalid configuration, atomic writes that preserve the previous config on failure, and absence of the token from URLs, logs, notifications, clipboard contents, and user-visible errors.

API fixtures must cover active/archived stream merging, duplicate-ID removal, newest-first ordering, querying both endpoints, independent lazy pagination, stale-response protection, visible partial failure, and distinct handling for `401/403`, `429`, `5xx`, timeouts, malformed JSON, and unreachable hosts.

Manual UI acceptance must cover clicking the bar icon, automatic search focus, immediate recent results, debounced search, keyboard navigation, Enter-to-open, Ctrl+C-to-copy-and-close, Escape-to-close, understandable loading/empty/unavailable/configuration-error states, and healthy/checking/unavailable connectivity transitions.

Package acceptance requires successful manifest validation, ID `io.github.rafaelvzago.linkding`, schema-1 `bar-widget` entry point, complete dependency and security documentation, and successful add, enable, rescan, move, update, and remove operations on Quattro.

The map is complete when `/to-spec` can collapse these decisions into one implementation-ready specification with no unresolved product, security, API, UX, or packaging choices. Implementation remains outside this map.
