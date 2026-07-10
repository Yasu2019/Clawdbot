from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np


class ONNXImageAdapter:
    """一般的なNCHW画像モデル用の最小ONNX Runtimeアダプター。

    モデル固有の正規化・出力解釈はdeployment_metadataで明示してください。
    """

    def __init__(self, model_path: str | Path, providers: list[str] | None = None):
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise RuntimeError("onnxruntime または onnxruntime-gpu を導入してください") from exc
        available = ort.get_available_providers()
        requested = providers or ["CUDAExecutionProvider", "CPUExecutionProvider"]
        selected = [p for p in requested if p in available]
        if not selected:
            selected = ["CPUExecutionProvider"]
        self.session = ort.InferenceSession(str(model_path), providers=selected)
        self.input = self.session.get_inputs()[0]
        self.output_names = [o.name for o in self.session.get_outputs()]

    def preprocess(self, image: np.ndarray, size_hw: tuple[int, int]) -> np.ndarray:
        h, w = size_hw
        x = cv2.resize(image, (w, h), interpolation=cv2.INTER_AREA)
        x = cv2.cvtColor(x, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        x = np.transpose(x, (2, 0, 1))[None, ...]
        return x

    def run_raw(self, image: np.ndarray, size_hw: tuple[int, int]) -> list[np.ndarray]:
        x = self.preprocess(image, size_hw)
        return self.session.run(self.output_names, {self.input.name: x})
