# Linkding Search Plugin

This context describes a reusable Omarchy plugin for finding Linkding bookmarks and acting on their saved URLs from the desktop bar.

## Language

**Plugin**:
An installable Omarchy extension that provides Linkding bookmark search from the desktop bar.
_Avoid_: Skill, widget

**Bookmark Picker**:
The searchable field that loads and filters Linkding bookmarks as the user types.
_Avoid_: Search page, bookmark manager

**Bookmark Action**:
One of the two explicit operations available for a selected bookmark: opening its saved URL in the default browser or copying it to the clipboard.
_Avoid_: Browser extension

**Linkding Connection**:
The user-owned configuration containing the Linkding service URL and API token needed by the plugin.
_Avoid_: Account, credentials bundle

**API Helper**:
A narrow command boundary that validates the Linkding Connection and performs the plugin's approved Linkding operations without exposing credentials to the Bookmark Picker.
_Avoid_: Generic HTTP client, service layer

**Tag**:
A Linkding tag name shown and applied as `#name` in the Bookmark Picker. Completing a Tag searches bookmarks with that query; the picker does not create tags.
_Avoid_: Hashtag create, label
