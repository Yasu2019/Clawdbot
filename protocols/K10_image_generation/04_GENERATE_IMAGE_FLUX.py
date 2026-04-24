from __future__ import annotations

import argparse
from pathlib import Path
from datetime import datetime

import huggingface_hub as hf_hub
from PIL import Image
import openvino as ov
import openvino_genai as ov_genai


DEFAULT_MODEL_ID = "OpenVINO/FLUX.1-schnell-fp16-ov"


def choose_device(requested: str) -> str:
    if requested.upper() != "AUTO":
        return requested.upper()

    core = ov.Core()
    devices = set(core.available_devices)
    if "GPU" in devices:
        return "GPU"
    return "CPU"


def ensure_model(model_id: str, cache_dir: Path) -> Path:
    target = cache_dir / model_id.split("/")[-1]
    if target.exists():
        return target

    target.mkdir(parents=True, exist_ok=True)
    hf_hub.snapshot_download(repo_id=model_id, local_dir=str(target))
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an image with OpenVINO FLUX.1-schnell")
    parser.add_argument("--prompt", required=True, help="Text prompt")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID, help="Hugging Face model ID")
    parser.add_argument("--cache-dir", default="models", help="Local model cache directory")
    parser.add_argument("--device", default="AUTO", help="AUTO, CPU, or GPU")
    parser.add_argument("--steps", type=int, default=4, help="Inference steps")
    parser.add_argument("--guidance-scale", type=float, default=0.0, help="Guidance scale")
    parser.add_argument("--seed", type=int, default=42, help="Seed")
    parser.add_argument("--out-dir", default="outputs", help="Output directory")
    parser.add_argument("--file-name", default="", help="Optional output file name")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    cache_dir = Path(args.cache_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model_path = ensure_model(args.model_id, cache_dir)
    device = choose_device(args.device)

    print(f"Using model path: {model_path}")
    print(f"Using device: {device}")
    print(f"Prompt: {args.prompt}")

    pipe = ov_genai.Text2ImagePipeline(str(model_path), device)

    image_tensor = pipe.generate(
        args.prompt,
        guidance_scale=args.guidance_scale,
        num_inference_steps=args.steps,
        rng_seed=args.seed,
    )

    image = Image.fromarray(image_tensor.data[0])

    if args.file_name:
        out_path = out_dir / args.file_name
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"flux_{stamp}.png"

    image.save(out_path)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
