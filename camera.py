"""Camera discovery, 4K UVC capture, and mock-folder input."""
from pathlib import Path
import cv2

WIDTH, HEIGHT = 3840, 2160

def list_cameras(max_index=8):
    """Return camera indices that can be opened. May take a few seconds."""
    found = []
    for index in range(max_index):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW) if hasattr(cv2, "CAP_DSHOW") else cv2.VideoCapture(index)
        if cap.isOpened():
            ok, _ = cap.read()
            if ok:
                found.append(index)
        cap.release()
    return found

class Camera:
    def __init__(self, index=0, width=WIDTH, height=HEIGHT):
        self.index = index
        self.width, self.height = width, height
        self.cap = None

    def open(self):
        # CAP_DSHOW is generally more reliable on Windows; fall back if needed.
        backend = cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else cv2.CAP_ANY
        self.cap = cv2.VideoCapture(self.index, backend)
        if not self.cap.isOpened():
            self.cap.release()
            self.cap = cv2.VideoCapture(self.index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera index {self.index}.")
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        # Drivers may refuse requested settings. Report actual size in status.
        return int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def read(self):
        if self.cap is None or not self.cap.isOpened():
            raise RuntimeError("Camera is not open.")
        ok, frame = self.cap.read()
        if not ok or frame is None:
            raise RuntimeError("Camera frame could not be read.")
        return frame

    def set_control(self, prop, value):
        if self.cap is None or not self.cap.isOpened():
            return False
        return bool(self.cap.set(prop, float(value)))

    def close(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

class MockSource:
    """Cycles through image files in a folder; useful without a webcam."""
    EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

    def __init__(self, folder):
        self.folder = Path(folder)
        self.paths = sorted(p for p in self.folder.iterdir()
                            if p.suffix.lower() in self.EXTENSIONS)
        if not self.paths:
            raise RuntimeError(f"No image files found in {self.folder}")
        self.position = 0

    def read(self):
        path = self.paths[self.position]
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError(f"Could not read mock image: {path}")
        self.position = (self.position + 1) % len(self.paths)
        return image

    def close(self):
        pass
