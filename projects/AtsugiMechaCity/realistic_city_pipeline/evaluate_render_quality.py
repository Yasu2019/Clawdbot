import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = ROOT / "services" / "ai_image_gen" / "outputs" / "hon_atsugi_station_front_render_report.json"
DEFAULT_OUTPUT = ROOT / "services" / "ai_image_gen" / "outputs" / "hon_atsugi_station_front_quality_report.json"


MINIMUM_SCORES = {
    "city_density": 3,
    "material_realism": 3,
    "lighting": 3,
    "camera": 3,
    "character_integration": 3,
}


def score_city_density(features):
    windows = int(features.get("windows", 0))
    signs = int(features.get("sign_panels", 0))
    crosswalks = int(features.get("crosswalk_stripes", 0))
    street_furniture = int(features.get("bollards", 0)) + int(features.get("lamps", 0))

    if windows >= 600 and signs >= 20 and street_furniture >= 40:
        return 4
    if windows >= 100 and signs >= 5 and crosswalks >= 12:
        return 3
    if windows >= 20 and crosswalks >= 4:
        return 2
    if windows > 0 or crosswalks > 0:
        return 1
    return 0


def evaluate(report):
    features = report.get("procedural_features", {})
    outputs = report.get("outputs", {})
    note = report.get("note", "")

    scores = {
        "city_density": score_city_density(features),
        "material_realism": 1,
        "lighting": 2,
        "camera": 2,
        "character_integration": 2,
    }

    findings = []
    if scores["city_density"] >= 3:
        findings.append("City density passes the first practical gate: windows, signs, crosswalks, and street furniture are present.")
    else:
        findings.append("City density is still below release level; add more facade, road, and rooftop details.")

    findings.append("Material realism is intentionally scored low until PBR variation, dirt decals, glass reflection, and facade color variation are added.")
    findings.append("Lighting is basic Blender sky/sun/fill lighting; UE5 Lumen or stronger atmospheric control is still future work.")
    findings.append("Camera is composed for station-front review, but not yet a cinematic 35/50/85mm shot sequence.")
    findings.append("Character integration has visible placement, but contact shadow/AO should be strengthened for final release.")

    pass_release = all(scores[key] >= MINIMUM_SCORES[key] for key in MINIMUM_SCORES)
    return {
        "target": "generic_realistic_3d_city_render",
        "source_report": str(DEFAULT_INPUT),
        "outputs_checked": outputs,
        "source_note": note,
        "scores": scores,
        "minimum_scores": MINIMUM_SCORES,
        "pass_release_gate": pass_release,
        "next_actions": [
            "Add facade material randomization and dirt decals.",
            "Increase sign/panel contrast and add road surface wear.",
            "Add stronger contact shadow or ambient occlusion below DOM feet.",
            "Render a lower, more photographic station-front camera angle.",
            "Use local OpenVINO for texture/decal generation rather than replacing the whole scene."
        ],
        "findings": findings,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate AtsugiMechaCity render quality from a render report JSON.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Render report JSON path.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Quality report JSON path.")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    report = json.loads(input_path.read_text(encoding="utf-8"))
    result = evaluate(report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

