# Decide the plugin architecture and credential boundary

Type: grilling
Status: resolved
Blocked by: 01, 02

## Question

Given the researched Omarchy and Linkding contracts, which component boundaries, execution flow, configuration schema, token-storage permissions, connection-validation behavior, and dependency strategy should the implementation-ready specification require?

## Comments

## Answer

The implementation-ready architecture is split into two layers:

- QML owns the `BarWidget`, `Panel`, picker state, focus, loading/error presentation, and user actions.
- A narrow executable API helper owns configuration loading, permission checks, URL/token validation, authenticated Linkding requests, and health checks. It exposes purpose-built operations such as `validate`, `recent`, `search`, and `health`, rather than generic HTTP access.

The Linkding Connection is stored outside `shell.json` in an XDG user configuration directory. The setup helper prompts for the base URL and API token, validates them against `/api/user/profile/`, creates the directory with mode `0700`, and atomically writes a JSON file with mode `0600`:

```json
{
  "baseUrl": "https://linkding.example.com",
  "apiToken": "..."
}
```

Manual edits remain supported after setup. Missing, unreadable, unsafe, or invalid configuration leaves the bar icon present but shows an actionable setup error when clicked. The token may exist in memory and in the protected config file, but must never appear in URLs, logs, notifications, clipboard contents, or user-visible errors; the helper must minimize process-argument exposure.

This preserves a stable UI/helper seam and keeps credential handling out of QML.
