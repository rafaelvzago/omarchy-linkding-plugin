# Omarchy plugin contract for the Linkding Bookmark Picker

Research date: 2026-08-14. Sources are first-party Omarchy documentation and source code, plus the development guide named in the ticket.

## Decision-ready conclusion

Implement the reusable picker as a **Quattro `bar-widget` plugin**, not as a legacy Waybar edit and not as a separate launcher process. Its `BarWidget.qml` should render one clickable icon and load an internal `Panel.qml`; that panel should use the shell's keyboard-panel primitives, fetch Linkding through a bounded child process, and invoke established Omarchy commands for browser and clipboard actions. The plugin repository itself is the installable unit and must have `manifest.json` at its root.

The platform has no declared install/enable/disable/uninstall lifecycle-hook API and no plugin secret-store API. Therefore first-run URL/token prompting, config creation, mode enforcement, validation, and migration are application responsibilities, not manifest hooks. Keep them explicit, idempotent, user-owned, and documented.

## Exact platform contract

### Repository and installation

- A third-party plugin is a Git repository with `manifest.json` at its root. `omarchy plugin add <git-url>` clones it to `~/.config/omarchy/plugins/<id>/`; it initially lands disabled so the user can inspect unsandboxed code, and `omarchy plugin enable <id>` activates it. Updates are diff-shown fast-forward pulls; removal is `omarchy plugin remove <id>`. Manual installation requires copying into that directory, rescanning, then enabling. ([official shell reference](https://github.com/basecamp/omarchy/blob/quattro/docs/omarchy-shell.md#installing-a-third-party-plugin))
- Development should start from `omarchy plugin clone omarchy.clock --edit`; saved files hot-reload and `omarchy-shell shell rescanPlugins` forces rediscovery. The development guide says plugins execute unsandboxed, with user permissions, inside the single long-running Omarchy shell and must not launch another Quickshell instance. ([development guide](https://omarchyplugins.com/develop.html#start), [official shell reference](https://github.com/basecamp/omarchy/blob/quattro/docs/omarchy-shell.md))

### Manifest and directory

The minimum applicable manifest is:

```json
{
  "schemaVersion": 1,
  "id": "io.github.<owner>.linkding",
  "name": "Linkding Bookmark Picker",
  "version": "1.0.0",
  "author": "<author>",
  "license": "MIT",
  "description": "Search Linkding bookmarks from the Omarchy bar.",
  "kinds": ["bar-widget"],
  "entryPoints": { "barWidget": "BarWidget.qml" },
  "barWidget": {
    "displayName": "Linkding",
    "category": "Productivity",
    "allowMultiple": false,
    "defaultSection": "right"
  }
}
```

- The registry requires schema version `1` plus `id`, `name`, `version`, nonempty `kinds`, and object `entryPoints`. IDs cannot contain `/` or `..`; entry points must be nonempty relative paths without `..`. `defaultSection`, if supplied, is `left`, `center`, or `right`. ([registry source](https://github.com/basecamp/omarchy/blob/quattro/shell/services/PluginRegistry.qml), [development manifest](https://omarchyplugins.com/develop.html#contract))
- The relevant kind/key/file mapping is `bar-widget` / `entryPoints.barWidget` / `BarWidget.qml`. `Panel.qml` can be loaded internally and does **not** require a separately declared `panel` kind. A practical repository also contains model/helper files, `README.md`, `LICENSE`, and optionally `preview.png`. ([development guide](https://omarchyplugins.com/develop.html#contract), [built-in clock example](https://github.com/basecamp/omarchy/tree/quattro/shell/plugins/panels/clock))
- Choose the permanent reverse-domain-style namespaced ID before publishing, and keep `moduleName` identical in the QML components. The `omarchy.clonedFrom` field is development-only clone metadata and should be removed from the published manifest. ([development guide](https://omarchyplugins.com/develop.html#finished))

### Bar and panel lifecycle

- `BarWidget.qml` should derive from `BarWidget`, render a `WidgetButton`, toggle on left click, load `Panel.qml`, inject `bar`, `anchorItem`, and `hostWidget`, and forward `opened`, `popoutSwitchClosing`, `open()`, `close()`, `toggle()`, and `closeForPopoutSwitch()`. Omitting this forwarding causes panels that do not reopen correctly. ([bar/panel example](https://omarchyplugins.com/develop.html#entry-point))
- `Panel.qml` should derive from `Panel`; `KeyboardPanel` anchors it to the icon and manages focus, while `PanelKeyCatcher` supplies Escape-close and bar-panel tab switching. On open, focus the search field and load recent results immediately. This is the native contract for the requested searchable popout; do not introduce Walker/Rofi merely to obtain a search field. ([bar/panel example](https://omarchyplugins.com/develop.html#entry-point), [built-in Tailscale panel](https://github.com/basecamp/omarchy/blob/quattro/shell/plugins/panels/tailscale/Panel.qml))
- A bar widget is enabled by presence in `bar.layout.<section>` of `~/.config/omarchy/shell.json`; `defaultSection` determines initial placement and `omarchy bar move <id> --section <section>` moves it. `allowMultiple: false` enforces one instance. User `shell.json` is canonical once created and is not deep-merged. ([shell configuration contract](https://github.com/basecamp/omarchy/blob/quattro/docs/omarchy-shell.md#shelljson))
- There are no install, enable, disable, or uninstall hook fields in the documented manifest or registry validator. Do not rely on executable lifecycle files being called automatically. This is an inference from the complete documented schema and validator. ([registry source](https://github.com/basecamp/omarchy/blob/quattro/shell/services/PluginRegistry.qml))

### API process, browser, and clipboard

- Built-in plugins perform bounded HTTP calls with Quickshell `Process` running argument-array `curl` commands, parse stdout, debounce search, and prevent overlapping requests. Follow that pattern for Linkding: use timeouts, cancel/ignore stale generations, never form a `bash -c` string containing the token, and never log the command array. (`curl` and the API token are consequently explicit dependencies.) ([built-in weather panel](https://github.com/basecamp/omarchy/blob/quattro/shell/plugins/panels/weather/Panel.qml))
- Open a selected URL using `Quickshell.execDetached(["omarchy-launch-browser", url])`. That command resolves Omarchy's configured/default XDG browser and launches it through the user session. Do not hard-code a browser and do not use the Linkding token in the opened URL. ([built-in Tailscale service](https://github.com/basecamp/omarchy/blob/quattro/shell/plugins/panels/tailscale/Service.qml), [browser launcher source](https://github.com/basecamp/omarchy/blob/master/bin/omarchy-launch-browser))
- Copy with `wl-copy`, which first-party plugins declare as a dependency. Prefer a helper process receiving the URL via stdin. The existing first-party code safely shell-quotes values before piping when it must use `bash -c`; raw interpolation is forbidden. Close the picker only after the copy process has been started successfully, per the product decision. ([Tailscale requirements and service](https://github.com/basecamp/omarchy/tree/quattro/shell/plugins/panels/tailscale), [network panel implementation](https://github.com/basecamp/omarchy/blob/quattro/shell/plugins/panels/network/Panel.qml))

### Configuration and secrets

- Omarchy exposes environment access and arbitrary user-level processes to unsandboxed plugin QML, but neither the manifest nor shell configuration defines secret storage or lifecycle prompts. Keep connection data outside `shell.json` so the token is not mixed into bar layout/settings. This is an architectural inference from the platform contract. ([shell configuration contract](https://github.com/basecamp/omarchy/blob/quattro/docs/omarchy-shell.md#shelljson))
- Recommended contract: a checked-in executable setup helper prompts on a controlling terminal (token input hidden), validates the URL/token before replacing anything, creates a plugin-specific directory beneath `${XDG_CONFIG_HOME:-$HOME/.config}`, and atomically writes a user-owned config with directory mode `0700` and file mode `0600`. The QML runtime reads it through a helper that returns data without echoing/logging the token. Since no install hook exists, README/setup UI must tell the user to run this helper after installation. Manual editing remains supported afterward.
- Treat an unreadable file, permissive file mode, missing fields, non-HTTPS remote URL (localhost may be a documented exception), or failed authentication as an actionable configuration error. Never cache the token or bookmarks in shell settings, command-line URLs, notifications, logs, or clipboard.

### Dependencies and compatibility

- Runtime dependencies are Omarchy **Quattro** with its single `omarchy-shell`/Quickshell runtime, `curl`, `wl-copy`, and `omarchy-launch-browser`; shell/core utilities are needed by setup. Declare all of these in README because the manifest provides no dependency installer or dependency metadata contract. ([development guide warning](https://omarchyplugins.com/develop.html#overview), [official shell reference](https://github.com/basecamp/omarchy/blob/quattro/docs/omarchy-shell.md), [Tailscale requirements](https://github.com/basecamp/omarchy/tree/quattro/shell/plugins/panels/tailscale))
- The docs are explicitly Quattro-specific. Compatibility should therefore be stated as “Omarchy Quattro/plugin schema 1,” not an unverified historical Omarchy version range. Validate with `omarchy plugin validate ~/.config/omarchy/plugins/<id>` and inspect `omarchy plugin list --json`; runtime QML errors are visible through `qs log -p "$OMARCHY_PATH/shell" --tail 100`. ([development validation/troubleshooting](https://omarchyplugins.com/develop.html#validate), [development troubleshooting](https://omarchyplugins.com/develop.html#troubleshooting))

## Constraints to carry into the specification

1. Native bar icon plus internal keyboard panel; no second shell/launcher.
2. Schema-1 `bar-widget`, single instance, right-section default.
3. Immediate recent-results request, then debounced server-side searches with stale-response protection.
4. Enter opens through `omarchy-launch-browser`; a distinct visible/keyboard copy action uses `wl-copy` and closes afterward.
5. Setup is an explicit helper, not an Omarchy lifecycle hook; validated atomic `0600` user config.
6. Token stays out of argv where feasible and always out of URLs, logs, shell settings, notifications, and repository content.
7. README documents unsandboxed execution, dependencies, setup, validation, enable/move/remove, and Quattro-only compatibility.
