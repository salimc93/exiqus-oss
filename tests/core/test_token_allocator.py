"""
Tests for TokenAllocator - intelligent token allocation for Scale+ tier.
"""

from github_analyzer.core.token_allocator import RepositoryComplexity, TokenAllocator


class TestRepositoryComplexityCalculation:
    """Test repository complexity calculation."""

    def test_calculate_simple_repository_complexity(self) -> None:
        """Test complexity calculation for a simple repository."""
        allocator = TokenAllocator()

        repo_data = {
            "total_files": 15,
            "total_lines": 2000,
            "languages": {"Python": 80, "JavaScript": 20},
            "file_paths": ["main.py", "utils.py", "test_main.py"],
            "commit_count": 25,
            "contributor_count": 2,
        }

        complexity = allocator.calculate_repository_complexity(repo_data)

        assert complexity.total_files == 15
        assert complexity.total_lines == 2000
        assert complexity.languages_count == 2
        assert complexity.has_tests is True  # has test_main.py
        assert complexity.has_ci_cd is False
        assert complexity.commit_count == 25
        assert complexity.contributor_count == 2
        assert abs(complexity.avg_file_size - 133.33) < 0.01

    def test_calculate_complex_repository_complexity(self) -> None:
        """Test complexity calculation for a complex repository."""
        allocator = TokenAllocator()

        repo_data = {
            "total_files": 2500,
            "total_lines": 250000,
            "languages": {
                "TypeScript": 40,
                "Python": 25,
                "Go": 15,
                "Rust": 10,
                "SQL": 10,
            },
            "file_paths": [
                "src/main.ts",
                "tests/unit.spec.ts",
                ".github/workflows/ci.yml",
                "backend/api.py",
                "infrastructure/docker-compose.yml",
            ],
            "commit_count": 8000,
            "contributor_count": 75,
        }

        complexity = allocator.calculate_repository_complexity(repo_data)

        assert complexity.total_files == 2500
        assert complexity.total_lines == 250000
        assert complexity.languages_count == 5
        assert complexity.has_tests is True
        assert complexity.has_ci_cd is True  # has .github/workflows
        assert complexity.commit_count == 8000
        assert complexity.contributor_count == 75
        assert abs(complexity.avg_file_size - 100.0) < 0.01

    def test_detect_ci_cd_patterns(self) -> None:
        """Test CI/CD detection across different platforms."""
        allocator = TokenAllocator()

        test_cases = [
            ([".github/workflows/ci.yml"], True),
            ([".gitlab-ci.yml"], True),
            ([".circleci/config.yml"], True),
            (["Jenkinsfile"], True),
            ([".travis.yml"], True),
            (["src/main.py", "README.md"], False),
        ]

        for file_paths, expected_ci_cd in test_cases:
            repo_data = {
                "total_files": 10,
                "total_lines": 1000,
                "languages": {"Python": 100},
                "file_paths": file_paths,
                "commit_count": 50,
                "contributor_count": 1,
            }

            complexity = allocator.calculate_repository_complexity(repo_data)
            assert complexity.has_ci_cd == expected_ci_cd

    def test_detect_test_patterns(self) -> None:
        """Test test detection across different naming patterns."""
        allocator = TokenAllocator()

        test_cases = [
            (["test_main.py"], True),
            (["main.test.js"], True),
            (["spec/helper.rb"], True),
            (["tests/unit/api.py"], True),
            (["src/main.py", "utils.py"], False),
        ]

        for file_paths, expected_tests in test_cases:
            repo_data = {
                "total_files": 10,
                "total_lines": 1000,
                "languages": {"Python": 100},
                "file_paths": file_paths,
                "commit_count": 50,
                "contributor_count": 1,
            }

            complexity = allocator.calculate_repository_complexity(repo_data)
            assert complexity.has_tests == expected_tests


