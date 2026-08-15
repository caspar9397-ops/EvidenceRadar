from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from tools.featured_selection import select_featured_work_ids_v2
from tools.run_github_radar import (
    Candidate,
    DiscoveryResult,
    RadarRuntimeError,
    assess_candidate,
    event_record,
    execute,
    score_candidate,
    validate_glass_screening,
)


def included_screening() -> dict:
    return {
        "decision": "INCLUDE",
        "decision_reason": "No field, pure AgNO3, and explicit oxide composition.",
        "exclusion_reasons": [],
        "external_electric_field": "ABSENT",
        "molten_salt": "PURE_AGNO3",
        "oxide_composition_explicit": "YES",
        "reference_comparison": "EXACT_75_25_BINARY",
        "comparison_note": "Same binary 75 mol% SiO2 / 25 mol% Na2O reference.",
        "glass_compositions": [
            {
                "basis": "mol%",
                "components": [
                    {"oxide": "SiO2", "value": 75.0},
                    {"oxide": "Na2O", "value": 25.0},
                ],
                "source_locator": "p. 4, Table 1",
            }
        ],
        "exchange_conditions": [
            {
                "temperature_c": 350.0,
                "duration": "2 h",
                "salt_condition": "pure AgNO3 (100%)",
                "source_locator": "p. 5, Experimental",
            }
        ],
        "reported_outputs": [
            "CONCENTRATION_DEPTH_PROFILE",
            "DIFFUSION_COEFFICIENT",
            "MULTIPLE_EXCHANGE_TIMES",
        ],
        "main_values": [
            {
                "metric": "D",
                "value_text": "1.2e-11 cm2/s",
                "source_locator": "p. 8, Table 2",
            }
        ],
    }


