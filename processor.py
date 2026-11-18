"""Page detection, perspective correction, splitting, and document filters."""
import cv2
import numpy as np

FILTERS = ["Original Color", "Enhanced Document (Color)", "Clean Black & White"]

def order_points(points):
    pts = np.asarray(points, dtype=np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).reshape(-1)
    return np.array([
        pts[np.argmin(s)],       # top-left
        pts[np.argmin(d)],       # top-right
        pts[np.argmax(s)],       # bottom-right
        pts[np.argmax(d)]        # bottom-left
    ], dtype=np.float32)

def detect_book(frame):
    """Find a large bright 4-corner page/spread against a dark desk."""
    if frame is None:
        return None
    h, w = frame.shape[:2]
    scale = min(1.0, 1100.0 / max(h, w))
    small = cv2.resize(frame, (int(w*scale), int(h*scale))) if scale < 1 else frame.copy()
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    # Local contrast helps with uneven illumination; threshold assumes desk is darker.
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, mask = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Try both polarities and keep the largest plausible quadrilateral.
    candidates = []
    for binary in (mask, cv2.bitwise_not(mask)):
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE,
                                  cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9)))
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < small.shape[0] * small.shape[1] * 0.08:
                continue
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            if len(approx) == 4 and cv2.isContourConvex(approx):
                candidates.append((area, approx.reshape(4, 2).astype(np.float32) / scale))
    if not candidates:
        return None
    return order_points(max(candidates, key=lambda item: item[0])[1])

def warp_spread(frame, corners):
    """Warp selected corners to a rectangle, preserving the source resolution."""
    pts = order_points(corners)
    tl, tr, br, bl = pts
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    out_w = max(2, int(max(width_a, width_b)))
    out_h = max(2, int(max(height_a, height_b)))
    target = np.array([[0, 0], [out_w-1, 0],
                       [out_w-1, out_h-1], [0, out_h-1]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(pts, target)
    return cv2.warpPerspective(frame, matrix, (out_w, out_h),
                               flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

def split_spread(spread, offset=0):
    h, w = spread.shape[:2]
    split_x = max(1, min(w-1, w // 2 + int(offset)))
    return spread[:, :split_x].copy(), spread[:, split_x:].copy()

def enhance(image, mode):
    if mode == 0:
        return image.copy()
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    color = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
    if mode == 1:
        # Gentle white balance / paper brightening without removing colored ink.
        return cv2.convertScaleAbs(color, alpha=1.08, beta=8)
    gray = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY, 35, 13)

def process_capture(frame, corners=None, split=True, offset=0, mode=1):
    if corners is None:
        corners = detect_book(frame)
    if corners is None:
        # Fallback: use the whole image rather than silently failing.
        spread = frame.copy()
    else:
        spread = warp_spread(frame, corners)
    if split:
        pages = split_spread(spread, offset)
    else:
        pages = (spread,)
    return [enhance(page, mode) for page in pages], corners