class TestTokenAllocation:
    """Test intelligent token allocation logic."""

    def test_allocate_tokens_non_scale_plus_tiers(self) -> None:
        """Test standard token allocation for non-Scale+ tiers."""
        allocator = TokenAllocator()
        complexity = RepositoryComplexity(
            total_files=100,
            total_lines=10000,
            languages_count=3,
            has_tests=True,
            has_ci_cd=True,
            commit_count=500,
            contributor_count=5,
            avg_file_size=100.0,
        )

        test_cases = [
            ("free", 4096),
            ("basic", 8192),
            ("professional", 8192),
            ("enterprise", 16384),
            ("scale", 16384),
        ]

        for tier, expected_tokens in test_cases:
            tokens, reason, cost = allocator.allocate_tokens(complexity, tier)
            assert tokens == expected_tokens
            assert reason == "Standard allocation for tier"
            assert isinstance(cost, float)
            assert cost > 0

    def test_allocate_tokens_scale_plus_mega_repo_rule(self) -> None:
        """Test Scale+ mega-repo rule (Rule 1)."""
        allocator = TokenAllocator()

        # Test with >2000 files
        complexity = RepositoryComplexity(
            total_files=2500,
            total_lines=150000,
            languages_count=3,
            has_tests=True,
            has_ci_cd=True,
            commit_count=1000,
            contributor_count=10,
            avg_file_size=60.0,
        )

        tokens, reason, cost = allocator.allocate_tokens(complexity, "scale_plus")
        assert tokens == 32768  # TOKEN_TIERS["large"]
        assert "Very large codebase requires maximum analysis depth" in reason

        # Test with >200,000 lines
        complexity = RepositoryComplexity(
            total_files=1500,
            total_lines=250000,
            languages_count=2,
            has_tests=False,
            has_ci_cd=False,
            commit_count=500,
            contributor_count=5,
            avg_file_size=166.67,
        )

        tokens, reason, cost = allocator.allocate_tokens(complexity, "scale_plus")
        assert tokens == 32768
        assert "Very large codebase requires maximum analysis depth" in reason

    def test_allocate_tokens_scale_plus_high_collaboration_rule(self) -> None:
        """Test Scale+ high-collaboration rule (Rule 2)."""
        allocator = TokenAllocator()

        complexity = RepositoryComplexity(
            total_files=800,
            total_lines=80000,
            languages_count=3,
            has_tests=True,
            has_ci_cd=True,
            commit_count=6000,  # >5000
            contributor_count=60,  # >50
            avg_file_size=100.0,
        )

        tokens, reason, cost = allocator.allocate_tokens(complexity, "scale_plus")
        assert tokens == 32768
        assert (
            "High contributor count and deep history suggests complex collaboration patterns"
            in reason
        )

    def test_allocate_tokens_scale_plus_polyglot_rule(self) -> None:
        """Test Scale+ polyglot rule (Rule 3)."""
        allocator = TokenAllocator()

        complexity = RepositoryComplexity(
            total_files=300,
            total_lines=30000,
            languages_count=5,  # >=5
            has_tests=True,
            has_ci_cd=False,
            commit_count=200,
            contributor_count=8,
            avg_file_size=100.0,
        )

        tokens, reason, cost = allocator.allocate_tokens(complexity, "scale_plus")
        assert tokens == 16384  # TOKEN_TIERS["medium"]
        assert "Polyglot repository with multiple significant languages" in reason

    def test_allocate_tokens_scale_plus_trivial_rule(self) -> None:
        """Test Scale+ trivial repo rule (Rule 4)."""
        allocator = TokenAllocator()

        complexity = RepositoryComplexity(
            total_files=15,  # <20
            total_lines=800,
            languages_count=1,
            has_tests=False,
            has_ci_cd=False,
            commit_count=25,  # <50
            contributor_count=1,
            avg_file_size=53.33,
        )

        tokens, reason, cost = allocator.allocate_tokens(complexity, "scale_plus")
        assert tokens == 8192  # TOKEN_TIERS["small"]
        assert "Small, simple repository with limited history" in reason

    def test_allocate_tokens_scale_plus_default_rule(self) -> None:
        """Test Scale+ default rule for standard repos."""
        allocator = TokenAllocator()

        complexity = RepositoryComplexity(
            total_files=150,
            total_lines=15000,
            languages_count=3,
            has_tests=True,
            has_ci_cd=True,
            commit_count=300,
            contributor_count=8,
            avg_file_size=100.0,
        )

        tokens, reason, cost = allocator.allocate_tokens(complexity, "scale_plus")
        assert tokens == 16384  # TOKEN_TIERS["medium"]
        assert "Standard repository complexity" in reason


class TestCostEstimation:
    """Test cost estimation functionality."""

    def test_estimate_cost_calculation(self) -> None:
        """Test cost estimation accuracy."""
        allocator = TokenAllocator()

        # Test small tier (8192 tokens)
        cost = allocator._estimate_cost(8192)
        expected_input_cost = (8192 * 2 / 1000) * 0.0015  # Input tokens
        expected_output_cost = (8192 / 1000) * 0.0075  # Output tokens
        expected_total = expected_input_cost + expected_output_cost
        assert cost == round(expected_total, 4)

        # Test large tier (32768 tokens)
        cost = allocator._estimate_cost(32768)
        expected_input_cost = (32768 * 2 / 1000) * 0.0015
        expected_output_cost = (32768 / 1000) * 0.0075
        expected_total = expected_input_cost + expected_output_cost
        assert cost == round(expected_total, 4)

    def test_cost_increases_with_token_allocation(self) -> None:
        """Test that cost increases with higher token allocation."""
        allocator = TokenAllocator()

        small_cost = allocator._estimate_cost(8192)
        medium_cost = allocator._estimate_cost(16384)
        large_cost = allocator._estimate_cost(32768)

        assert small_cost < medium_cost < large_cost


