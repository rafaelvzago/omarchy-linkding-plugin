# Prototype the Bookmark Picker interaction

Type: prototype
Status: resolved
Blocked by: 01, 02

## Question

What concrete keyboard-and-mouse interaction—including initial loading, search updates, result rows, open and copy actions, copied confirmation/closure behavior, loading and empty states, and errors—best realizes the settled product choices within Omarchy's actual UI primitives?

## Comments

Prototype artifact: [bookmark-picker.html](../prototype/bookmark-picker.html). Open it locally and switch variants with `?variant=A`, `?variant=B`, or `?variant=C` (the bottom switcher also changes the URL).

## Answer

Choose **Variant A — Compact command palette**. The Bookmark Picker is a focused, single-column keyboard-first surface anchored to the bar icon:

- Opening focuses the search field and immediately loads recent bookmarks.
- Each result row shows title, domain, description, and tags, with a visible `Copy URL` action.
- Typing filters the server-backed result stream; arrow keys move selection; `Enter` opens the selected URL in the default browser; `Ctrl+C` copies it.
- `Escape` closes the picker. Copying closes the picker and provides brief confirmation.
- Loading, empty, unavailable, and configuration-error states occupy the same surface without changing the bar layout.
- The bar status indicator remains outside the picker and represents Linkding reachability.

The prototype is the primary interaction reference at [bookmark-picker.html](../prototype/bookmark-picker.html). This workspace has no Git repository, so it could not be captured on a separate prototype branch.
