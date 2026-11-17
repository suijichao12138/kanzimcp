# Monitor Web UI

A web-based GUI for remotely inspecting and debugging Kanzi applications via Monitor's Protocol Bridge. Connects over TCP or serial (UART) and provides real-time access to the scene graph, properties, resources, performance metrics, render passes, screen capture, and more.

## Overview

This tool consists of:
- **bridge.py** - A Python WebSocket-to-TCP/Serial bridge that connects to Monitor's RemoteConsole or SerialConsole
- **index.html** - A web UI that displays the node tree with expand/collapse and auto-refresh

## Requirements

- Python 3.7+
- websockets library: `pip install websockets`
- For serial/UART connections (optional): `pip install pyserial-asyncio-fast`

## Usage

### 1. Start the Kanzi application with Monitor

Run your Kanzi application with Monitor enabled. The Overwatch service is enabled by default (ServiceOverwatchEnabled=1 in kanzimonitor.cfg).

### 2. Start the WebSocket bridge

```bash
cd tools/monitor-web-ui
pip install websockets
python bridge.py
```

The bridge connects to Monitor at 127.0.0.1:56000 and serves the web UI at http://localhost:8765.

### 2b. (Alternative) Connect via Serial/UART

For embedded targets with `SerialConsoleEnabled=1`:

```bash
pip install websockets pyserial-asyncio-fast
python bridge.py --serial-port COM3
```

Optional: specify baud rate (default 115200):
```bash
python bridge.py --serial-port /dev/ttyUSB0 --baud-rate 921600
```

### 3. Open the web UI

Open http://localhost:8765 in your browser.

## Features

- **Node Tree**: Live scene graph with expand/collapse, auto-refresh, and node type icons
- **Property Inspector**: View and edit properties on selected nodes
- **Resource Viewer**: Browse all resources with texture type details (including cubemap face count), texture preview, per-face cubemap preview (all six faces as a thumbnail strip, click to enlarge), GPU readback, full-resolution toggle, and download (PNG/Raw)
- **Performance**: FPS/frame timing metrics, configurable performance watchers, auto-refresh, and SuspendWhenIdle status indicator with toggle
- **Screen Capture**: Screenshot with full-resolution toggle and download PNG; inspect and download framebuffer previews; all previews flipped vertically by default to match screen orientation (toggle with Flip vertical checkbox); overlay controls for PerformanceInfo level, Monitor UI visibility, BasicUI screen selection, and font scale (auto-detects available commands)
- **Render Passes**: Render pass tree with CompositionTarget preview and download (PNG/Raw)
- **DataSources**: Inspect and edit DataSource/DataObject trees
- **Trace**: Capture and view Chrome Trace profiling data with summary stats (session, Kanzi version, duration, events, size, categories), download JSON, and open in the Perfetto UI with **View in Perfetto** (new browser tab; trace parsed locally in your browser)
- **Logs**: Log entries with severity filter, live auto-refresh, and download as .txt
- **Graphics Info**: GPU and graphics details
- **Resource Purge**: Clear unused resources from the Kanzi resource manager
- **Interactive Console**: Send arbitrary commands to Monitor

## Standalone Executable

You can build a standalone `monitor-web-ui.exe` that bundles Python, websockets, and the web UI into a single file. No Python installation needed on the target machine.

### Building

```bash
cd tools/monitor-web-ui
build_exe.bat
```

This creates `dist/monitor-web-ui.exe` (~10-15 MB).

### Using

Double-click `monitor-web-ui.exe` — the browser opens automatically to the Monitor Web UI.

Command-line options work the same as `bridge.py`:

```
monitor-web-ui.exe --monitor-host 192.168.1.100   (connect to remote Monitor)
monitor-web-ui.exe --no-browser                    (don't auto-open browser)
monitor-web-ui.exe --serial-port COM3              (connect via serial/UART)
monitor-web-ui.exe --serial-port COM3 --baud-rate 921600
```

## Command Line Options