class TestAdminMonitoring:
    """Test admin monitoring functionality."""

    def test_monitor_usage_no_alerts(self) -> None:
        """Test monitoring with normal usage - no alerts."""
        allocator = TokenAllocator()

        alerts = allocator.monitor_usage_for_admin("user123", 25.0, 200.0)
        assert alerts is None

    def test_monitor_usage_warning_alert(self) -> None:
        """Test monitoring with warning-level usage."""
        allocator = TokenAllocator()

        alerts = allocator.monitor_usage_for_admin("user123", 75.0, 300.0)
        assert alerts is not None
        assert len(alerts) == 1
        assert alerts[0]["level"] == "warning"
        assert "daily cost: $75.00" in alerts[0]["message"]

    def test_monitor_usage_urgent_alert(self) -> None:
        """Test monitoring with urgent-level usage."""
        allocator = TokenAllocator()

        alerts = allocator.monitor_usage_for_admin("user123", 150.0, 600.0)
        assert alerts is not None
        assert len(alerts) == 3  # warning, urgent, and info

        levels = [alert["level"] for alert in alerts]
        assert "warning" in levels
        assert "urgent" in levels
        assert "info" in levels  # Monthly cost >500

    def test_monitor_usage_upsell_opportunity(self) -> None:
        """Test monitoring identifies upsell opportunities."""
        allocator = TokenAllocator()

        alerts = allocator.monitor_usage_for_admin("user123", 200.0, 800.0)
        assert alerts is not None

        info_alerts = [a for a in alerts if a["level"] == "info"]
        assert len(info_alerts) == 1
        assert "Scale++ tier" in info_alerts[0]["message"]


class TestBatchProcessingStrategy:
    """Test batch processing strategy recommendations."""

    def test_get_batch_processing_strategy_empty_repos(self) -> None:
        """Test strategy with no repositories."""
        allocator = TokenAllocator()

        strategy = allocator.get_batch_processing_strategy([])
        assert strategy["strategy"] == "none"
        assert "No repositories" in strategy["reason"]

    def test_get_batch_processing_strategy_large_repos(self) -> None:
        """Test strategy with mostly large repositories."""
        allocator = TokenAllocator()

        # Create repos that trigger large allocation
        large_repos = [
            {
                "total_files": 2500,
                "total_lines": 250000,
                "languages": {"TypeScript": 60, "Python": 40},
                "file_paths": ["src/main.ts"],
                "commit_count": 1000,
                "contributor_count": 20,
            }
            for _ in range(8)
        ]

        strategy = allocator.get_batch_processing_strategy(large_repos)
        assert strategy["strategy"] == "sequential"
        assert strategy["chunk_size"] == 3
        assert "large repositories" in strategy["reason"]

    def test_get_batch_processing_strategy_trivial_repos(self) -> None:
        """Test strategy with mostly trivial repositories."""
        allocator = TokenAllocator()

        # Create repos that trigger small allocation
        trivial_repos = [
            {
                "total_files": 10,
                "total_lines": 500,
                "languages": {"Python": 100},
                "file_paths": ["main.py"],
                "commit_count": 20,
                "contributor_count": 1,
            }
            for _ in range(10)
        ]

        strategy = allocator.get_batch_processing_strategy(trivial_repos)
        assert strategy["strategy"] == "parallel"
        assert strategy["chunk_size"] == 15
        assert "small repositories" in strategy["reason"]

    def test_get_batch_processing_strategy_mixed_repos(self) -> None:
        """Test strategy with mixed repository sizes."""
        allocator = TokenAllocator()

        mixed_repos = [
            # Some large repos
            {
                "total_files": 1500,
                "total_lines": 150000,
                "languages": {"TypeScript": 80, "Python": 20},
                "file_paths": ["src/main.ts"],
                "commit_count": 2000,
                "contributor_count": 30,
            },
            # Some medium repos
            {
                "total_files": 200,
                "total_lines": 20000,
                "languages": {"Python": 60, "JavaScript": 40},
                "file_paths": ["app.py", "script.js"],
                "commit_count": 500,
                "contributor_count": 8,
            },
        ]

        strategy = allocator.get_batch_processing_strategy(mixed_repos)
        assert strategy["strategy"] == "adaptive"
        assert strategy["chunk_size"] == 5
        assert "Mixed repository sizes" in strategy["reason"]
