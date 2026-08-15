# Specify the Linkding Search Plugin

Label: `wayfinder:map`

## Destination

An implementation-ready specification for a reusable Omarchy plugin that opens a keyboard-first Bookmark Picker from a clickable bar icon, searches every bookmark on one Linkding server, and provides separate open-in-default-browser and copy-URL actions using a securely stored API token.

Specification: [Linkding Search Plugin — Implementation Specification](spec.md)

## Notes

Use the `grilling`, `domain-modeling`, `research`, and `prototype` skills as indicated by each ticket. Planning only: implementation and publication are outside this map. Preserve the settled preferences from the initial interview: immediate initial results; debounced remote search; title, domain, tags, and description in results; keyboard and mouse operation; recent-first initial results; errors rather than an offline bookmark cache; setup prompts for URL and token and validates before saving; later edits happen directly in the user-owned configuration; one Linkding connection; copying closes the picker; and the bar icon continuously represents connectivity.

## Decisions so far

- [Research the Omarchy plugin and bar integration contract](issues/01-research-omarchy-plugin-contract.md) — Use a schema-1 Quattro bar widget with an internal keyboard panel, established browser/clipboard commands, and an explicit secure setup helper.
- [Research the Linkding bookmark search API contract](issues/02-research-linkding-api-contract.md) — Authenticate by header, merge independently paginated active and archived searches, validate setup through the profile endpoint, and poll unauthenticated health conservatively.
- [Decide the plugin architecture and credential boundary](issues/03-decide-plugin-architecture-and-credential-boundary.md) — Keep QML presentation separate from a narrow API helper; store one validated Linkding Connection in a protected XDG JSON file and never expose its token.
- [Prototype the Bookmark Picker interaction](issues/04-prototype-the-bookmark-picker-interaction.md) — Adopt the compact command-palette layout with focused search, rich result rows, explicit open/copy actions, and in-place loading/error states.
- [Decide the search and connectivity policy](issues/05-decide-search-and-connectivity-policy.md) — Merge 20 newest active/archived results, debounce and lazily paginate server-native searches, reject partial results, retry only transient failures, and expose conservative health states.
- [Decide packaging, compatibility, and installation guidance](issues/06-decide-packaging-compatibility-and-installation.md) — Publish as `io.github.rafaelvzago.linkding` under MIT for Omarchy Quattro/schema 1, with explicit dependencies, setup, lifecycle, validation, and unsandboxed-security documentation.
- [Decide the verification and acceptance matrix](issues/07-decide-verification-and-acceptance-matrix.md) — Require automated API/security checks, practical UI tests, Quattro smoke testing, and complete package lifecycle validation before implementation handoff.

## Not yet specified

- No unresolved decisions remain before specification handoff.

## Out of scope

- Implementing or publishing the plugin.
- Creating, editing, deleting, or tagging bookmarks.
- Multiple Linkding connections, local bookmark caching, and browser-extension behavior.
