"""
Tests for scoring purge logic to ensure comprehensive removal of scoring contamination.

This tests the core logic that should be applied during migration to purge
all scoring data from the evidence-based analysis system.
"""

import json
from typing import Any

import pytest


def clean_scoring_structure(data: Any) -> Any:
    """
    Comprehensive scoring purge logic - mirrors the migration function.

    This function removes all scoring contamination from analysis JSON to ensure
    database stores same clean data that users see, preventing training data
    contamination for future ML/AI systems.
    """
    if isinstance(data, dict):
        cleaned = {}

        # Forbidden top-level structures that contain scoring
        forbidden_structures = [
            "technical_assessment",
            "professional_practices",
            "communication_skills",
            "growth_indicators",
            "team_fit_analysis",
        ]

        # Forbidden keys at any level
        forbidden_keys = [
            "overall_score",
            "confidence_score",
            "score",
            "rating",
            "verdict",
            "hire",
            "pass",
            "investigate",
            "metrics",
            "numerical_assessment",
            "overall_assessment",
            "code_quality",
            "architecture",
            "testing",
            "documentation",
            "best_practices",
            "version_control",
            "collaboration",
            "issue_management",
            "ci_cd",
            "documentation_quality",
            "commit_messages",
            "pr_descriptions",
            "issue_discussions",
            "learning_velocity",
            "technology_adoption",
            "contribution_consistency",
            "skill_progression",
        ]

        # Forbidden behavioral summary phrases
        forbidden_summaries = [
            "Shows moderate technical capability",
            "Follows industry best practices consistently",
            "Strong written communication evident",
            "Limited evidence of recent skill development",
        ]

        for key, value in data.items():
            # Skip entire forbidden structures
            if key in forbidden_structures:
                continue

            # Skip forbidden keys
            if any(forbidden in key.lower() for forbidden in forbidden_keys):
                continue

            # Clean forbidden summaries (exact matches or containing phrases)
            if isinstance(value, str):
                should_remove = False
                for forbidden in forbidden_summaries:
                    if forbidden in value:
                        should_remove = True
                        break
                if should_remove:
                    continue

            # Recursively clean nested structures
            cleaned[key] = clean_scoring_structure(value)

        return cleaned

    elif isinstance(data, list):
        cleaned_list = []
        for item in data:
            # For string items in lists, check for forbidden behavioral summaries
            if isinstance(item, str):
                should_remove = False
                forbidden_summaries = [
                    "Shows moderate technical capability",
                    "Follows industry best practices consistently",
                    "Strong written communication evident",
                    "Limited evidence of recent skill development",
                ]
                for forbidden in forbidden_summaries:
                    if forbidden in item:
                        should_remove = True
                        break
                if should_remove:
                    continue

            cleaned_item = clean_scoring_structure(item)
            # Only keep non-empty items
            # For dict items, check if they have meaningful content after cleaning
            if isinstance(cleaned_item, dict):
                # Only keep dict if it has non-forbidden keys
                if cleaned_item:  # Non-empty dict
                    cleaned_list.append(cleaned_item)
            elif cleaned_item is not None and cleaned_item != "":
                cleaned_list.append(cleaned_item)
        return cleaned_list

    else:
        return data


