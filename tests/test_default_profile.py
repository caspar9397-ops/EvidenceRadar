from __future__ import annotations

import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from tools.radar_control import compile_runtime, load_master
from tools.run_github_radar import RadarRuntimeError, execute, parse_args

ROOT = Path(__file__).resolve().parents[1]


class DefaultProfileTests(unittest.TestCase):
    def test_unspecified_profile_resolves_to_glass_radar(self) -> None:
        master = load_master(ROOT / "config" / "radar_master.json")
        control = master["control_plane"]
        self.assertEqual(control["default_profile"], "glass_ag_na_ion_exchange")
        self.assertEqual(control["production_profile"], "glass_ag_na_ion_exchange")

        runtime = compile_runtime(
            master,
            legacy_streams=yaml.safe_load(
                (ROOT / "config" / "streams.yml").read_text(encoding="utf-8")
            ),
            legacy_scoring=yaml.safe_load(
                (ROOT / "config" / "scoring.yml").read_text(encoding="utf-8")
            ),
            profile_id=None,
        )
        self.assertEqual(
            runtime.category_order,
            ["glass_ag_na_ion_exchange"],
        )
        self.assertEqual(
            runtime.limits["selection"]["final_digest"],
            {"target": 15, "hard_max": 30},
        )
        self.assertEqual(
            {"crossref", "openalex", "publisher"},
            set(runtime.streams["streams"]["glass_ag_na_ion_exchange"]["sources"]),
        )
        self.assertEqual(
            "pure AgNO3 only",
            runtime.profile_policy["screening_policy"]["molten_salt"],
        )

    def test_checked_in_runner_accepts_profile_without_a_patch_step(self) -> None:
        args = parse_args(
            [
                "--output-dir",
                "/tmp/evidenceradar-profile-output",
                "--state",
                "/tmp/evidenceradar-profile-state.json",
                "--profile",
                "glass_ag_na_ion_exchange",
            ]
        )
        self.assertEqual("glass_ag_na_ion_exchange", args.profile)

    def test_missing_master_fails_closed_before_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            for name in ("output.yml", "deployment.yml"):
                shutil.copy2(ROOT / "config" / name, root / "config" / name)

            def should_not_run(*_args, **_kwargs):
                raise AssertionError("discovery must not run without master control")

            with self.assertRaisesRegex(
                RadarRuntimeError, "authoritative master control is missing"
            ):
                execute(
                    root=root,
                    output_dir=root / "output",
                    state_path=root / "state.json",
                    end_at=datetime(
                        2026, 8, 10, 12, 0, tzinfo=ZoneInfo("Asia/Tokyo")
                    ),
                    run_id="missing-master",
                    execution_lane="github_actions",
                    discoverer=should_not_run,
                    publisher_probe=should_not_run,
                )


if __name__ == "__main__":
    unittest.main()
