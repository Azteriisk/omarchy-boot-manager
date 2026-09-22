import QtQuick
import Quickshell
import Quickshell.Io

Item {
  id: root

  property var shell: null
  property bool secureBootEnabled: false
  property bool windowsDetected: false
  property string windowsGuid: ""
  property string boardModel: ""

  readonly property string bootCli: Quickshell.env("HOME") + "/.config/omarchy/plugins/azterisk.boot/scripts/omarchy-boot"

  function refresh() {
    if (!statusProc.running) {
      statusProc.running = true;
    }
  }

  function rebootWindows() {
    rebootWinProc.running = true;
  }

  function rebootBios() {
    rebootBiosProc.running = true;
  }

  function openGui() {
    guiProc.running = true;
  }

  Component.onCompleted: {
    refresh();
  }

  Process {
    id: statusProc
    command: [root.bootCli, "json"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        try {
          var data = JSON.parse(text.trim());
          if (data.secure_boot) {
            root.secureBootEnabled = data.secure_boot.enabled || false;
          }
          if (data.windows_partitions && data.windows_partitions.length > 0) {
            root.windowsDetected = true;
            root.windowsGuid = data.windows_partitions[0].partuuid || "";
          } else {
            root.windowsDetected = false;
            root.windowsGuid = "";
          }
          if (data.hardware) {
            root.boardModel = (data.hardware.vendor || "") + " " + (data.hardware.model || "");
          }
        } catch (e) {
          // JSON parse fallback
        }
      }
    }
  }

  Process {
    id: rebootWinProc
    command: [root.bootCli, "reboot", "windows"]
  }

  Process {
    id: rebootBiosProc
    command: [root.bootCli, "reboot", "bios"]
  }

  Process {
    id: guiProc
    command: [root.bootCli, "gui"]
  }
}
