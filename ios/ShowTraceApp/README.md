# Show Trace iOS

SwiftUI client for the Show Trace Tool API.

## Scope

- View recommended / maybe / filtered events.
- View historical digests.
- Edit subscription artists, local city, local keywords, and enabled sources.
- Send natural-language preference feedback.
- Store API base URL and token locally on device.
- View recent worker runs and manually trigger a non-notifying run.

The app does not collect source data, send real-time push notifications, handle login, or perform ticket purchases.

## Open

Open `ShowTraceApp.xcodeproj` in Xcode, select a personal development team, then run on an iPhone.

The app defaults to the production API server:

```text
http://8.153.84.10
```

Paste the cloud API token into Settings before testing the connection.

For local API testing from a physical iPhone, use the Mac's LAN address, for example:

```text
http://192.168.1.10:8000
```

`http://127.0.0.1:8000` only works in the iOS simulator.

## Device Notes

If Xcode shows a device tunnel / reconnect error while Finder can still see the
iPhone, temporarily disable VPN or system proxy tools, then reconnect the phone.
The Xcode device debugging tunnel is sensitive to network filters even when the
USB cable and trust relationship are fine.
