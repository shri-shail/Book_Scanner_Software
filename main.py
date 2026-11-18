"""DIY A3 overhead book scanner - desktop prototype."""
import argparse
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
from PIL import Image, ImageTk

from camera import Camera, MockSource, list_cameras
from processor import FILTERS, detect_book, process_capture
from pdf_exporter import export_pdf

PREVIEW_W, PREVIEW_H = 1100, 650

class ScannerApp:
    def __init__(self, root, args):
        self.root = root
        self.root.title("DIY A3 Overhead Book Scanner")
        self.root.geometry("1250x850")
        self.source = None
        self.source_kind = None
        self.current_frame = None
        self.current_corners = None
        self.manual_points = []
        self.pages = []
        self.split_mode = True
        self.filter_mode = 1
        self.offset = tk.IntVar(value=0)
        self.autofocus = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Choose a camera or mock image folder.")
        self.session_dir = Path("scans") / datetime.now().strftime("session_%Y%m%d_%H%M")
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._build_ui()
        if args.mock:
            self.start_mock(args.mock)
        elif args.camera is not None:
            self.start_camera(args.camera)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.update_preview()

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill="x")
        ttk.Button(top, text="Scan Cameras", command=self.scan_cameras).pack(side="left", padx=3)
        self.camera_var = tk.StringVar(value="0")
        self.camera_combo = ttk.Combobox(top, textvariable=self.camera_var, width=5, state="readonly")
        self.camera_combo.pack(side="left", padx=3)
        ttk.Button(top, text="Connect Camera", command=self.connect_selected).pack(side="left", padx=3)
        ttk.Button(top, text="Open Mock Folder", command=self.choose_mock).pack(side="left", padx=3)
        ttk.Button(top, text="Set 4 Corners", command=self.begin_manual).pack(side="left", padx=3)
        ttk.Button(top, text="Auto Detect", command=self.auto_detect).pack(side="left", padx=3)

        controls = ttk.LabelFrame(self.root, text="Capture controls", padding=8)
        controls.pack(fill="x", padx=8, pady=4)
        ttk.Checkbutton(controls, text="Autofocus", variable=self.autofocus,
                        command=self.apply_autofocus).pack(side="left", padx=5)
        ttk.Label(controls, text="Focus").pack(side="left")
        self.focus_var = tk.DoubleVar(value=30)
        ttk.Scale(controls, from_=0, to=255, variable=self.focus_var,
                  command=lambda v: self.set_camera_control(cv2.CAP_PROP_FOCUS, v)).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Label(controls, text="Exposure").pack(side="left")
        self.exposure_var = tk.DoubleVar(value=-6)
        ttk.Scale(controls, from_=-13, to=0, variable=self.exposure_var,
                  command=lambda v: self.set_camera_control(cv2.CAP_PROP_EXPOSURE, v)).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Checkbutton(controls, text="Split dual pages (S)", command=self.toggle_split,
                        variable=tk.BooleanVar(value=True)).pack(side="left", padx=8)

        options = ttk.Frame(self.root, padding=8)
        options.pack(fill="x")
        ttk.Label(options, text="Center offset").pack(side="left")
        ttk.Scale(options, from_=-300, to=300, variable=self.offset, orient="horizontal",
                  length=220).pack(side="left", padx=6)
        ttk.Label(options, text="Filter:").pack(side="left", padx=(20, 4))
        self.filter_label = ttk.Label(options, text=FILTERS[self.filter_mode])
        self.filter_label.pack(side="left")
        ttk.Button(options, text="Cycle Filter (M)", command=self.cycle_filter).pack(side="left", padx=8)
        ttk.Button(options, text="Capture (Space)", command=self.capture).pack(side="left", padx=8)
        ttk.Button(options, text="Undo (Z)", command=self.undo).pack(side="left", padx=8)
        ttk.Button(options, text="Export PDF (P)", command=self.export).pack(side="left", padx=8)

        self.preview = ttk.Label(self.root)
        self.preview.pack(padx=8, pady=5)
        ttk.Label(self.root, textvariable=self.status, relief="sunken", anchor="w").pack(fill="x", side="bottom")
        self.root.bind("<space>", lambda e: self.capture())
        self.root.bind("z", lambda e: self.undo())
        self.root.bind("Z", lambda e: self.undo())
        self.root.bind("s", lambda e: self.toggle_split())
        self.root.bind("S", lambda e: self.toggle_split())
        self.root.bind("m", lambda e: self.cycle_filter())
        self.root.bind("M", lambda e: self.cycle_filter())
        self.root.bind("p", lambda e: self.export())
        self.root.bind("P", lambda e: self.export())
        self.preview.bind("<Button-1>", self.add_manual_point)

    def scan_cameras(self):
        found = list_cameras()
        self.camera_combo["values"] = found
        if found:
            self.camera_var.set(str(found[0]))
            self.status.set(f"Available camera indices: {found}")
        else:
            self.status.set("No camera found. Use Open Mock Folder to test.")

    def connect_selected(self):
        try:
            self.start_camera(int(self.camera_var.get()))
        except Exception as exc:
            messagebox.showerror("Camera error", str(exc))

    def start_camera(self, index):
        self.stop_source()
        cam = Camera(index)
        actual = cam.open()
        self.source, self.source_kind = cam, "camera"
        self.status.set(f"Camera {index} connected. Driver-reported resolution: {actual[0]} x {actual[1]} (requested 3840 x 2160).")

    def choose_mock(self):
        folder = filedialog.askdirectory(title="Choose folder containing test images")
        if folder:
            self.start_mock(folder)

    def start_mock(self, folder):
        try:
            self.stop_source()
            self.source = MockSource(folder)
            self.source_kind = "mock"
            self.status.set(f"Mock mode: {folder}")
        except Exception as exc:
            messagebox.showerror("Mock mode error", str(exc))

    def stop_source(self):
        if self.source:
            self.source.close()
        self.source = None
        self.source_kind = None

    def set_camera_control(self, prop, value):
        if self.source_kind == "camera":
            self.source.set_control(prop, value)

    def apply_autofocus(self):
        self.set_camera_control(cv2.CAP_PROP_AUTOFOCUS, 1 if self.autofocus.get() else 0)

    def toggle_split(self, event=None):
        self.split_mode = not self.split_mode
        self.status.set("Dual-page split ON" if self.split_mode else "Single-page mode")

    def cycle_filter(self):
        self.filter_mode = (self.filter_mode + 1) % len(FILTERS)
        self.filter_label.config(text=FILTERS[self.filter_mode])

    def auto_detect(self):
        if self.current_frame is None:
            return
        self.current_corners = detect_book(self.current_frame)
        self.manual_points = []
        self.status.set("Book edges detected." if self.current_corners is not None else "No quadrilateral found; click Set 4 Corners.")

    def begin_manual(self):
        self.manual_points = []
        self.current_corners = None
        self.status.set("Click 4 page corners in preview: top-left, top-right, bottom-right, bottom-left.")

    def add_manual_point(self, event):
        if len(self.manual_points) >= 4 or self.current_frame is None:
            return
        h, w = self.current_frame.shape[:2]
        scale = min(PREVIEW_W / w, PREVIEW_H / h)
        shown_w, shown_h = int(w * scale), int(h * scale)
        x0 = (PREVIEW_W - shown_w) // 2
        y0 = (PREVIEW_H - shown_h) // 2
        x = (event.x - x0) / scale
        y = (event.y - y0) / scale
        if 0 <= x < w and 0 <= y < h:
            self.manual_points.append([x, y])
        if len(self.manual_points) == 4:
            self.current_corners = self.manual_points[:]
            self.status.set("Manual corners set. Press Space to capture.")

    def update_preview(self):
        if self.source is not None:
            try:
                self.current_frame = self.source.read()
                if self.current_corners is None and not self.manual_points:
                    self.current_corners = detect_book(self.current_frame)
            except Exception as exc:
                self.status.set(str(exc))
        if self.current_frame is not None:
            frame = self.current_frame.copy()
            corners = self.current_corners
            if corners is not None:
                pts = corners.astype("int32").reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], True, (0, 255, 0), 5)
            for point in self.manual_points:
                cv2.circle(frame, tuple(map(int, point)), 12, (0, 0, 255), -1)
            h, w = frame.shape[:2]
            scale = min(PREVIEW_W / w, PREVIEW_H / h)
            preview = cv2.resize(frame, (int(w*scale), int(h*scale)))
            canvas = Image.new("RGB", (PREVIEW_W, PREVIEW_H), (35, 35, 35))
            pic = Image.fromarray(cv2.cvtColor(preview, cv2.COLOR_BGR2RGB))
            canvas.paste(pic, ((PREVIEW_W-pic.width)//2, (PREVIEW_H-pic.height)//2))
            self.photo = ImageTk.PhotoImage(canvas)
            self.preview.configure(image=self.photo)
        self.root.after(30, self.update_preview)

    def capture(self):
        if self.current_frame is None:
            self.status.set("No frame available.")
            return
        try:
            pages, corners = process_capture(self.current_frame, self.current_corners,
                                              self.split_mode, self.offset.get(), self.filter_mode)
            self.current_corners = corners
            number = len(self.pages) // (2 if self.split_mode else 1) + 1
            saved = []
            for idx, page in enumerate(pages):
                side = ("_L" if idx == 0 else "_R") if self.split_mode else ""
                path = self.session_dir / f"Page_{number:03d}{side}.jpg"
                # JPEG quality 98 preserves fine print better than default quality.
                cv2.imwrite(str(path), page, [cv2.IMWRITE_JPEG_QUALITY, 98])
                saved.append(path)
            self.pages.extend(saved)
            self.status.set(f"Saved {len(saved)} page(s). Total saved: {len(self.pages)}. Folder: {self.session_dir}")
        except Exception as exc:
            messagebox.showerror("Capture failed", str(exc))

    def undo(self):
        if not self.pages:
            self.status.set("Nothing to undo.")
            return
        path = self.pages.pop()
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        self.status.set(f"Removed {path.name}. {len(self.pages)} page(s) remain.")

    def export(self):
        if not self.pages:
            self.status.set("Capture pages before exporting.")
            return
        try:
            output = self.session_dir / "scanned_register.pdf"
            export_pdf(self.pages, output)
            self.status.set(f"PDF exported: {output}")
            messagebox.showinfo("PDF complete", f"Saved PDF:\n{output}")
        except Exception as exc:
            messagebox.showerror("PDF export failed", str(exc))

    def close(self):
        self.stop_source()
        self.root.destroy()

def main():
    parser = argparse.ArgumentParser(description="DIY A3 overhead book scanner")
    parser.add_argument("--camera", type=int, help="Camera index, e.g. --camera 0")
    parser.add_argument("--mock", type=str, help="Folder of images for offline testing")
    args = parser.parse_args()
    root = tk.Tk()
    ScannerApp(root, args)
    root.mainloop()

if __name__ == "__main__":
    main()
