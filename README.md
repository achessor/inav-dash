# INAV Telemetry Dashboard

Start Docker Desktop, open PowerShell in this folder, and run:

```powershell
docker compose up --build -d
```

Open http://localhost:8501. Under Import logs, select raw and/or telemetry CSVs
and click Import selected files. Standard filenames with the same timestamp are
paired automatically. The database retains the original CSVs and decoded samples.
Repeated uploads of the same file contents are skipped.

Select sessions and readings in the two searchable dropdowns. Each numeric
reading has its own chart with a line for each session. Use elapsed seconds to
align session starts, or UTC to compare recorded times. Text readings appear
in the recorded-values table. When raw and telemetry provide the same reading
at the same time, the dashboard uses the raw payload decoder.

For full-precision voltage and matching current and calculated watts, select
the battery_state readings. Legacy telemetry-only uploads expose the analog
readings instead. Raw decoding follows the INAV 9.1.0 logger layout.

Run `docker compose down` to stop the dashboard. SQLite lives in the named
Docker volume and persists between restarts. The service listens on localhost.

Use All decoded readings to browse every decoded sample across selected sessions,
with optional command and measurement filters. Use Uploaded files to inspect all
original columns and rows, including MSP command IDs and hexadecimal payloads.
Both views have CSV downloads.

To update an existing installation, extract these files over the existing
dashboard folder and run the same Docker Compose command there. Keep the
existing Compose project so it continues to use the same SQLite volume.

In Charts, use Data to chart to switch between Battery, GPS, Attitude,
Altitude, RC inputs, Servo outputs, and other available groups. Choose
All numeric readings to chart every group. The optional reading filter
narrows the charts within the chosen group.
