# Linkding Bookmark Picker for Omarchy Quattro

Search all active and archived Linkding bookmarks directly from the Omarchy bar. Select a result to open it in the configured default browser, or copy its URL to the Wayland clipboard.

## Compatibility and permissions

This plugin targets **Omarchy Quattro, plugin schema 1**. It is not tested or advertised as compatible with legacy Omarchy shells. Plugins run unsandboxed inside the user’s long-running Omarchy shell: this package can execute user-level processes, contact the configured Linkding server, launch the default browser, write the clipboard, and read/write its protected configuration file. Inspect the source before enabling it.

Runtime tools are provided by the host and are not installed by this plugin: Omarchy Quattro/Quickshell, Python 3, standard shell utilities, `curl`, `wl-copy`, and `omarchy-launch-browser`.

## Install and configure

```sh
omarchy plugin add <git-url>
omarchy plugin inspect io.github.rafaelvzago.linkding
omarchy plugin enable io.github.rafaelvzago.linkding
```

Configure the user-owned Linkding connection from a terminal. The token is prompted without echoing, validated against `/api/user/profile/`, and atomically saved as `${XDG_CONFIG_HOME:-$HOME/.config}/linkding-search-plugin/config.json` (directory `0700`, file `0600`):

```sh
~/.config/omarchy/plugins/io.github.rafaelvzago.linkding/linkding-setup
```

The URL and token can be edited manually afterward; preserve JSON fields `baseUrl` and `apiToken` and the restrictive permissions. The token is never placed in QML arguments, URLs, notifications, or logs.

## Lifecycle and troubleshooting

```sh
omarchy plugin list --json
omarchy plugin inspect io.github.rafaelvzago.linkding
omarchy plugin validate ~/.config/omarchy/plugins/io.github.rafaelvzago.linkding
omarchy-shell shell rescanPlugins
omarchy bar move io.github.rafaelvzago.linkding --section left   # or center/right
omarchy plugin update io.github.rafaelvzago.linkding
omarchy plugin disable io.github.rafaelvzago.linkding
omarchy plugin remove io.github.rafaelvzago.linkding
```

For a manual install, copy this directory to `~/.config/omarchy/plugins/io.github.rafaelvzago.linkding/`, rescan, then enable it. Exact command names can vary with the installed Quattro release; `omarchy plugin --help` is authoritative.

If the bar reports missing or unsafe configuration, rerun `linkding-setup` and check file modes. `authentication-failed`, `unreachable`, `timeout`, `rate-limited`, `server-failed`, and `invalid-response` are intentionally distinct. The bar health color only probes unauthenticated `/health`; it never sends the API token. Inspect shell errors with:

```sh
qs log -p "$OMARCHY_PATH/shell" --tail 100
```

## Development checks

```sh
python3 -m unittest discover -s tests -v
qmllint -I /usr/share/omarchy/shell BarWidget.qml Panel.qml
python3 -m json.tool manifest.json >/dev/null
python3 -m py_compile linkding_helper.py
omarchy plugin validate .
```

The package does not start a second Quickshell process and has no automatic install or secret-store lifecycle hooks. Setup is intentionally explicit and user-owned.
