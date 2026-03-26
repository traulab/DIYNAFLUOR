# DIYNAFLUOR GUI

The DIYNAFLUOR GUI is a Python desktop application for controlling the DIYNAFLUOR fluorometer, visualising fluorescence measurements, and calculating DNA concentrations.

## Features

- **Quantification kit modes** — 2-point calibration workflow for High Sensitivity and Broad Range kits, with automatic sample concentration calculation (ng/μL)
- **Fluorometer mode** — direct fluorescence readout at adjustable LED power for custom assays
- **Live plot** — fluorescence vs. concentration chart updates after each measurement
- **Measurement history table** — scrollable log of all standards and samples taken in the current session, colour-coded green (standards) and blue (samples)
- **Calibration progress indicator** — shows current calibration step (e.g. "Step 1 / 2") and confirms when calibration is complete
- **Prominent result display** — last measured concentration shown in large text for easy bench reading
- **Connection status indicator** — coloured dot next to the COM port selector:
  - Orange: DEMO mode (no device connected)
  - Grey: port selected, not yet tested
  - Green: last measurement succeeded
  - Red: last measurement failed
- **COM port refresh** — rescan available ports at any time without restarting the application
- **CSV export** — save all measurements from the current session to a CSV file

## File overview

| File | Description |
|------|-------------|
| `main.py` | Main application — GUI layout, measurement workflow, plotting |
| `fluorometer.py` | Serial communication with the Arduino; includes a DEMO mode for testing without hardware |
| `requirements.txt` | Python package dependencies |
| `diynafluor.spec` | PyInstaller build spec for producing a standalone executable |
| `icon.png` | Application window icon |
| `logo.png` | DIYNAFLUOR logo displayed in the application header |

## Running from source

### Prerequisites

Python 3.9 or later is recommended. Install dependencies with:

```bash
pip install -r requirements.txt
```

### Launch

```bash
python main.py
```

The application opens in **DEMO mode** by default (no hardware required). Select a real COM port from the dropdown once the DIYNAFLUOR is connected via USB.

## Usage workflow

### Quantification kit mode (High Sensitivity or Broad Range)

1. Select a kit mode using the radio buttons on the left.
2. Enter the **Sample Input** volume (μL) — the volume of sample added to the assay tube.
3. Follow the on-screen instruction to insert each standard in turn and click **Measure**.
4. Once both standards are measured (calibration complete), insert each sample and click **Measure**.
5. The calculated sample concentration appears in the result display and is logged in the history table.
6. Click **Save** to export results to a CSV file.

### Fluorometer mode

1. Select **Fluorometer** mode.
2. Adjust **LED Power (%)** as required.
3. Optionally enter a **Known Concentration** if building a manual calibration curve.
4. Click **Measure** for each sample. Raw fluorescence values are logged in the history table.
5. Click **Save** to export.

### Restarting a session

Click **Restart** to discard the current measurements and begin a new session. If there are unsaved measurements, you will be prompted to save them first.

## Building a standalone executable

The application is packaged with [PyInstaller](https://pyinstaller.org). Install PyInstaller, then run:

```bash
pyinstaller diynafluor.spec
```

On **Windows**, this produces a single `diynafluor.exe` in `dist/` with a splash screen.
On **macOS**, this produces a `diynafluor.app` bundle in `dist/`.

## DEMO mode

Selecting `DEMO` as the COM port runs the application without any hardware. The first two measurements return fixed calibration values (0 and 25 000 arb. units) to simulate a completed calibration; subsequent measurements return random values. This is useful for testing the interface and export workflow.

## Dependencies

| Package | Purpose |
|---------|---------|
| `matplotlib` | Live fluorescence plot |
| `numpy` | Linear calibration curve fitting |
| `Pillow` | Logo and icon image loading |
| `pyserial` | Serial communication with the Arduino |
