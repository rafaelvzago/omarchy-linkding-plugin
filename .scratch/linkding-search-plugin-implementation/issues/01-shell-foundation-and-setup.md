# 01 — Build the installable Quattro shell foundation and secure setup flow

**What to build:** An installable `io.github.rafaelvzago.linkding` Omarchy Quattro bar Plugin whose icon opens the compact Bookmark Picker, together with a user-run setup flow that validates and securely stores one Linkding Connection. The picker must explain missing or invalid configuration instead of failing silently.

**Blocked by:** None — can start immediately.

**Status:** done

- [x] The schema-1 manifest identifies a single `bar-widget` with the permanent plugin ID and right-section default.
- [x] The bar icon uses native Quattro widget/panel lifecycle primitives and opens/closes the compact Bookmark Picker without launching a second shell.
- [x] The Bookmark Picker focuses its search field on open and has a visible configuration-error state when the Linkding Connection is missing or invalid.
- [x] The setup helper prompts with hidden token input, validates the base URL and token through the authenticated profile endpoint before replacement, and preserves the prior valid configuration if writing fails.
- [x] The Linkding Connection is stored outside shell settings in a user-owned directory with mode `0700` and a file with mode `0600`.
- [x] Unsafe permissions, malformed values, unsupported URLs, and failed validation are rejected without exposing the token.
- [x] Automated tests cover setup validation, permission enforcement, atomic replacement, redirect safety, and the bar/picker configuration state.
