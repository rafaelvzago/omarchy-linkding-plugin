# Decide packaging, compatibility, and installation guidance

Type: grilling
Status: resolved
Blocked by: 01

## Question

Given the schema-1 Quattro plugin contract, what permanent plugin identity, repository contents, declared compatibility floor, dependency policy, setup/enable/update/remove instructions, and user-facing security disclosure should the implementation-ready specification require?

## Comments

## Answer

The package identity is `io.github.rafaelvzago.linkding`, with MIT licensing. The repository must contain the schema-1 `manifest.json`, `BarWidget.qml`, internal `Panel.qml`, API/config helper, setup helper, `README.md`, and `LICENSE`; a preview image is optional.

The compatibility promise is Omarchy Quattro with plugin schema 1 only. Runtime dependencies are documented—not silently installed—as Omarchy Quattro/Quickshell, `curl`, `wl-copy`, `omarchy-launch-browser`, and standard shell utilities.

README installation guidance must cover:

1. `omarchy plugin add <git-url>`
2. Inspecting the unsandboxed plugin
3. Running the setup helper to create and validate the Linkding Connection
4. `omarchy plugin enable io.github.rafaelvzago.linkding`
5. Moving the widget if desired
6. Omarchy update and remove commands

The README must prominently disclose that plugins run unsandboxed with the user's permissions and that this plugin reads the protected Linkding Connection and invokes network, browser, and clipboard commands. It must also document `omarchy plugin validate`, plugin listing, and Quickshell log inspection for verification and troubleshooting.
