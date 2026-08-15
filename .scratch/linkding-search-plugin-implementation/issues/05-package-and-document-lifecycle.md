# 05 — Package and document the Plugin lifecycle

**What to build:** A release-ready Quattro Plugin package whose lifecycle can be inspected, installed, enabled, rescanned, moved, updated, troubleshot, and removed by following complete documentation, with the full automated and manual acceptance matrix recorded.

**Blocked by:** 01 — Build the installable Quattro shell foundation and secure setup flow; 02 — Search and merge all Linkding bookmarks; 03 — Add Bookmark Actions; 04 — Add resilience and connectivity states.

**Status:** done

- [x] Manifest validation succeeds for `io.github.rafaelvzago.linkding` under schema 1 with the `bar-widget` entry point.
- [x] The package declares MIT licensing and documents compatibility with Omarchy Quattro only.
- [x] README documentation lists Quickshell/Quattro, `curl`, `wl-copy`, `omarchy-launch-browser`, and standard shell utilities without silently installing dependencies.
- [x] Documentation covers inspection, setup, enable, rescan, bar movement, update, validation, troubleshooting, and removal.
- [x] Documentation prominently discloses unsandboxed execution and access to network, browser, clipboard, and protected configuration resources.
- [x] Automated tests and static Quattro smoke checks cover the acceptance matrix from the source specification.
- [x] Lifecycle commands are documented; live add/enable/update/remove verification requires an installed Quattro host and was not runnable in this workspace.
