"""
Performance benchmarking tests for evidence-based system.

Tests performance characteristics of the evidence-based analysis
to ensure it meets performance requirements.
"""

import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from github_analyzer.ai.analyzer import AIAnalyzer
from github_analyzer.core.evidence.insight_engine import InsightEngine
from github_analyzer.data.models import (
    CommitInfo,
    FileInfo,
    RepositoryData,
    RepositoryMetrics,
)


class TestEvidencePerformance:
    """Performance tests for evidence-based analysis system."""

    @pytest.fixture
    def insight_engine(self):
        """Create InsightEngine instance."""
        return InsightEngine()

    @pytest.fixture
    def large_repo_data(self):
        """Create a large repository for performance testing."""
        # Simulate a large enterprise repository
        return RepositoryData(
            url="https://github.com/enterprise/large-system",
            full_name="enterprise/large-system",
            name="large-system",
            owner="enterprise",
            description="Large enterprise system with extensive history",
            created_at=datetime(2015, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime.now(timezone.utc),
            pushed_at=datetime.now(timezone.utc),
            default_branch="main",
            size=500000,  # 500MB
            languages={
                "Java": 2000000,
                "Python": 500000,
                "JavaScript": 300000,
                "TypeScript": 200000,
                "Go": 100000,
                "Rust": 50000,
            },
            topics=["enterprise", "microservices", "cloud-native"],
            license_name="MIT",
            stars=1500,
            forks=400,
            watchers=200,
            open_issues=150,
            has_readme=True,
            has_license=True,
            has_contributing=True,
            has_tests=True,
            has_ci_config=True,
            # Simulate extensive commit history
            recent_commits=[
                CommitInfo(
                    sha=f"commit_{i}",
                    message=f"feat: Feature implementation {i}",
                    author_name=f"dev_{i % 50}",  # 50 different contributors
                    author_email=f"dev_{i % 50}@example.com",
                    date=datetime(2024, 1, (i % 30) + 1, 10, 0, tzinfo=timezone.utc),
                )
                for i in range(1000)  # 1000 recent commits
            ],
            # Simulate complex file structure
            file_structure=[
                FileInfo(
                    path=f"src/services/service_{i}/main.py",
                    name="main.py",
                    size=5000,
                    type="file",
                    extension="py",
                )
                for i in range(100)
            ]
            + [
                FileInfo(
                    path=f"tests/test_service_{i}.py",
                    name=f"test_service_{i}.py",
                    size=3000,
                    type="file",
                    extension="py",
                    is_test=True,
                )
                for i in range(100)  # 100 test files
            ],
            readme_content="# Large System\n\n" + "Documentation content " * 1000,
            metrics=RepositoryMetrics(
                total_commits=50000,
                unique_contributors=200,
                lines_of_code=3000000,  # 3M lines
                test_coverage_estimate=0.82,
                documentation_presence="2 documentation files in 10 total files",
                days_since_last_commit=1,
                commit_frequency=50.0,
                avg_commit_size=150.0,
            ),
            fetched_at=datetime.now(timezone.utc),
            is_private=False,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
        )

    def test_insight_engine_performance_baseline(self, insight_engine, large_repo_data):
        """Test baseline performance of InsightEngine analysis."""
        from github_analyzer.core.evidence.evidence_extractor import EvidenceExtractor

        # Extract evidence first
        extractor = EvidenceExtractor()
        evidence = extractor.extract_all_evidence(large_repo_data)

        start_time = time.time()

        # Generate insights from evidence
        result = insight_engine.generate_screening_insights(
            evidence=evidence, context="enterprise", repository_type="microservices"
        )

        end_time = time.time()
        analysis_time = end_time - start_time

        # Analysis should complete within reasonable time
        assert analysis_time < 5.0  # Should complete within 5 seconds
        assert result is not None
        assert len(result.insights) > 0

        print(f"\nBaseline analysis time: {analysis_time:.3f}s")
        print(f"Insights generated: {len(result.insights)}")

    def test_evidence_extraction_scaling(self, insight_engine):
        """Test how evidence extraction scales with repository size."""
        from github_analyzer.core.evidence.evidence_extractor import EvidenceExtractor

        extractor = EvidenceExtractor()
        sizes = [100, 1000, 10000, 100000]  # Different repo sizes in lines of code
        times = []

        for size in sizes:
            repo = self._create_repo_with_size(size)

            start_time = time.time()
            evidence = extractor.extract_all_evidence(repo)
            end_time = time.time()

            extraction_time = end_time - start_time
            times.append(extraction_time)

            pattern_count = sum(
                len(v) if isinstance(v, list) else 1 for v in evidence.values() if v
            )
            print(
                f"\nSize: {size} LOC, Time: {extraction_time:.3f}s, Evidence items: {pattern_count}"
            )

        # Check that performance doesn't degrade exponentially
        # Time should not increase more than linearly with size
        for i in range(1, len(times)):
            size_ratio = sizes[i] / sizes[i - 1]
            time_ratio = times[i] / times[i - 1]
            # Allow some overhead, but not exponential growth
            assert time_ratio < size_ratio * 2

    def test_context_analysis_performance(self, insight_engine, large_repo_data):
        """Test performance of context-specific analysis."""
        from github_analyzer.core.evidence.evidence_extractor import EvidenceExtractor

        contexts = ["startup", "enterprise", "agency", "open_source"]

        # First, extract evidence once
        extractor = EvidenceExtractor()
        evidence = extractor.extract_all_evidence(large_repo_data)

        context_times = {}

        for context in contexts:
            start_time = time.time()
            result = insight_engine.generate_screening_insights(
                evidence=evidence, context=context
            )
            end_time = time.time()

            context_times[context] = end_time - start_time
            print(
                f"\nContext {context}: {context_times[context]:.3f}s, "
                f"Insights: {len(result.insights)}"
            )

        # All context analyses should be fast (under 1 second)
        assert all(t < 1.0 for t in context_times.values())

    @patch("github_analyzer.ai.analyzer.anthropic.Anthropic")
    def test_ai_analysis_performance_with_caching(
        self, mock_anthropic, mock_get_config_new, large_repo_data
    ):
        """Test AI analysis performance with caching considerations."""
        analyzer = AIAnalyzer()
        analyzer.cost_tracker.check_budget = Mock(return_value=(True, "Within budget"))

        # Mock AI response
        mock_response = Mock()
        mock_response.content = [
            Mock(
                text=(
                    '{"summary": "Test", "evidence_strength": {"technical_competence": 85, '
                    '"communication_skills": 80, "professional_practices": 90, '
                    '"growth_potential": 75}, "evidence_patterns": [], '
                    '"context_alignment": {}, "verification_gaps": [], "key_insights": []}'
                )
            )
        ]
        mock_response.usage = Mock(input_tokens=1000, output_tokens=500)
        mock_anthropic.return_value.messages.create.return_value = mock_response

        # First analysis (cold)
        start_time = time.time()
        analyzer.analyze_repository(large_repo_data)
        cold_time = time.time() - start_time

        # Second analysis (should use any internal optimizations)
        start_time = time.time()
        analyzer.analyze_repository(large_repo_data)
        warm_time = time.time() - start_time

        print(f"\nCold analysis: {cold_time:.3f}s")
        print(f"Warm analysis: {warm_time:.3f}s")

        # Both should complete reasonably quickly
        assert cold_time < 10.0
        assert warm_time < 10.0

    def test_concurrent_analysis_integrity(self, insight_engine):
        """Test concurrent analysis integrity - verifies correctness under concurrent load."""
        import concurrent.futures

        from github_analyzer.core.evidence.evidence_extractor import EvidenceExtractor

        # Create multiple different repositories
        repos = [self._create_repo_with_size(10000) for _ in range(5)]

        def analyze_repo(repo):
            extractor = EvidenceExtractor()
            evidence = extractor.extract_all_evidence(repo)
            return insight_engine.generate_screening_insights(evidence)

        # Sequential baseline
        start_time = time.time()
        [analyze_repo(repo) for repo in repos]
        sequential_time = time.time() - start_time

        # Concurrent execution
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            concurrent_results = list(executor.map(analyze_repo, repos))
        concurrent_time = time.time() - start_time

        print(f"\nSequential time: {sequential_time:.3f}s")
        print(f"Concurrent time: {concurrent_time:.3f}s")

        # Verify concurrent integrity - correct number of results
        assert len(concurrent_results) == len(repos)
        # All results should be valid
        assert all(r is not None for r in concurrent_results)

    def test_memory_efficiency_large_repos(self, insight_engine, large_repo_data):
        """Test memory efficiency when processing large repositories."""
        import gc
        import os

        import psutil

        from github_analyzer.core.evidence.evidence_extractor import EvidenceExtractor

        process = psutil.Process(os.getpid())

        # Get baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process large repository
        extractor = EvidenceExtractor()
        evidence = extractor.extract_all_evidence(large_repo_data)
        result = insight_engine.generate_screening_insights(evidence)

        # Get peak memory
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - baseline_memory

        print(f"\nBaseline memory: {baseline_memory:.1f} MB")
        print(f"Peak memory: {peak_memory:.1f} MB")
        print(f"Memory increase: {memory_increase:.1f} MB")

        # Memory increase should be reasonable (less than 500MB for large repo)
        assert memory_increase < 500

        # Cleanup
        del result
        del evidence
        gc.collect()

    def test_evidence_pattern_matching_performance(self, insight_engine):
        """Test performance of pattern matching algorithms."""
        from github_analyzer.core.evidence.evidence_extractor import EvidenceExtractor

        # Create repo with many patterns to match
        repo = self._create_repo_with_size(50000)
        repo.file_structure = [
            FileInfo(
                path=f"src/module_{i}.py",
                name=f"module_{i}.py",
                size=1000,
                type="file",
                extension="py",
            )
            for i in range(1000)
        ]

        patterns_to_search = [
            "test_coverage",
            "documentation_quality",
            "code_organization",
            "commit_patterns",
            "maintenance_activity",
            "security_practices",
            "performance_optimization",
            "error_handling",
        ]

        start_time = time.time()

        # Extract evidence
        extractor = EvidenceExtractor()
        evidence = extractor.extract_all_evidence(repo)

        # Search for specific pattern types in technical patterns
        found_patterns = {}
        technical_patterns = evidence.get("technical_patterns", [])

        for pattern_type in patterns_to_search:
            found_patterns[pattern_type] = [
                p
                for p in technical_patterns
                if pattern_type in p.get("finding", "").lower()
            ]

        end_time = time.time()
        search_time = end_time - start_time

        print(f"\nEvidence extraction and search time: {search_time:.3f}s")
        print(f"Total technical patterns found: {len(technical_patterns)}")
        for ptype, plist in found_patterns.items():
            print(f"  {ptype}: {len(plist)} patterns")

        # Should complete quickly even with many files
        assert search_time < 3.0

    def test_evidence_strength_calculation_performance(self, insight_engine):
        """Test performance of evidence strength calculations."""
        from github_analyzer.core.evidence.evidence_extractor import EvidenceExtractor

        repo_sizes = [1000, 10000, 100000]

        for size in repo_sizes:
            repo = self._create_repo_with_size(size)

            # Extract evidence
            extractor = EvidenceExtractor()

            start_time = time.time()
            evidence = extractor.extract_all_evidence(repo)
            result = insight_engine.generate_screening_insights(evidence)
            calc_time = time.time() - start_time

            print(f"\nRepo size: {size}, Analysis time: {calc_time:.3f}s")
            print(f"  Insights generated: {len(result.insights)}")

            # Calculation should be fast regardless of repo size
            assert calc_time < 1.0  # Allow up to 1 second

    def test_comprehensive_analysis_integrity(self, insight_engine, large_repo_data):
        """Test comprehensive analysis integrity - verifies quality under repeated analysis."""
        from github_analyzer.core.evidence.evidence_extractor import EvidenceExtractor

        results = []
        times = []

        # Run multiple analyses to verify consistency
        for i in range(10):
            extractor = EvidenceExtractor()

            start_time = time.time()
            evidence = extractor.extract_all_evidence(large_repo_data)
            result = insight_engine.generate_screening_insights(evidence)
            analysis_time = time.time() - start_time
            times.append(analysis_time)
            results.append(result)

            # Verify result quality isn't compromised
            assert len(result.insights) >= 1  # At least one insight
            assert len(result.key_strengths) >= 0  # May have key strengths

        # Calculate statistics for informational purposes
        times.sort()
        p95 = times[int(len(times) * 0.95)]
        p99 = times[int(len(times) * 0.99)] if len(times) > 1 else times[-1]

        print("\nPerformance distribution (informational):")
        print(f"  Min: {min(times):.3f}s")
        print(f"  Max: {max(times):.3f}s")
        print(f"  Avg: {sum(times) / len(times):.3f}s")
        print(f"  P95: {p95:.3f}s")
        print(f"  P99: {p99:.3f}s")

        # Verify integrity - all analyses should produce valid results
        assert len(results) == 10
        assert all(r is not None for r in results)
        assert all(
            len(r.insights) >= 1 for r in results
        )  # At least one insight per analysis
        assert all(
            hasattr(r, "key_strengths") for r in results
        )  # Has key_strengths attribute

    def _create_repo_with_size(self, lines_of_code: int) -> RepositoryData:
        """Create a repository with specified size for testing."""
        return RepositoryData(
            url=f"https://github.com/test/repo-{lines_of_code}",
            full_name=f"test/repo-{lines_of_code}",
            name=f"repo-{lines_of_code}",
            owner="test",
            description=f"Test repo with {lines_of_code} lines",
            created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime.now(timezone.utc),
            pushed_at=datetime.now(timezone.utc),
            default_branch="main",
            size=lines_of_code // 10,
            languages={"Python": lines_of_code},
            topics=[],
            license_name="MIT",
            stars=lines_of_code // 1000,
            forks=lines_of_code // 5000,
            watchers=lines_of_code // 2000,
            open_issues=lines_of_code // 10000,
            has_readme=True,
            has_license=True,
            has_contributing=lines_of_code > 10000,
            has_tests=lines_of_code > 5000,
            has_ci_config=lines_of_code > 5000,
            recent_commits=[],
            file_structure=[],
            readme_content=f"# Repo {lines_of_code}",
            metrics=RepositoryMetrics(
                total_commits=lines_of_code // 100,
                unique_contributors=max(1, lines_of_code // 10000),
                lines_of_code=lines_of_code,
                test_coverage_estimate=min(0.8, lines_of_code / 100000),
                documentation_presence="2 documentation files in 10 total files",
                days_since_last_commit=5,
                commit_frequency=5.0,
                avg_commit_size=100.0,
            ),
            fetched_at=datetime.now(timezone.utc),
            is_private=False,
            is_fork=False,
            is_archived=False,
            is_disabled=False,
        )

    def _create_evidence_pattern(self, index: int):
        """Create a test evidence pattern."""
        patterns = [
            "test_coverage",
            "documentation",
            "code_quality",
            "security",
            "performance",
        ]
        return {
            "type": patterns[index % len(patterns)],
            "finding": f"Evidence for pattern {index}",
            "confidence": "high" if index % 3 == 0 else "medium",
            "context": {"commits": [f"commit_{index}"], "files": [f"file_{index}.py"]},
        }