class GlassProfileTests(unittest.TestCase):
    def candidate(self, screening: dict | None) -> Candidate:
        return Candidate(
            title="Silver sodium ion exchange in sodium silicate glass",
            stream="glass_ag_na_ion_exchange",
            category="glass_ag_na_ion_exchange",
            source="fixture",
            publication_date="2026-08-08",
            doi="10.1000/glass",
            glass_screening=screening,
        )

    def test_exact_reference_include_is_valid_and_prioritized(self) -> None:
        screening = included_screening()
        self.assertEqual("INCLUDE", validate_glass_screening(screening))
        candidate = self.candidate(screening)
        candidate.score = score_candidate(candidate, ["silver sodium ion exchange"])
        status, reasons = assess_candidate(
            candidate, {"category_min_relevance": {"glass_ag_na_ion_exchange": 45}}
        )
        self.assertEqual("PRIORITY", status)
        self.assertIn("MEETS_CATEGORY_ROUTING_THRESHOLD", reasons)
        self.assertGreaterEqual(candidate.score, 80)

    def test_mixed_salt_must_be_excluded(self) -> None:
        screening = included_screening()
        screening.update(
            {
                "decision": "EXCLUDE",
                "decision_reason": "AgNO3/NaNO3 mixed salt.",
                "exclusion_reasons": ["MIXED_AGNO3_NANO3"],
                "molten_salt": "MIXED_SALT",
                "reference_comparison": "NOT_COMPARABLE",
            }
        )
        candidate = self.candidate(screening)
        status, reasons = assess_candidate(candidate, {})
        self.assertEqual("LOWER_PRIORITY", status)
        self.assertIn("MIXED_AGNO3_NANO3", reasons)

    def test_include_without_original_page_number_fails_closed(self) -> None:
        screening = included_screening()
        screening["main_values"][0]["source_locator"] = "Table 2"
        with self.assertRaisesRegex(RadarRuntimeError, "original page numbers"):
            validate_glass_screening(screening)

    def test_exact_reference_cannot_hide_multicomponent_glass(self) -> None:
        screening = included_screening()
        screening["glass_compositions"][0]["components"].append(
            {"oxide": "Al2O3", "value": 5.0}
        )
        with self.assertRaisesRegex(RadarRuntimeError, "75 mol% SiO2"):
            validate_glass_screening(screening)

    def test_excluded_and_uncertain_glass_records_never_become_featured(self) -> None:
        base = {
            "category": "glass_ag_na_ion_exchange",
            "event_status": "QUALIFYING",
            "event_class": "NEW_PUBLICATION",
            "triage_status": "LOWER_PRIORITY",
            "routing_score": 100,
        }
        records = []
        for decision in ("EXCLUDE", "UNCERTAIN"):
            record = copy.deepcopy(base)
            record.update(
                {
                    "work_id": decision.casefold(),
                    "glass_screening": {"decision": decision},
                }
            )
            records.append(record)
        included = copy.deepcopy(base)
        included.update(
            {
                "work_id": "include",
                "triage_status": "PRIORITY",
                "routing_score": 10,
                "glass_screening": {"decision": "INCLUDE"},
            }
        )
        records.append(included)
        self.assertEqual(
            {"include"},
            select_featured_work_ids_v2(
                records, target_per_category=3, hard_max_per_category=3
            ),
        )

    def test_terminal_glass_bundle_lists_conditions_values_pages_and_exclusion(self) -> None:
        end_at = datetime(2026, 8, 16, 12, 0, tzinfo=ZoneInfo("Asia/Taipei"))
        include = self.candidate(included_screening())
        include.events = [
            event_record(
                "formal_version_verified",
                "1985-06-01",
                "Crossref",
                "published-print",
                "https://doi.org/10.1000/glass",
                "date",
                "provider_metadata",
            )
        ]
        include.score = score_candidate(include, ["silver sodium ion exchange"])
        include.triage_status, include.triage_reasons = assess_candidate(
            include, {"category_min_relevance": {"glass_ag_na_ion_exchange": 45}}
        )

        excluded_screening = included_screening()
        excluded_screening.update(
            {
                "decision": "EXCLUDE",
                "decision_reason": "The bath contains AgNO3 and NaNO3.",
                "exclusion_reasons": ["MIXED_AGNO3_NANO3"],
                "molten_salt": "MIXED_SALT",
                "reference_comparison": "NOT_COMPARABLE",
            }
        )
        excluded = Candidate(
            title="Mixed nitrate silver exchange in glass",
            stream="glass_ag_na_ion_exchange",
            category="glass_ag_na_ion_exchange",
            source="Crossref",
            publication_date="1990-01-01",
            doi="10.1000/mixed",
            landing_url="https://doi.org/10.1000/mixed",
            glass_screening=excluded_screening,
            events=[
                event_record(
                    "formal_version_verified",
                    "1990-01-01",
                    "Crossref",
                    "published-print",
                    "https://doi.org/10.1000/mixed",
                    "date",
                    "provider_metadata",
                )
            ],
        )
        excluded.score = 100
        excluded.triage_status, excluded.triage_reasons = assess_candidate(excluded, {})

        def discoverer(*_args, **_kwargs):
            return DiscoveryResult(
                all_candidates=[include, excluded],
                priority_candidates=[include],
                raw_candidate_count=2,
                queries=[
                    {
                        "query_id": "query-001",
                        "category": "glass_ag_na_ion_exchange",
                        "query": "glass AgNO3 ion exchange",
                        "searched_at": end_at.isoformat(),
                        "source_ids": ["crossref"],
                        "status": "SUCCESS",
                        "result_count": 2,
                    },
                    {
                        "query_id": "query-002",
                        "category": "glass_ag_na_ion_exchange",
                        "query": "glass AgNO3 ion exchange",
                        "searched_at": end_at.isoformat(),
                        "source_ids": ["openalex"],
                        "status": "NO_RESULTS",
                        "result_count": 0,
                    }
                ],
                source_access=[
                    {
                        "source_id": "query-001-crossref",
                        "provider": "crossref",
                        "url": "https://api.crossref.org/works",
                        "accessed_at": end_at.isoformat(),
                        "status": "SUCCESS",
                        "result_count": 2,
                    },
                    {
                        "source_id": "query-002-openalex",
                        "provider": "openalex",
                        "url": "https://api.openalex.org/works",
                        "accessed_at": end_at.isoformat(),
                        "status": "NO_RESULTS",
                        "result_count": 0,
                    },
                ],
                checked_sources={"crossref", "openalex"},
                searched_sources={"crossref", "openalex"},
                unavailable_sources=set(),
            )

        def publisher_probe(*_args, **_kwargs):
            access = {
                "source_id": "publisher-glass",
                "provider": "publisher",
                "url": "https://doi.org/10.1000/glass",
                "accessed_at": end_at.isoformat(),
                "status": "SUCCESS",
                "result_count": 1,
                "work_id": include.work_id,
                "candidate_title": include.title,
                "category": include.category,
                "http_status": 200,
            }
            return [(include, access)], [access], []

        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            output = temporary / "output"
            execute(
                root=root,
                output_dir=output,
                state_path=temporary / "state.json",
                end_at=end_at,
                start_at=datetime(1900, 1, 1, tzinfo=ZoneInfo("Asia/Taipei")),
                mode="focused",
                run_id="glass-integration",
                execution_lane="chatgpt_work",
                profile_id="glass_ag_na_ion_exchange",
                protocol_commit="a" * 40,
                discoverer=discoverer,
                publisher_probe=publisher_probe,
                work_translation_overrides={
                    include.work_id: {
                        "title_zh_tw": "鈉矽酸鹽玻璃中的銀鈉離子交換",
                        "summary_zh_tw": "",
                    },
                    excluded.work_id: {
                        "title_zh_tw": "玻璃中的混合硝酸鹽銀離子交換",
                        "summary_zh_tw": "",
                    },
                },
            )
            run = json.loads((output / "EvidenceRadar_Run.json").read_text())
            report = (output / "EvidenceRadar_Report.html").read_text()
            self.assertEqual("focused", run["mode"])
            self.assertEqual(2, len(run["candidates"]))
            self.assertIn("Ag⁺/Na⁺ 離子交換全文篩選", report)
            self.assertIn("1.2e-11 cm2/s", report)
            self.assertIn("p. 8, Table 2", report)
            self.assertIn("MIXED_AGNO3_NANO3", report)


if __name__ == "__main__":
    unittest.main()
