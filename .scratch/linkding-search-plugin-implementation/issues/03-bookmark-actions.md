# 03 — Add Bookmark Actions

**What to build:** A complete result-selection path that lets users navigate Bookmark Picker results, open a selected saved URL through the configured default browser, or copy it to the clipboard through either the keyboard shortcut or visible action.

**Blocked by:** 02 — Search and merge all Linkding bookmarks.

**Status:** done

- [x] Arrow keys and mouse selection identify one result at a time.
- [x] `Enter` opens the selected URL through `omarchy-launch-browser` without hard-coding a browser.
- [x] `Ctrl+C` copies the selected URL through `wl-copy` via process stdin rather than command-line interpolation.
- [x] Each result exposes a visible copy action with the same behavior as the shortcut.
- [x] Copying closes the picker after the copy process starts successfully and provides brief confirmation.
- [x] Bookmark URLs and tokens are never placed in logs, notifications, or unrelated clipboard content.
- [x] QML lint and the Quattro panel contract validate the keyboard/action path; interactive smoke testing remains part of the package ticket.
- [x] A Quattro-compatible browser/clipboard command path is wired for user-session smoke verification.