class TestScoringPurgeLogic:
    """Test the comprehensive scoring purge logic."""

    def test_removes_forbidden_top_level_structures(self):
        """Test removal of forbidden top-level structures."""
        contaminated_data = {
            "technical_assessment": {"score": 85, "details": "Good code"},
            "professional_practices": {"rating": 4.2, "collaboration": "Excellent"},
            "communication_skills": {"verdict": "HIRE", "pr_quality": "High"},
            "growth_indicators": {"pass": True, "learning_velocity": 3.2},
            "team_fit_analysis": {"investigate": False, "culture_fit": 90},
            "evidence_patterns": ["Pattern 1", "Pattern 2"],  # Should remain
            "insights": {"key_finding": "Clear evidence"},  # Should remain
        }

        result = clean_scoring_structure(contaminated_data)

        # Forbidden structures should be completely removed
        assert "technical_assessment" not in result
        assert "professional_practices" not in result
        assert "communication_skills" not in result
        assert "growth_indicators" not in result
        assert "team_fit_analysis" not in result

        # Valid evidence-based fields should remain
        assert result["evidence_patterns"] == ["Pattern 1", "Pattern 2"]
        assert result["insights"] == {"key_finding": "Clear evidence"}

    def test_removes_forbidden_keys_at_any_level(self):
        """Test removal of forbidden keys at any nested level."""
        contaminated_data = {
            "analysis": {
                "overall_score": 0.85,
                "confidence_score": 0.9,
                "details": {
                    "score": 90,
                    "rating": 4.5,
                    "metrics": {"code_quality": 85, "architecture": 4.2},
                    "testing": {"coverage": 0.8, "verdict": "PASS"},
                    "evidence": ["Valid evidence"],  # Should remain
                },
                "confidence_explanation": "High confidence based on evidence",  # Should remain
            }
        }

        result = clean_scoring_structure(contaminated_data)

        # All scoring fields should be removed
        assert "overall_score" not in result["analysis"]
        assert "confidence_score" not in result["analysis"]
        assert "score" not in result["analysis"]["details"]
        assert "rating" not in result["analysis"]["details"]
        assert "metrics" not in result["analysis"]["details"]
        assert "testing" not in result["analysis"]["details"]

        # Valid fields should remain
        assert result["analysis"]["details"]["evidence"] == ["Valid evidence"]
        assert (
            result["analysis"]["confidence_explanation"]
            == "High confidence based on evidence"
        )

    def test_removes_behavioral_summary_phrases(self):
        """Test removal of forbidden behavioral summary phrases."""
        contaminated_data = {
            "summary1": "Shows moderate technical capability and works well",
            "summary2": "Follows industry best practices consistently",
            "summary3": "Strong written communication evident in all PRs",
            "summary4": "Limited evidence of recent skill development",
            "valid_summary": "Developer has 3 years Python experience with Django",  # Should remain
        }

        result = clean_scoring_structure(contaminated_data)

        # Behavioral summaries should be removed
        assert "summary1" not in result
        assert "summary2" not in result
        assert "summary3" not in result
        assert "summary4" not in result

        # Factual summary should remain
        assert (
            result["valid_summary"]
            == "Developer has 3 years Python experience with Django"
        )

    def test_preserves_evidence_based_structure(self):
        """Test that clean evidence-based data is preserved intact."""
        clean_evidence_data = {
            "evidence_patterns": [
                "Strong testing practices with 1,422 tests",
                "Consistent commit patterns over 3 years",
                "Active code review participation",
            ],
            "insights": {
                "technical_depth": "Deep expertise in Python ecosystem",
                "project_complexity": "Handles multi-service architectures",
            },
            "confidence_explanation": "High confidence based on 7 evidence types across 3 years",
            "technical_patterns": {
                "languages": ["Python", "JavaScript", "TypeScript"],
                "frameworks": ["Django", "React", "FastAPI"],
                "tools": ["Docker", "PostgreSQL", "Redis"],
            },
            "quality_indicators": {
                "test_coverage": "Maintains high coverage",
                "error_handling": "Robust exception handling",
            },
        }

        result = clean_scoring_structure(clean_evidence_data)

        # All clean data should be preserved exactly
        assert result == clean_evidence_data

    def test_handles_deeply_nested_contamination(self):
        """Test cleaning of complex nested contaminated structures."""
        deeply_contaminated = {
            "analysis": {
                "technical_assessment": {
                    "code_quality": {
                        "score": 85,
                        "rating": 4.2,
                        "metrics": {
                            "complexity": 3.1,
                            "maintainability": 4.5,
                            "overall_score": 0.85,
                        },
                    },
                    "architecture": {
                        "patterns": ["MVC", "Repository"],
                        "score": 90,
                        "verdict": "EXCELLENT",
                    },
                },
                "evidence_section": {
                    "patterns": ["Valid pattern 1", "Valid pattern 2"],
                    "nested_evidence": {"commits": 342, "prs": 89},
                },
            }
        }

        result = clean_scoring_structure(deeply_contaminated)

        # Entire technical_assessment should be removed
        assert "technical_assessment" not in result["analysis"]

        # Clean evidence section should remain
        assert result["analysis"]["evidence_section"]["patterns"] == [
            "Valid pattern 1",
            "Valid pattern 2",
        ]
        assert (
            result["analysis"]["evidence_section"]["nested_evidence"]["commits"] == 342
        )
        assert result["analysis"]["evidence_section"]["nested_evidence"]["prs"] == 89

    def test_handles_contaminated_lists(self):
        """Test cleaning of lists containing contaminated items."""
        data_with_contaminated_lists = {
            "assessments": [
                {
                    "name": "Item 1",
                    "score": 85,
                    "rating": 4.2,
                },  # Forbidden keys removed, name remains
                {
                    "name": "Item 2",
                    "verdict": "HIRE",
                },  # Forbidden key removed, name remains
                {"name": "Item 3", "evidence": "Valid data"},  # Should remain intact
                {
                    "name": "Item 4",
                    "patterns": ["Pattern A", "Pattern B"],
                },  # Should remain intact
            ],
            "insights": [
                "Shows moderate technical capability",  # Should be removed
                "Developer has 5+ years experience",  # Should remain
                "Strong written communication evident",  # Should be removed
            ],
        }

        result = clean_scoring_structure(data_with_contaminated_lists)

        # All 4 assessment items should remain, but with forbidden keys removed
        assert len(result["assessments"]) == 4
        clean_items = result["assessments"]

        # Verify each item's expected state after cleaning
        item_1 = next(
            (item for item in clean_items if item.get("name") == "Item 1"), None
        )
        item_2 = next(
            (item for item in clean_items if item.get("name") == "Item 2"), None
        )
        item_3 = next(
            (item for item in clean_items if item.get("name") == "Item 3"), None
        )
        item_4 = next(
            (item for item in clean_items if item.get("name") == "Item 4"), None
        )

        # Item 1: score and rating removed, name remains
        assert item_1 == {"name": "Item 1"}

        # Item 2: verdict removed, name remains
        assert item_2 == {"name": "Item 2"}

        # Item 3: intact with valid data
        assert item_3["name"] == "Item 3"
        assert item_3["evidence"] == "Valid data"

        # Item 4: intact with valid patterns
        assert item_4["name"] == "Item 4"
        assert item_4["patterns"] == ["Pattern A", "Pattern B"]

        # Only factual insight should remain
        assert len(result["insights"]) == 1
        assert result["insights"][0] == "Developer has 5+ years experience"

    def test_database_export_contamination_example(self):
        """Test cleaning data that matches real database contamination example."""
        # This matches the contamination found in the database dump
        database_contaminated = {
            "analysis": {
                "overall_score": 0.30000000000000004,
                "confidence_score": 0.25,
                "technical_assessment": {
                    "code_quality": 0.4,
                    "architecture": 0.3,
                    "testing": 0.2,
                    "documentation": 0.3,
                },
                "professional_practices": {
                    "version_control": 0.4,
                    "collaboration": 0.2,
                    "issue_management": 0.1,
                },
                "evidence_patterns": [
                    "Limited recent activity",
                    "Basic repository structure",
                ],
                "confidence": "medium",  # This should remain as it's Claude's built-in confidence
            }
        }

        result = clean_scoring_structure(database_contaminated)

        # All scoring contamination should be removed
        assert "overall_score" not in result["analysis"]
        assert "confidence_score" not in result["analysis"]
        assert "technical_assessment" not in result["analysis"]
        assert "professional_practices" not in result["analysis"]

        # Evidence-based data should remain
        assert result["analysis"]["evidence_patterns"] == [
            "Limited recent activity",
            "Basic repository structure",
        ]
        assert result["analysis"]["confidence"] == "medium"

    def test_comprehensive_forbidden_keys_coverage(self):
        """Test that all comprehensive forbidden keys are properly removed."""
        comprehensive_contamination = {
            # Scoring keys
            "overall_score": 0.85,
            "confidence_score": 0.9,
            "score": 90,
            "rating": 4.5,
            "verdict": "HIRE",
            "hire": True,
            "pass": True,
            "investigate": False,
            # Assessment keys
            "metrics": {"complexity": 3.1},
            "numerical_assessment": 4.2,
            "overall_assessment": "Strong",
            # Technical scoring keys
            "code_quality": 85,
            "architecture": 4.2,
            "testing": 0.8,
            "documentation": 90,
            "best_practices": True,
            "version_control": 4.5,
            # Collaboration scoring keys
            "collaboration": 3.8,
            "issue_management": 4.1,
            "ci_cd": 3.5,
            "documentation_quality": 4.3,
            "commit_messages": 3.9,
            "pr_descriptions": 4.0,
            "issue_discussions": 3.7,
            # Growth scoring keys
            "learning_velocity": 3.2,
            "technology_adoption": 4.1,
            "contribution_consistency": 3.8,
            "skill_progression": 4.0,
            # This should remain
            "evidence_patterns": ["Valid evidence"],
        }

        result = clean_scoring_structure(comprehensive_contamination)

        # Only evidence_patterns should remain
        assert len(result) == 1
        assert result["evidence_patterns"] == ["Valid evidence"]

    def test_empty_and_edge_cases(self):
        """Test handling of empty and edge case values."""
        edge_case_data = {
            "empty_dict": {},
            "empty_list": [],
            "none_value": None,
            "empty_string": "",
            "zero_value": 0,
            "false_value": False,
            "nested_empty": {"inner": {}},
            "score": 0,  # This should be removed even if 0
        }

        result = clean_scoring_structure(edge_case_data)

        # Empty values should be preserved except for forbidden keys
        assert result["empty_dict"] == {}
        assert result["empty_list"] == []
        assert result["none_value"] is None
        assert result["empty_string"] == ""
        assert result["zero_value"] == 0
        assert result["false_value"] is False
        assert result["nested_empty"] == {"inner": {}}

        # Forbidden key should be removed regardless of value
        assert "score" not in result
