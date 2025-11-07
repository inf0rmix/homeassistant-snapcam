<div align="center">
  <img src="branding/logo.svg" alt="SnapCam Logo" width="360"/>
  <h1>SnapCam – Virtual Snapshot Camera for Home Assistant</h1>
  <p>Virtual cameras that keep the latest snapshot from one or more source cameras – stored in RAM only.</p>
</div>

## Features
- Virtual camera entity (images in RAM, no disk writes)
- Multiple camera+trigger pairs (binary_sensor -> on)
- Global delay (0–30 min) per virtual camera
- Optional `_last` camera for the previous image
- Initial snapshot at startup
- Binary sensor “Triggered” (5s pulse) & sensor “Last Source”
- Service `snapcam.request_snapshot` (optional `source_camera`)

## Install
- Copy `custom_components/snapcam` → HA config folder
- Or use HACS (Custom repo) and restart HA
