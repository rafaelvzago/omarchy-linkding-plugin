# Research the Omarchy plugin and bar integration contract

Type: research
Status: resolved
Blocked by:

## Question

According to the official Omarchy plugin development documentation and relevant primary platform sources, what exact manifest, directory, lifecycle-hook, bar-integration, launcher/UI, browser-opening, clipboard, configuration, secret-permission, dependency, installation, and compatibility contracts constrain this reusable Plugin and its Bookmark Picker?

## Comments

## Answer

Resolved in [Omarchy plugin contract for the Linkding Bookmark Picker](../research/omarchy-plugin-contract.md). The reusable integration should be a schema-1 Quattro `bar-widget` with an internal keyboard panel; browser and clipboard actions should use `omarchy-launch-browser` and `wl-copy`. Omarchy defines no lifecycle hooks or secret-store contract, so a documented, explicit setup helper must validate and atomically create the user-owned `0600` connection file.
