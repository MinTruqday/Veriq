from types import SimpleNamespace

from src.modules.design.services.design_suggestion import (
    DesignSuggestionService,
    approved_performance_configuration_inputs,
    performance_targets_match,
)
from src.schemas.test_analysis import PerformanceScenario, SecurityCandidate


def test_design_suggestion_service_exposes_typed_generation_schemas():
    assert callable(DesignSuggestionService.generate_security)
    assert callable(DesignSuggestionService.generate_performance)
    assert SecurityCandidate.__name__ == "SecurityCandidate"
    assert PerformanceScenario.__name__ == "PerformanceScenario"


def test_performance_scenarios_must_preserve_explicit_numeric_targets():
    payload = SimpleNamespace(
        target_virtual_users=120,
        duration_minutes=15,
        target_requests_per_second=35.0,
    )
    scenario = {
        "virtual_users": 120,
        "duration_minutes": 15,
        "requests_per_second": 35.0,
    }

    assert performance_targets_match([scenario], payload)
    assert not performance_targets_match(
        [{**scenario, "virtual_users": 121}], payload
    )
    assert not performance_targets_match(
        [{**scenario, "duration_minutes": 16}], payload
    )
    assert not performance_targets_match(
        [{**scenario, "requests_per_second": 40.0}], payload
    )
    assert not performance_targets_match(
        [{**scenario, "requests_per_second": None}], payload
    )


def test_approved_performance_configuration_does_not_supply_missing_workload_values():
    inputs, missing = approved_performance_configuration_inputs(
        {
            "baseline": {},
            "load": {"description": "configured load"},
            "concurrency": {"minimum": 10, "maximum": 50},
            "duration_minutes": None,
            "requirement_refs": ["REQV-1"],
            "throughput_target": None,
        }
    )

    assert inputs["workload_types"] == ["load"]
    assert inputs["target_virtual_users"] is None
    assert inputs["duration_minutes"] is None
    assert inputs["target_requests_per_second"] is None
    assert inputs["workload_configuration"] == {"load": {"description": "configured load"}}
    assert "concurrency dạng số nguyên dương" in missing
    assert "duration_minutes" in missing


def test_approved_performance_configuration_uses_only_explicit_typed_values():
    inputs, missing = approved_performance_configuration_inputs(
        {
            "baseline": {},
            "load": {"target": "existing approved load section"},
            "concurrency": 240,
            "duration_minutes": 45,
            "requirement_refs": ["REQV-1", "REQV-1"],
            "throughput_target": 80,
        }
    )

    assert missing == []
    assert inputs == {
        "workload_types": ["load"],
        "target_virtual_users": 240,
        "duration_minutes": 45,
        "requirement_version_ids": ["REQV-1"],
        "target_requests_per_second": 80,
        "workload_configuration": {"load": {"target": "existing approved load section"}},
    }
