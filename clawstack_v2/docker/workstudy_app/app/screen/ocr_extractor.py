"""
OCRExtractor — Extracts visible text from screen recording frames via Tesseract.

Phase 1 of the procedure generation pipeline:
  video frame → grayscale + upscale → Tesseract (jpn+eng) → text string

Usage:
    extractor = OCRExtractor()
    text = extractor.extract_near_click(frame, x=540, y=320, radius=200)
    full = extractor.extract_full_frame(frame)
"""
import cv2
import numpy as np

try:
    import pytesseract
    _HAVE_TESSERACT = True
except ImportError:
    _HAVE_TESSERACT = False


class OCRExtractor:
    """
    Runs Tesseract OCR on screen recording frames.
    Falls back silently (returns "") if Tesseract is not installed.
    """

    # psm 6 = assume uniform block of text; works well for screen UI areas
    _CFG_BLOCK  = "--psm 6 -l jpn+eng"
    # psm 11 = sparse text, no specific order — good for full-frame mixed layouts
    _CFG_SPARSE = "--psm 11 -l jpn+eng"
    _SCALE      = 2       # upscale factor; 2× gives Tesseract sharper glyphs

    # ── Public API ───────────────────────────────────────────────────────────

    def extract_near_click(
        self,
        frame: np.ndarray,
        x: int,
        y: int,
        radius: int = 220,
    ) -> str:
        """
        Extract text from the rectangular region centred on (x, y).

        Args:
            frame:  BGR frame from OpenCV.
            x, y:   Click coordinates.
            radius: Half-size of the extraction window (pixels).

        Returns:
            Stripped UTF-8 text string; "" on failure.
        """
        if not _HAVE_TESSERACT or frame is None:
            return ""

        h, w = frame.shape[:2]
        x1, y1 = max(0, x - radius), max(0, y - radius)
        x2, y2 = min(w, x + radius), min(h, y + radius)
        roi = frame[y1:y2, x1:x2]
        return self._run_ocr(roi, config=self._CFG_BLOCK)

    def extract_full_frame(self, frame: np.ndarray) -> str:
        """
        Extract all text visible in a full frame (slower than extract_near_click).

        Returns:
            Stripped UTF-8 text; "" on failure.
        """
        if not _HAVE_TESSERACT or frame is None:
            return ""
        return self._run_ocr(frame, config=self._CFG_SPARSE)

    def extract_title_bar(self, frame: np.ndarray, bar_height: int = 40) -> str:
        """
        Extract text from the top title-bar strip of the frame.
        Useful for identifying the active application/window name.
        """
        if not _HAVE_TESSERACT or frame is None:
            return ""
        strip = frame[:bar_height, :]
        return self._run_ocr(strip, config=self._CFG_BLOCK)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _run_ocr(self, img: np.ndarray, config: str) -> str:
        """Upscale, binarise, and run Tesseract on an image region."""
        if img is None or img.size == 0:
            return ""
        try:
            scaled = cv2.resize(
                img, None,
                fx=self._SCALE, fy=self._SCALE,
                interpolation=cv2.INTER_CUBIC,
            )
            gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
            # Otsu binarisation — high contrast for screen text
            _, binary = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            text = pytesseract.image_to_string(binary, config=config)
            return text.strip()
        except Exception:
            return ""

    @staticmethod
    def is_available() -> bool:
        """Return True if Tesseract is installed and callable."""
        if not _HAVE_TESSERACT:
            return False
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False
