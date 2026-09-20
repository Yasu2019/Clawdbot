from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import run_cae_7track_acceptance as R


def test_all_seven_tracks_are_explicit_and_nonempty():
    assert set(R.TRACKS) == {
        "openfoam_physics", "resume_and_failure", "conservative_transfer",
        "six_defects", "arbitrary_3d", "verification", "visual_qa",
    }
    assert all(tests for tests in R.TRACKS.values())


def test_missing_test_fails_closed(tmp_path: Path):
    result = R.run_track("broken", ["tests/does_not_exist.py"], tmp_path)
    assert result["status"] == "MISSING_TESTS"
    assert result["returncode"] != 0
