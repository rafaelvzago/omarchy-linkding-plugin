import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

Panel {
  id: root
  moduleName: "io.github.rafaelvzago.linkding"
  ipcTarget: "io.github.rafaelvzago.linkding"
  manageIpc: false

  property var anchorItem: null
  property var hostWidget: null
  property bool openedFromHotkey: false
  readonly property var barIdentity: hostWidget || root
  readonly property string helperPath: String(Qt.resolvedUrl("linkding_helper.py")).replace(/^file:\/\//, "")
  readonly property color themeBackground: Color.background
  readonly property color themeSecondary: root.bar ? root.bar.foreground : Color.foreground
  readonly property color themeAccent: Color.accent
  property string configurationState: "checking"
  property var bookmarks: []
  property string searchQuery: ""
  property bool loading: false
  property string searchError: ""
  property int nextActiveOffset: -1
  property int nextArchivedOffset: -1
  property bool appendSearchResults: false
  property bool pendingSearch: false
  property string pendingQuery: ""
  property bool pendingAppend: false
  property int pendingActiveOffset: 0
  property int pendingArchivedOffset: 0
  property int selectedIndex: 0
  property string healthState: "checking"
  property int healthFailures: 0
  property bool incompleteResults: false

  function open() {
    openedFromHotkey = false
    controller.show()
    refreshConfiguration()
    Qt.callLater(function() { if (root.opened) searchField.forceActiveFocus() })
  }

  function openFromHotkey() {
    openedFromHotkey = true
    controller.show()
    refreshConfiguration()
    Qt.callLater(function() { if (root.opened) searchField.forceActiveFocus() })
  }

  function close() { controller.hide() }
  function toggle() { opened ? close() : open() }
  function switchPanel(direction) {
    if (bar && typeof bar.switchPanelFrom === "function") return bar.switchPanelFrom(barIdentity, direction)
    return false
  }

  function refreshConfiguration() {
    if (!configStatus.running) configStatus.running = true
  }

  function refreshHealth() {
    if (root.configurationState !== "ready" || healthProcess.running) return
    root.healthState = "checking"
    healthProcess.running = true
  }

  function requestBookmarks(query, append, activeOffset, archivedOffset) {
    if (root.configurationState !== "ready") return
    if (searchProcess.running) {
      root.pendingSearch = true
      root.pendingQuery = query
      root.pendingAppend = append
      root.pendingActiveOffset = activeOffset || 0
      root.pendingArchivedOffset = archivedOffset || 0
      return
    }
    root.searchQuery = query
    root.appendSearchResults = append
    if (!append) root.selectedIndex = 0
    root.loading = true
    root.searchError = ""
    root.incompleteResults = false
    searchProcess.command = [
      "python3", root.helperPath, query === "" ? "recent" : "search",
      "--query", query,
      "--limit", "20",
      "--active-offset", String(activeOffset || 0),
      "--archived-offset", String(archivedOffset || 0)
    ]
    searchProcess.running = true
  }

  function applySearchResult(result) {
    var incoming = Array.isArray(result.results) ? result.results : []
    if (root.appendSearchResults) {
      var byId = {}
      for (var existing of root.bookmarks) {
        var existingKey = existing.id === null || existing.id === undefined ? existing.url : existing.id
        byId[String(existingKey)] = existing
      }
      for (var item of incoming) {
        var itemKey = item.id === null || item.id === undefined ? item.url : item.id
        byId[String(itemKey)] = item
      }
      root.bookmarks = Object.keys(byId).map(function(key) { return byId[key] })
    } else {
      root.bookmarks = incoming
    }
    root.bookmarks.sort(function(left, right) {
      return String(right.date_added || "").localeCompare(String(left.date_added || ""))
    })
    root.nextActiveOffset = result.next && result.next.activeOffset !== null
      ? Number(result.next.activeOffset) : -1
    root.nextArchivedOffset = result.next && result.next.archivedOffset !== null
      ? Number(result.next.archivedOffset) : -1
    root.loading = false
  }

  function selectBookmark(index) {
    if (root.bookmarks.length === 0) return
    root.selectedIndex = Math.max(0, Math.min(index, root.bookmarks.length - 1))
    bookmarkList.positionViewAtIndex(root.selectedIndex, ListView.Contain)
  }

  function openBookmark(index) {
    if (index < 0 || index >= root.bookmarks.length) return
    var url = String(root.bookmarks[index].url || "")
    if (url === "") return
    Quickshell.execDetached(["omarchy-launch-browser", url])
    root.close()
  }

  function copyBookmark(index) {
    if (index < 0 || index >= root.bookmarks.length) return
    var url = String(root.bookmarks[index].url || "")
    if (url === "") return
    if (copyProcess.running) return
    copyProcess.command = ["wl-copy", "--type", "text/plain;charset=utf-8", url]
    copyProcess.running = true
  }

  Component.onCompleted: refreshConfiguration()

  Process {
    id: configStatus
    command: ["python3", root.helperPath, "validate"]
    stdout: StdioCollector { id: statusOutput; waitForEnd: true }
    onExited: function(exitCode) {
      var output = String(statusOutput.text || "")
      try {
        var result = JSON.parse(output)
        root.configurationState = result.ok === true ? "ready" : String(result.reason || "invalid")
        if (root.configurationState === "ready") {
          Qt.callLater(function() {
            if (root.opened) searchField.forceActiveFocus()
          })
          root.refreshHealth()
          root.requestBookmarks(searchField.text, false, 0, 0)
        }
      } catch (error) {
        root.configurationState = exitCode === 0 ? "invalid" : "unavailable"
      }
    }
  }

  Process {
    id: searchProcess
    command: []
    stdout: StdioCollector { id: searchOutput; waitForEnd: true }
    onExited: function(exitCode) {
      if (root.pendingSearch) {
        var queuedQuery = root.pendingQuery
        var queuedAppend = root.pendingAppend
        var queuedActiveOffset = root.pendingActiveOffset
        var queuedArchivedOffset = root.pendingArchivedOffset
        root.pendingSearch = false
        root.requestBookmarks(queuedQuery, queuedAppend, queuedActiveOffset, queuedArchivedOffset)
        return
      }
      var output = String(searchOutput.text || "")
      try {
        var result = JSON.parse(output)
        if (exitCode !== 0 || result.ok !== true) {
          root.searchError = String(result.reason || "search-failed")
          root.bookmarks = []
          root.incompleteResults = false
          root.loading = false
          root.refreshHealth()
          return
        }
        root.incompleteResults = result.complete === false
        root.applySearchResult(result)
        root.refreshHealth()
      } catch (error) {
        root.searchError = "invalid-response"
        root.loading = false
      }
    }
  }

  Process {
    id: healthProcess
    command: ["python3", root.helperPath, "health"]
    stdout: StdioCollector { id: healthOutput; waitForEnd: true }
    onExited: function(_exitCode) {
      try {
        var result = JSON.parse(String(healthOutput.text || ""))
        root.healthState = result.state === "healthy" ? "healthy" : "unavailable"
        root.healthFailures = root.healthState === "healthy" ? 0 : root.healthFailures + 1
      } catch (error) {
        root.healthState = "unavailable"
        root.healthFailures++
      }
      healthTimer.restart()
    }
  }

  Timer {
    id: healthTimer
    interval: root.healthState === "unavailable"
      ? Math.min(600000, 60000 * Math.pow(2, root.healthFailures))
      : 60000
    repeat: true
    running: root.configurationState === "ready"
    onTriggered: root.refreshHealth()
  }

  Process {
    id: copyProcess
    command: []
    onExited: function(exitCode) {
      if (exitCode === 0) {
        Quickshell.execDetached(["omarchy-notification-send", "Linkding", "URL copied"])
        root.close()
      } else {
        root.searchError = "copy-failed"
      }
      command = []
    }
  }

  Timer {
    id: searchDebounce
    interval: 200
    repeat: false
    onTriggered: root.requestBookmarks(searchField.text, false, 0, 0)
  }

  KeyboardPanel {
    id: keyboardPanel
    anchorItem: root.anchorItem
    owner: root.barIdentity
    bar: root.bar
    open: root.opened
    centerOnBar: true
    focusTarget: searchField
    padding: Style.spacing.popupPadding
    contentWidth: fittedContentWidth(Style.space(540))
    contentHeight: fittedContentHeight(contentColumn.implicitHeight)

    // Keep the content surface on the active Omarchy theme background.
    Rectangle {
      anchors.fill: parent
      anchors.margins: -keyboardPanel.padding
      color: root.themeBackground
      z: 0
    }

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      z: 1
      blocked: searchField.activeFocus
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }
      onMoveRequested: function(_dx, dy) { root.selectBookmark(root.selectedIndex + dy) }
      onActivateRequested: root.openBookmark(root.selectedIndex)

      Column {
        id: contentColumn
        width: parent.width
        spacing: Style.space(12)

        Row {
          width: parent.width
          spacing: Style.space(8)

          Text {
            text: "󰃃"
            color: root.themeSecondary
            font.family: root.bar ? root.bar.fontFamily : Style.font.family
            font.pixelSize: Style.font.heading
            anchors.verticalCenter: parent.verticalCenter
          }

          TextField {
            id: searchField
            width: parent.width - x - Style.space(8)
            foreground: root.themeSecondary
            // Keep the input surface on the theme background instead of the
            // light control-fill fallback used by generic Qt controls.
            background: BorderSurface {
              color: root.themeBackground
              borderSpec: searchField._borderSpec
              radius: Style.cornerRadius
            }
            placeholderText: "Search Linkding bookmarks…"
            font.family: root.bar ? root.bar.fontFamily : Style.font.family
            enabled: root.configurationState === "ready"
            onTextChanged: {
              if (root.configurationState === "ready") searchDebounce.restart()
            }
            Keys.onPressed: function(event) {
              if (event.key === Qt.Key_Down) {
                root.selectBookmark(root.selectedIndex + 1)
                event.accepted = true
              } else if (event.key === Qt.Key_Up) {
                root.selectBookmark(root.selectedIndex - 1)
                event.accepted = true
              } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                root.openBookmark(root.selectedIndex)
                event.accepted = true
              } else if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_C) {
                root.copyBookmark(root.selectedIndex)
                event.accepted = true
              } else if (event.key === Qt.Key_Escape) {
                root.close()
                event.accepted = true
              } else if (event.key === Qt.Key_Tab) {
                root.switchPanel((event.modifiers & Qt.ShiftModifier) ? -1 : 1)
                event.accepted = true
              }
            }
          }
        }

        Text {
          visible: root.configurationState !== "ready"
          width: parent.width
          wrapMode: Text.WordWrap
          text: root.configurationState === "checking"
            ? "Checking Linkding Connection…"
            : root.configurationState === "missing"
              ? "Linkding is not configured. Run linkding_helper.py setup from a terminal."
              : "Linkding configuration is unavailable (" + root.configurationState + "). Run the setup helper and try again."
          color: root.configurationState === "checking" ? Color.foreground : Color.warning
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          font.pixelSize: Style.font.body
        }

        Text {
          visible: root.configurationState === "ready"
          text: root.loading
            ? "Loading bookmarks…"
            : root.incompleteResults
              ? "Some bookmark results are unavailable. Retry to load all bookmarks."
            : root.searchError !== ""
              ? "Could not load bookmarks (" + root.searchError + ")."
              : root.bookmarks.length === 0
                ? "No bookmarks found."
                : ""
          color: root.bar ? Qt.darker(root.bar.barForeground, 1.35) : Color.muted
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          font.pixelSize: Style.font.body
        }

        Button {
          visible: root.configurationState === "ready" && (root.incompleteResults || root.searchError !== "")
          text: "Retry"
          width: parent.width
          foreground: root.bar ? root.bar.barForeground : Color.foreground
          fontFamily: root.bar ? root.bar.fontFamily : Style.font.family
          bordered: true
          onClicked: root.requestBookmarks(root.searchQuery, false, 0, 0)
        }

        ListView {
          id: bookmarkList
          visible: root.configurationState === "ready" && root.bookmarks.length > 0
          width: parent.width
          height: Math.min(contentHeight, Style.space(320))
          clip: true
          model: root.bookmarks
          onAtYEndChanged: {
            if (atYEnd && contentHeight > height && !root.loading && (root.nextActiveOffset >= 0 || root.nextArchivedOffset >= 0))
              root.requestBookmarks(root.searchQuery, true, root.nextActiveOffset, root.nextArchivedOffset)
          }
          delegate: Rectangle {
            id: bookmarkRow
            required property var modelData
            required property int index
            width: bookmarkList.width
            height: Style.space(58)
            color: root.themeBackground
            radius: 0
            border.width: 0

            Rectangle {
              visible: bookmarkRow.index === root.selectedIndex
              anchors.fill: parent
              anchors.margins: Style.space(2)
              radius: Style.cornerRadius
              color: Style.selectedFillFor(root.themeSecondary, root.themeAccent)
              border.width: Math.max(1, Style.space(2))
              border.color: root.themeAccent
            }

            MouseArea {
              anchors.fill: parent
              hoverEnabled: true
              cursorShape: Qt.PointingHandCursor
              onEntered: root.selectBookmark(bookmarkRow.index)
              onClicked: root.openBookmark(bookmarkRow.index)
            }

            Column {
              anchors.fill: parent
              anchors.margins: Style.space(8)
              spacing: Style.space(2)

              Text {
                width: parent.width
                text: modelData.title
                color: bookmarkRow.index === root.selectedIndex ? root.themeAccent : root.themeSecondary
                font.family: root.bar ? root.bar.fontFamily : Style.font.family
                font.pixelSize: Style.font.body
                elide: Text.ElideRight
              }

              Text {
                width: parent.width - Style.space(36)
                text: modelData.domain + (modelData.description !== "" ? " · " + modelData.description : "")
                color: root.bar ? Qt.darker(root.bar.barForeground, 1.4) : Color.muted
                font.family: root.bar ? root.bar.fontFamily : Style.font.family
                font.pixelSize: Style.font.bodySmall
                elide: Text.ElideRight
              }
            }

            PanelActionButton {
              anchors.right: parent.right
              anchors.rightMargin: Style.space(8)
              anchors.verticalCenter: parent.verticalCenter
              iconText: "󰆏"
              foreground: root.bar ? root.bar.barForeground : Color.foreground
              fontFamily: root.bar ? root.bar.fontFamily : Style.font.family
              tooltipText: "Copy URL"
              onClicked: root.copyBookmark(bookmarkRow.index)
            }
          }
        }

        Text {
          width: parent.width
          text: "Enter to open  ·  Ctrl+C to copy  ·  Esc to close"
          color: root.bar ? Qt.darker(root.bar.barForeground, 1.5) : Color.muted
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          font.pixelSize: Style.font.bodySmall
        }
      }
    }
  }
}