```
python bridge.py [OPTIONS]

TCP options (default):
  --monitor-host HOST    Monitor host address (default: 127.0.0.1)
  --monitor-port PORT    Monitor RemoteConsole port (default: 56000)

Serial options:
  --serial-port PORT     Serial device (e.g. COM3, /dev/ttyUSB0). Uses serial instead of TCP.
  --baud-rate RATE       Serial baud rate (default: 115200). Only used with --serial-port.

General options:
  --ws-port PORT         WebSocket server port (default: 8765)
  --command-timeout SEC  Response timeout per command (default: 30 for TCP, 120 for serial)
  --no-browser           Don't auto-open browser on startup
```

## Architecture

```
                                                          TCP (default)
┌─────────────────┐     WebSocket      ┌─────────────────┐◄───────────────►┌─────────────────┐
│   Web Browser   │◄──────────────────►│   bridge.py     │  localhost:56000│    Monitor      │
│   (index.html)  │   ws://localhost   │   (Python)      │                 │  (Kanzi Plugin) │
└─────────────────┘       :8765        └─────────────────┘◄───────────────►└─────────────────┘
                                                         Serial (--serial-port)
                                                          COM3 / /dev/ttyUSB0
```

## Protocol

The web UI sends `overwatch.*` commands via WebSocket:
```json
{"command": "overwatch.nodes"}
```

The bridge forwards to Monitor and returns:
```json
{
  "command": "overwatch.nodes",
  "response": "{\"rootCount\": 1, \"roots\": [...]}"
}
```

The `bridge.info` command is handled locally by the bridge (not forwarded to Monitor) and returns transport metadata:
```json
{"command": "bridge.info", "response": "{\"transport\":\"serial\",\"baudRate\":115200,\"commandTimeout\":120}"}
```

## Connection status

The header "Connected" indicator tracks the **bridge → Monitor** link, not just the browser → bridge WebSocket. The bridge tags every response envelope with a `monitorConnected` boolean (true iff its TCP/serial connection to Monitor is alive), and the UI updates the indicator from that field. A 5 s `overwatch.status` heartbeat surfaces Monitor disconnects without user action, and the bridge auto-reconnects on the next command once Monitor comes back.

## TCP vs Serial Behavior

The web UI queries `bridge.info` on connect and adapts its behavior based on the transport type.

| Behavior | TCP | Serial |
|----------|-----|--------|
| Status indicator | "Connected" | "Connected (serial 115200)" |
| Texture preview default | 256px | 64px |
| Screenshot default | 512px | 128px |
| Render pass preview default | 256px | 64px |
| Full resolution checkbox | Immediate | Confirmation dialog |
| Fetch Last Trace | Immediate | Confirmation dialog (warns about size) |
| Capture Trace | Auto-fetches result | Captures only; user must click "Fetch Last Trace" |
| Command timeout | 30s | 120s |

### Serial/UART bandwidth notes

At 115200 baud (~11.5 KB/s), large responses like texture previews or screenshots can be slow. The UI automatically reduces default image sizes on serial to keep transfers under ~2 seconds. Additional recommendations:

- Use a higher baud rate when the hardware supports it (`--baud-rate 921600`)
- Text-based commands (nodes, props, perf) work well even at 115200 baud
- Avoid full-resolution images over serial unless necessary — the UI will warn before proceeding
- Trace files can be several MB; the UI will not auto-fetch them on serial

## Timeout Recovery

When a command times out, the bridge recovers gracefully based on transport type:

- **TCP**: The bridge disconnects, which causes the Monitor's blocked `send()` to fail and unblock the main thread. The next command automatically reconnects.
- **Serial**: The bridge drains remaining data from the timed-out response (up to 5 seconds) before sending the next command. If draining times out, the serial port is reopened.

In both cases, the bridge returns a clean `{"error": "Timeout waiting for response"}` to the web UI instead of garbled partial data.

## Future Enhancements

- Trace timeline visualization
