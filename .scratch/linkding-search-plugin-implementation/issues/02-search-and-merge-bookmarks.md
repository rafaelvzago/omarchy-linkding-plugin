# 02 — Search and merge all Linkding bookmarks

**What to build:** A working Bookmark Picker search path that loads the newest active and archived Linkding bookmarks, merges them into one result list, searches both collections with Linkding-native semantics, and loads additional results lazily.

**Blocked by:** 01 — Build the installable Quattro shell foundation and secure setup flow.

**Status:** done

- [x] Opening the configured picker requests up to 20 results from both active and archived collections and presents one newest-first list.
- [x] Results are merged by bookmark ID, deduplicated, and titleless bookmarks fall back to their URL for identification.
- [x] Typing applies a 200 ms debounce and sends the unchanged URL-encoded query to both collections.
- [x] Linkding-native search behavior, including tags, quoted phrases, boolean operators, and special terms, remains authoritative.
- [x] Active and archived pagination remain independent and load more results only when the user reaches the end of the current list.
- [x] Obsolete requests cannot overwrite results for a newer query; a latest-query queue prevents stale in-flight output from replacing it.
- [x] API Helper tests cover merging, ordering, duplicate removal, both-endpoint search, pagination, and request construction.
- [x] The picker visibly distinguishes loading, empty, and successful result states.
