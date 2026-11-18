# DIY A3 Overhead Book Scanner

A Python desktop prototype for capturing overhead book/register spreads, correcting perspective, splitting pages, enhancing documents, and exporting a multi-page PDF.

## 1. Project folder

```text
a3_book_scanner/
├── main.py
├── camera.py
├── processor.py
├── pdf_exporter.py
├── requirements.txt
├── README.md
├── mock_images/
│   ├── test_spread_01.jpg
│   └── test_spread_02.jpg
└── scans/
```

## 2. Requirements

- Python 3.9 or newer
- Windows, Linux, or macOS desktop with Tkinter available
- UVC USB webcam for live capture (4K recommended)
- Dark matte background and even lighting

Install dependencies:

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

On some Linux distributions, Tkinter must be installed using the OS package manager (for example, `python3-tk`).

## 3. Run the application

Live camera (camera index 0):

```bash
python main.py --camera 0
```

Or run without a camera using the included mock images:

```bash
python main.py --mock mock_images
```

You can also launch `python main.py` and select **Scan Cameras**, **Connect Camera**, or **Open Mock Folder** in the UI.

## 4. Controls

| Control | Action |
|---|---|
| Space | Capture, process, and save |
| Z | Undo the last saved page image |
| S | Toggle dual-page split / single spread |
| M | Cycle Original Color → Enhanced Color → Clean B&W |
| P | Export all saved page images to one PDF |
| Set 4 Corners | Click four points in preview in TL, TR, BR, BL order |
| Auto Detect | Run automatic page quadrilateral detection |
| Autofocus | Toggle camera autofocus |
| Focus / Exposure | Adjust UVC camera controls where supported |

The app creates a timestamped folder under `scans/`, for example `scans/session_20261115_2130/`.

## 5. Modules

- `camera.py`: camera discovery, MJPG/4K request, UVC controls, mock-folder source.
- `processor.py`: quadrilateral detection, perspective warp, center split, enhancement.
- `pdf_exporter.py`: multi-page PDF export.
- `main.py`: Tkinter interface, preview, workflow, shortcuts, session management.

## 6. Important hardware notes

- The application requests MJPG and 3840×2160 from the camera. Some webcams/drivers may reject 4K or MJPG. The status line displays the resolution reported by the driver; verify it is 3840×2160 for true 4K capture.
- Focus, exposure, and autofocus controls are hardware/driver-dependent. A successful `set()` call is not guaranteed by every UVC camera.
- The preview is scaled for speed. Captures are processed from the full frame returned by the camera.
- For stable scans, mount the camera perpendicular to the desk, avoid glare, use diffuse lighting, and keep the desk significantly darker than the paper.
- Automatic contour detection is a best-effort prototype. If the register edge is worn, shadowed, or not clearly brighter than the desk, use **Set 4 Corners**.
- The prototype treats the open spread as one flat quadrilateral. It does not perform true page dewarping for curved pages near the spine. For production-quality book flattening, add a curved-surface/dewarping model or structured-light/depth guidance.
- The app saves JPEG at quality 98. For archival capture, consider saving PNG/TIFF (larger files) and generating a compressed PDF separately.
- For a very wide A3 spread, the camera's aspect ratio and mounting distance determine whether the entire register fits in the frame.

## 7. Sample output

The `sample_output/` folder contains synthetic test pages and a sample multi-page PDF generated from the mock spread. Use these to verify the workflow without a camera.
