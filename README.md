# Linkding bookmark picker for Omarchy Quattro

Search active and archived Linkding bookmarks from the Omarchy bar. Select a result to open it in the configured default browser, or copy its URL to the Wayland clipboard.

![Linkding bookmark search panel in the Omarchy bar](preview.png)

## Compatibility and permissions

This plugin targets Omarchy Quattro with plugin schema 1. It is not tested on legacy Omarchy shells.

Plugins run unsandboxed inside the user's long-running Omarchy shell. This one can start user-level processes, talk to the configured Linkding server, launch the default browser, write the clipboard, and read and write its protected configuration file. Read the source before you enable it.

The host already has the tools below. The plugin does not install them:

- Omarchy Quattro and Quickshell
- Python 3 and standard shell utilities
- `curl`
- `wl-copy`
- `omarchy-launch-browser`

## Install and configure

Install the plugin from its public repository:

```sh
omarchy plugin add https://github.com/rafaelvzago/omarchy-linkding-plugin.git
omarchy plugin inspect io.github.rafaelvzago.linkding
omarchy plugin enable io.github.rafaelvzago.linkding
```

Configure the Linkding connection in a terminal. The setup helper wants an HTTPS Linkding URL, asks for the token without echoing it, checks the token against `/api/user/profile/`, and writes `${XDG_CONFIG_HOME:-$HOME/.config}/linkding-search-plugin/config.json` atomically. HTTP URLs, including localhost and loopback, are rejected before any request so the token and bookmark data are never sent in cleartext.

```sh
~/.config/omarchy/plugins/io.github.rafaelvzago.linkding/linkding-setup
```

The configuration directory is mode `0700` and the file is mode `0600`. If you edit the file by hand, keep the JSON fields `baseUrl` and `apiToken`, use an `https://` base URL, and leave those permissions as they are. Existing HTTP configurations fail with `https-required`; turn on TLS for Linkding and run `linkding-setup` again. The token is never passed as a QML argument, put in a URL, shown in a notification, or written to logs.

## Search

Open the Linkding panel from the bar or its configured hotkey, then type.

Plain text searches active and archived bookmarks. The list loads more results when you reach the end.

Tags work like a hashtag search:

1. Type `#`. The panel lists Tags that already exist in Linkding.
2. Keep typing after `#` to filter that list by name prefix.
3. Move with Up and Down, then press Enter or click a Tag. The picker finishes the current `#` token and searches bookmarks with Linkding's `#tag` query.
4. After a Tag is applied, the field holds something like `#work`. Type more words after a space to narrow the search, or type another `#` to pick a second Tag the same way.

A name that is not an existing Tag only filters the Tag list. The picker does not create Tags.

Actions on a bookmark result:

- Click a result to open its URL in the default browser.
- Click the copy button on a result to copy its URL.
- Use Up and Down to select a result, then press Enter to open it.
- Press Ctrl+C to copy the selected URL.
- Press Escape to close the panel.
- Press Tab, or Shift+Tab, to switch between bar panels.

While the current token starts with `#`, Up, Down, and Enter move through Tags instead of bookmarks.

## Manual install and lifecycle

To install by hand, copy this directory to `~/.config/omarchy/plugins/io.github.rafaelvzago.linkding/`, rescan the shell, and enable the plugin. Exact command names can vary with the installed Quattro release. Run `omarchy plugin --help` for the commands your installation supports.

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

The plugin does not start a second Quickshell process and has no automatic install or secret-store lifecycle hooks. You run setup yourself. Disabling or removing the plugin does not touch the separate Linkding configuration file.

## Troubleshooting

If the bar reports missing or unsafe configuration, run `linkding-setup` again and check the directory and file modes. The helper reports these connection states separately: `authentication-failed`, `unreachable`, `timeout`, `rate-limited`, `server-failed`, and `invalid-response`.

The bar health color checks unauthenticated `/health`. It never sends the API token. To inspect shell errors, run:

```sh
qs log -p "$OMARCHY_PATH/shell" --tail 100
```

## Local validation

From the repository root:

```sh
python3 -m unittest discover -s tests -v
qmllint -I /usr/share/omarchy/shell BarWidget.qml Panel.qml
python3 -m json.tool manifest.json >/dev/null
python3 -m py_compile linkding_helper.py
omarchy plugin validate .
```

## Maintainers

Before submitting this plugin to the marketplace:

- Keep the code in a public GitHub repository.
- Keep a valid `manifest.json` at the repository root.
- Keep `README.md` and the MIT `LICENSE` at the repository root.
- Check that installation and removal do not need automatic secret-store lifecycle hooks.
- Run the local validation commands above, including `omarchy plugin validate .`.
- Submit the repository through the [Omarchy plugin issue form](https://github.com/HANCORE-linux/omarchy-plugin-marketplace/issues/new?template=submit-plugin.yml).
- Suggested category: `Productivity`.
- Suggested tags: `Linkding`, `bookmarks`, `search`, `bar-widget`.

The marketplace validates listings, not plugin security. Review the code and document any permissions before submitting.
