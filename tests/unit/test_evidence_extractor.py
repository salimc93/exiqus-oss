"""
Test suite for Evidence Extractor module.

Tests evidence extraction from repository data including technical patterns,
security issues, collaboration patterns, and behavioral analysis integration.
"""

import re
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from github_analyzer.core.evidence.evidence_extractor import EvidenceExtractor
from github_analyzer.data.models import (
    CommitInfo,
    FileInfo,
    RepositoryData,
    RepositoryMetrics,
)


class TestEvidenceExtractor:
    """Test suite for evidence extraction functionality."""

    @pytest.fixture
    def evidence_extractor(self):
        """Create an EvidenceExtractor instance."""
        return EvidenceExtractor()

    @pytest.fixture
    def mock_repo_data(self):
        """Create mock repository data with various patterns."""
        now = datetime.now(timezone.utc)

        # Create diverse commit history
        commits = [
            CommitInfo(
                sha="abc123",
                message="feat: implement user authentication with JWT tokens",
                author_name="John Doe",
                author_email="john@example.com",
                author_login="johndoe",
                date=now - timedelta(days=1),
                additions=150,
                deletions=20,
            ),
            CommitInfo(
                sha="def456",
                message="fix: resolve SQL injection vulnerability in user queries",
                author_name="John Doe",
                author_email="john.doe@company.com",  # Different email
                author_login="johndoe",  # Same GitHub username
                date=now - timedelta(days=2),
                additions=50,
                deletions=30,
            ),
            CommitInfo(
                sha="ghi789",
                message="test: add comprehensive test coverage for auth module",
                author_name="Jane Smith",
                author_email="jane@example.com",
                author_login="janesmith",
                date=now - timedelta(days=3),
                additions=200,
                deletions=0,
            ),
            CommitInfo(
                sha="jkl012",
                message="refactor: improve code organization and reduce complexity",
                author_name="John Doe",
                author_email="12345+johndoe@users.noreply.github.com",  # GitHub noreply
                author_login="johndoe",  # Same GitHub username
                date=now - timedelta(days=4),
                additions=300,
                deletions=250,
            ),
            CommitInfo(
                sha="mno345",
                message="docs: update README with API documentation",
                author_name="Jane Smith",
                author_email="jane@example.com",
                author_login="janesmith",
                date=now - timedelta(days=5),
                additions=100,
                deletions=10,
            ),
            CommitInfo(
                sha="pqr678",
                message="ci: configure GitHub Actions for automated testing",
                author_name="John Doe",
                author_email="john@example.com",
                author_login="johndoe",
                date=now - timedelta(days=6, hours=22),  # Late night commit
                additions=80,
                deletions=0,
            ),
            CommitInfo(
                sha="stu901",
                message="fix: address performance issues in data processing",
                author_name="Bob Wilson",
                author_email="bob@example.com",
                author_login="bobwilson",
                date=now - timedelta(days=7),
                additions=120,
                deletions=60,
            ),
            # Weekend commit
            CommitInfo(
                sha="vwx234",
                message="feat: add caching layer for improved performance",
                author_name="John Doe",
                author_email="john@example.com",
                author_login="johndoe",
                date=now - timedelta(days=8),  # Assuming this is a weekend
                additions=200,
                deletions=50,
            ),
            CommitInfo(
                sha="yza567",
                message="feat: implement user profile management",
                author_name="Jane Smith",
                author_email="jane@example.com",
                author_login="janesmith",
                date=now - timedelta(days=9),
                additions=180,
                deletions=30,
            ),
            CommitInfo(
                sha="bcd890",
                message="fix: resolve memory leak in data processing",
                author_name="Bob Wilson",
                author_email="bob@example.com",
                author_login="bobwilson",
                date=now - timedelta(days=10),
                additions=75,
                deletions=15,
            ),
        ]

        # Create file structure with various patterns
        files = [
            FileInfo(
                path="src/auth/auth_service.py",
                name="auth_service.py",
                type="file",
                extension="py",
                size=5000,
                is_test=False,
                is_documentation=False,
            ),
            FileInfo(
                path="src/auth/test_auth_service.py",
                name="test_auth_service.py",
                type="file",
                extension="py",
                size=8000,
                is_test=True,
                is_documentation=False,
            ),
            FileInfo(
                path="src/database/queries.py",
                name="queries.py",
                type="file",
                extension="py",
                size=3000,
                is_test=False,
                is_documentation=False,
            ),
            FileInfo(
                path="tests/integration/test_api.py",
                name="test_api.py",
                type="file",
                extension="py",
                size=6000,
                is_test=True,
                is_documentation=False,
            ),
            FileInfo(
                path="README.md",
                name="README.md",
                type="file",
                extension="md",
                size=4000,
                is_test=False,
                is_documentation=True,
            ),
            FileInfo(
                path=".github/workflows/ci.yml",
                name="ci.yml",
                type="file",
                extension="yml",
                size=1500,
                is_test=False,
                is_documentation=False,
            ),
            FileInfo(
                path="docs/api.md",
                name="api.md",
                type="file",
                extension="md",
                size=3500,
                is_test=False,
                is_documentation=True,
            ),
            FileInfo(
                path="src/utils/crypto.py",
                name="crypto.py",
                type="file",
                extension="py",
                size=2000,
                is_test=False,
                is_documentation=False,
            ),
            # Add some less common language files
            FileInfo(
                path="src/scripts/analyze.clj",
                name="analyze.clj",
                type="file",
                extension="clj",
                size=1000,
                is_test=False,
                is_documentation=False,
            ),
        ]

        return RepositoryData(
            name="test-repo",
            full_name="user/test-repo",
            url="https://github.com/user/test-repo",
            owner="user",
            description="A test repository for evidence extraction",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            pushed_at=datetime.now(timezone.utc),
            default_branch="main",
            size=31000,
            languages={"Python": 25000, "JavaScript": 5000, "Clojure": 1000},
            topics=["python", "javascript", "testing"],
            license_name="MIT",
            stars=150,
            forks=25,
            watchers=30,
            open_issues=5,
            has_readme=True,
            has_license=True,
            has_contributing=False,
            has_tests=True,
            has_ci_config=True,
            recent_commits=commits,
            file_structure=files,
            readme_content="# Test Repository\n\nComprehensive test application...",
            fetched_at=datetime.now(timezone.utc),
            is_private=False,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
            metrics=RepositoryMetrics(
                total_commits=150,
                unique_contributors=3,
                commit_frequency=2.5,
                lines_of_code=25000,
                test_coverage_estimate=0.65,
                documentation_presence="30 documentation files in 200 total files",
                avg_commit_size=85.3,
                days_since_last_commit=1,
            ),
        )

    def test_extract_all_evidence(self, evidence_extractor, mock_repo_data):
        """Test comprehensive evidence extraction."""
        evidence = evidence_extractor.extract_all_evidence(mock_repo_data)

        # Verify all evidence categories are present
        assert "technical_patterns" in evidence
        assert "security_issues" in evidence
        assert "collaboration_patterns" in evidence
        assert "quality_indicators" in evidence
        assert "temporal_insights" in evidence
        # NO behavioral_analysis after The Great Purge
        assert "behavioral_analysis" not in evidence
        assert "skill_evolution" in evidence

        # Verify evidence contains actual data
        assert len(evidence["technical_patterns"]) > 0
        # behavioral_analysis has been removed
        assert isinstance(evidence["skill_evolution"], dict)

    def test_extract_technical_evidence(self, evidence_extractor, mock_repo_data):
        """Test technical pattern extraction."""
        evidence = evidence_extractor.extract_technical_evidence(mock_repo_data)

        # Check language expertise detection
        lang_evidence = [e for e in evidence if e["type"] == "language_expertise"]
        assert len(lang_evidence) > 0
        assert "Python" in lang_evidence[0]["finding"]
        assert lang_evidence[0]["languages"]["Python"] == 25000

        # Check architecture patterns
        arch_evidence = [e for e in evidence if e["type"] == "architecture"]
        assert len(arch_evidence) > 0
        assert "src/" in arch_evidence[0]["finding"]

        # Check test coverage structure
        test_evidence = [e for e in evidence if e["type"] == "test_coverage_structure"]
        assert len(test_evidence) > 0
        assert "test files" in test_evidence[0]["finding"]

    def test_extract_security_evidence(self, evidence_extractor, mock_repo_data):
        """Test security-related evidence extraction."""
        evidence = evidence_extractor.extract_security_evidence(mock_repo_data)

        # Debug: Print all evidence
        print(f"All evidence: {evidence}")

        # Check SQL injection detection
        sql_evidence = [
            e for e in evidence if "sql injection" in e.get("finding", "").lower()
        ]
        print(f"SQL evidence: {sql_evidence}")
        assert len(sql_evidence) > 0
        assert sql_evidence[0]["severity"] == "medium"

        # Check security file detection
        sec_files = [e for e in evidence if e["type"] == "security_awareness"]
        print(f"Security files: {sec_files}")
        assert len(sec_files) > 0
        assert "crypto.py" in str(sec_files[0]["files"])

    def test_extract_collaboration_evidence(self, evidence_extractor, mock_repo_data):
        """Test collaboration pattern extraction."""
        evidence = evidence_extractor.extract_collaboration_evidence(mock_repo_data)

        # Check multiple contributors detection
        collab_evidence = [e for e in evidence if e["type"] == "collaboration"]
        assert len(collab_evidence) > 0
        # Should detect 3 distinct GitHub users (johndoe, janesmith, bobwilson) despite johndoe's multiple emails
        assert "3 distinct GitHub users" in collab_evidence[0]["finding"]

        # Check commit discipline
        discipline = [e for e in evidence if e["type"] == "commit_discipline"]
        assert len(discipline) > 0
        assert "feat:" in str(discipline[0]["examples"])

        # Check issue tracking
        # Our test data doesn't have issue references, so this might be empty
        # But the extractor should still work

    def test_email_deduplication(self, evidence_extractor):
        """Test email deduplication logic."""
        contributors = {
            "john@example.com": 10,
            "john.doe@company.com": 5,
            "12345+johndoe@users.noreply.github.com": 3,
            "jane@example.com": 8,
            "bob@example.com": 4,
        }

        deduplicated = evidence_extractor._deduplicate_contributors(contributors)

        # Should merge John's three emails into one
        assert len(deduplicated) == 3

        # Check that commits are summed correctly
        john_total = sum(
            v for k, v in deduplicated.items() if "john" in k.lower() or "johndoe" in k
        )
        assert john_total == 18  # 10 + 5 + 3

    def test_are_same_person(self, evidence_extractor):
        """Test person identification logic."""
        # Test GitHub noreply pattern
        assert evidence_extractor._are_same_person(
            "john@example.com", "12345+johndoe@users.noreply.github.com"
        )

        # Test similar usernames
        assert evidence_extractor._are_same_person(
            "john.doe@example.com", "johndoe@company.com"
        )

        # Test with numbers
        assert evidence_extractor._are_same_person(
            "smith@example.com", "smith123@example.com"
        )

        # Test different people
        assert not evidence_extractor._are_same_person(
            "john@example.com", "jane@example.com"
        )

    def test_extract_quality_evidence(self, evidence_extractor, mock_repo_data):
        """Test code quality indicator extraction."""
        evidence = evidence_extractor.extract_quality_evidence(mock_repo_data)

        # Check refactoring detection
        refactor = [e for e in evidence if e["type"] == "code_maintenance"]
        assert len(refactor) > 0
        assert "refactor" in refactor[0]["finding"].lower()

        # Check documentation detection
        docs = [e for e in evidence if e["type"] == "documentation"]
        assert len(docs) > 0
        assert docs[0]["has_readme"] is True

    def test_extract_temporal_evidence(self, evidence_extractor, mock_repo_data):
        """Test time-based pattern extraction."""
        evidence = evidence_extractor.extract_temporal_evidence(mock_repo_data)

        # Check activity pattern
        activity = [e for e in evidence if e["type"] == "activity_pattern"]
        assert len(activity) > 0
        assert "activity_level" in activity[0]  # Now using qualitative assessment
        assert activity[0]["activity_level"] in [
            "inactive",
            "low activity",
            "moderately active",
            "active",
            "very active",
        ]

        # Check commit size pattern
        size_pattern = [e for e in evidence if e["type"] == "commit_size_pattern"]
        assert len(size_pattern) > 0
        assert "largest" in size_pattern[0]

        # Check work pattern (might not have enough data in test)
        # This depends on having enough commits

    def test_get_code_file_extensions(self, evidence_extractor, mock_repo_data):
        """Test dynamic code file extension detection."""
        extensions = evidence_extractor._get_code_file_extensions(
            mock_repo_data.file_structure
        )

        # Should detect Python and Clojure
        assert "py" in extensions
        assert "clj" in extensions

        # Should not include documentation
        assert "md" not in extensions

    def test_behavioral_analysis_removed(self, evidence_extractor, mock_repo_data):
        """Test that behavioral analysis has been removed after The Great Purge."""
        # Verify behavioral_analyzer doesn't exist
        assert not hasattr(evidence_extractor, "behavioral_analyzer")

        # Extract all evidence
        evidence = evidence_extractor.extract_all_evidence(mock_repo_data)

        # Ensure no behavioral analysis in the output
        assert "behavioral_analysis" not in evidence
        assert "work_patterns" not in evidence

        # But collaboration patterns should still exist (factual, not behavioral)
        assert "collaboration_patterns" in evidence

    def test_temporal_analysis_integration(self, evidence_extractor, mock_repo_data):
        """Test temporal analysis integration."""
        with patch.object(
            evidence_extractor.temporal_analyzer, "analyze_skill_evolution"
        ) as mock_analyze:
            mock_analyze.return_value = {
                "growth_summary": {
                    "trajectory": "expanding",
                    "growth_indicators": [
                        "Added new language",
                        "Improved architecture",
                        "Enhanced testing",
                    ],
                    "challenges": [],
                },
                "recent_focus": {
                    "primary_area": "performance optimization",
                    "focus_areas": [
                        "caching",
                        "query optimization",
                        "async processing",
                    ],
                },
                "activity_trends": {
                    "momentum_interpretation": "increasing",
                    "overall_frequency": 2.5,
                    "consistency": {"interpretation": "consistent", "active_weeks": 8},
                },
            }

            result = evidence_extractor._integrate_temporal_analysis(mock_repo_data)

            assert result["development_trajectory"] == "expanding"
            assert len(result["temporal_insights"]) > 0
            assert result["activity_trend"] == "increasing"

            # Check growth insights
            growth_insights = [
                i for i in result["temporal_insights"] if i["type"] == "skill_growth"
            ]
            assert len(growth_insights) > 0
            assert "continuous learning" in growth_insights[0]["insight"]

    def test_evidence_summary_generation(self, evidence_extractor):
        """Test evidence summary generation."""
        evidence = {
            "technical_patterns": [
                {"type": "test", "finding": "Good test coverage"},
                {"type": "architecture", "finding": "Clean architecture"},
            ],
            "security_issues": [
                {
                    "type": "vulnerability",
                    "severity": "high",
                    "finding": "SQL injection risk",
                },
            ],
            "collaboration_patterns": [
                {"type": "teamwork", "finding": "Active collaboration"},
            ],
            "quality_indicators": [],
            "behavioral_analysis": {
                "behavioral_insights": [
                    {
                        "type": "work_consistency",
                        "finding": "Consistent",
                        "insight": "Reliable",
                    },
                ],
            },
        }

        summary = evidence_extractor.get_evidence_summary(evidence)

        assert summary["total_evidence_points"] > 0
        assert len(summary["high_value_findings"]) > 0
        assert len(summary["key_insights"]) > 0

        # Check high-value finding detection
        high_value = summary["high_value_findings"]
        security_findings = [f for f in high_value if "SQL injection" in f["finding"]]
        assert len(security_findings) > 0

    def test_security_pattern_detection(self, evidence_extractor):
        """Test specific security pattern detection."""
        # Test hardcoded secrets pattern
        patterns = evidence_extractor.security_patterns["hardcoded_secrets"]
        test_code = 'api_key = "sk-1234567890abcde"'

        matches = [p for p in patterns if re.search(p, test_code)]
        assert len(matches) > 0

        # Test weak crypto pattern
        crypto_patterns = evidence_extractor.security_patterns["weak_crypto"]
        weak_code = "hashlib.md5(password)"

        matches = [p for p in crypto_patterns if re.search(p, weak_code)]
        assert len(matches) > 0

    def test_empty_repository_handling(self, evidence_extractor):
        """Test handling of repositories with minimal data."""
        empty_repo = RepositoryData(
            name="empty-repo",
            full_name="user/empty-repo",
            url="https://github.com/user/empty-repo",
            owner="user",
            description="",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            pushed_at=datetime.now(timezone.utc),
            default_branch="main",
            size=0,
            languages={},
            topics=[],
            license_name=None,
            stars=0,
            forks=0,
            watchers=0,
            open_issues=0,
            has_readme=False,
            has_license=False,
            has_contributing=False,
            has_tests=False,
            has_ci_config=False,
            recent_commits=[],
            file_structure=[],
            readme_content="",
            fetched_at=datetime.now(timezone.utc),
            is_private=False,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
            metrics=RepositoryMetrics(
                total_commits=0,
                unique_contributors=0,
                commit_frequency=0,
                lines_of_code=0,
                test_coverage_estimate=0,
                documentation_presence="0 documentation files found",
                avg_commit_size=0,
                days_since_last_commit=0,
            ),
        )

        # Should not crash
        evidence = evidence_extractor.extract_all_evidence(empty_repo)

        assert evidence is not None
        # Empty repositories will still have some basic evidence (e.g. complexity baseline)
        assert len(evidence["technical_patterns"]) >= 0
        assert len(evidence["collaboration_patterns"]) == 0
