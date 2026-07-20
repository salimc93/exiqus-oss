"""
Unit tests for the MarkdownParser module.

Tests the parsing of structured Markdown AI responses with validation
and error recovery capabilities.
"""

from github_analyzer.ai.markdown_parser import (
    MarkdownParser,
    create_markdown_parser,
    get_markdown_instructions,
)


class TestMarkdownParser:
    """Test suite for MarkdownParser functionality."""

    def test_parser_initialization(self):
        """Test parser creates correctly."""
        parser = create_markdown_parser()
        assert isinstance(parser, MarkdownParser)
        assert parser.parse_attempts == 0
        assert parser.last_error is None

    def test_get_markdown_instructions(self):
        """Test markdown instruction generation."""
        instructions = get_markdown_instructions(
            insight_count=5, question_count=3, recommendation_count=2
        )
        assert "Generate AT LEAST 5 insights" in instructions
        assert "Generate AT LEAST 3 questions" in instructions
        assert "Generate AT LEAST 2 recommendations" in instructions
        assert "# Summary" in instructions
        assert "# Insights" in instructions
        assert "# Questions" in instructions

    def test_parse_valid_markdown(self):
        """Test parsing of valid markdown structure."""
        parser = create_markdown_parser()

        valid_markdown = """
# Summary
This is an executive summary of the repository analysis.

# Insights

## Insight 1
**Title:** Strong Testing Practices
**Category:** technical_skills
**Description:** The repository shows comprehensive test coverage with unit and integration tests.
**Evidence:** Found 45 test files covering 80% of the codebase
**Confidence:** high
**Impact:** positive

## Insight 2
**Title:** Modern Architecture
**Category:** technical_skills
**Description:** Clean separation of concerns with MVC pattern.
**Evidence:** Well-structured folders for models, views, and controllers
**Confidence:** high
**Impact:** positive

# Questions

## Question 1
**Question:** How do you approach test-driven development?
**Purpose:** Understanding testing philosophy
**Context:** Strong test coverage observed
**Category:** technical

## Question 2
**Question:** Describe your experience with microservices?
**Purpose:** Architectural understanding
**Context:** Modular code structure
**Category:** technical

# Recommendations

## Recommendation 1
**Recommendation:** Proceed with technical interview
**Priority:** high
**Rationale:** Strong technical foundation evident

# Areas to Explore
- Testing methodologies and TDD approach
- Experience with CI/CD pipelines
- Team collaboration practices

# Data Limitations
- Cannot assess soft skills from code
- Limited visibility into team dynamics

# Confidence Explanation
High confidence based on comprehensive code samples and clear patterns.
"""

        result, error = parser.parse(valid_markdown)

        assert error == ""
        assert result is not None
        assert (
            result["summary"]
            == "This is an executive summary of the repository analysis."
        )
        # API response wraps insights in a list with evidence as a list
        assert len(result["insights"]) >= 1  # At least one insight parsed
        assert len(result["questions"]) >= 1  # At least one question parsed
        assert len(result["recommendations"]) == 1
        assert len(result["areas_to_explore"]) == 3
        assert len(result["data_limitations"]) == 2

    def test_parse_insights_section(self):
        """Test parsing of insights section specifically."""
        parser = MarkdownParser()

        insights_text = """
## Insight 1
**Title:** Bug Fix Methodology
**Category:** problem_solving
**Description:** Systematic approach to bug fixes with detailed commit messages.
**Evidence:** 15 bug fix commits with thorough descriptions
**Confidence:** high
**Impact:** positive

## Insight 2
**Title:** API Documentation Standards
**Category:** professional_practices
**Description:** Comprehensive API documentation maintained.
**Evidence:** All endpoints documented with examples
**Confidence:** medium
**Impact:** positive
"""

        insights = parser._parse_insights(insights_text)

        assert len(insights) == 2
        assert insights[0]["title"] == "Bug Fix Methodology"
        assert insights[0]["category"] == "problem_solving"
        assert insights[1]["title"] == "API Documentation Standards"
        assert insights[1]["confidence"] == "medium"

    def test_parse_questions_section(self):
        """Test parsing of questions section."""
        parser = MarkdownParser()

        questions_text = """
## Question 1
**Question:** Walk me through your debugging process?
**Purpose:** Understanding problem-solving approach
**Context:** Multiple bug fixes observed
**Category:** behavioral

## Question 2
**Question:** How do you ensure code quality?
**Purpose:** Quality practices assessment
**Context:** Clean code structure
**Category:** technical
"""

        questions = parser._parse_questions(questions_text)

        assert len(questions) == 2
        assert questions[0]["question"] == "Walk me through your debugging process?"
        assert questions[0]["category"] == "behavioral"
        assert questions[1]["purpose"] == "Quality practices assessment"

    def test_parse_recommendations_section(self):
        """Test parsing of recommendations section."""
        parser = MarkdownParser()

        recommendations_text = """
## Recommendation 1
**Recommendation:** Focus on system design questions
**Priority:** high
**Rationale:** Strong coding skills but need to assess architecture

## Recommendation 2
**Recommendation:** Explore team collaboration experience
**Priority:** medium
**Rationale:** Solo project work observed
"""

        recommendations = parser._parse_recommendations(recommendations_text)

        assert len(recommendations) == 2
        assert (
            recommendations[0]["recommendation"] == "Focus on system design questions"
        )
        assert recommendations[0]["priority"] == "high"
        assert recommendations[1]["rationale"] == "Solo project work observed"

    def test_parse_bullet_lists(self):
        """Test parsing of bullet point lists."""
        parser = MarkdownParser()

        bullet_text = """
- First item in the list
- Second item with more detail
- Third item
"""

        items = parser._parse_bullet_list(bullet_text)

        assert len(items) == 3
        assert items[0] == "First item in the list"
        assert items[1] == "Second item with more detail"

    def test_validate_counts(self):
        """Test count validation."""
        parser = MarkdownParser()

        parsed_data = {
            "insights": [1, 2, 3],
            "questions": [1, 2],
            "recommendations": [1],
        }

        # Should pass with correct counts
        error = parser._validate_counts(
            parsed_data, {"insights": 3, "questions": 2, "recommendations": 1}
        )
        assert error is None

        # Should fail with incorrect counts
        error = parser._validate_counts(
            parsed_data, {"insights": 5, "questions": 3, "recommendations": 2}
        )
        assert error is not None
        assert "insights: expected 5, got 3" in error

    def test_markdown_to_api_response(self):
        """Test conversion to API-compatible format."""
        parser = MarkdownParser()

        parsed_data = {
            "summary": "Test summary",
            "insights": [
                {
                    "category": "technical_skills",
                    "title": "Strong Testing",
                    "description": "Good test coverage",
                    "evidence": "45 test files",
                    "confidence": "high",
                    "impact": "positive",
                }
            ],
            "questions": [
                {
                    "question": "Test question?",
                    "purpose": "Test purpose",
                    "context": "Test context",
                    "category": "technical",
                }
            ],
            "recommendations": [
                {
                    "recommendation": "Test recommendation",
                    "priority": "high",
                    "rationale": "Test rationale",
                }
            ],
            "areas_to_explore": ["Area 1", "Area 2"],
            "data_limitations": ["Limitation 1"],
            "confidence_explanation": "High confidence",
        }

        api_response = parser._markdown_to_api_response(parsed_data)

        assert api_response["summary"] == "Test summary"
        assert len(api_response["insights"]) == 1
        assert api_response["insights"][0]["title"] == "Strong Testing"
        assert isinstance(api_response["insights"][0]["evidence"], list)
        assert len(api_response["questions"]) == 1
        assert len(api_response["recommendations"]) == 1
        assert (
            len(api_response["key_strengths"]) == 1
        )  # Extracted from positive insights
        assert api_response["overall_impression"] == "Test summary"

    def test_parse_malformed_markdown(self):
        """Test parsing handles malformed markdown gracefully."""
        parser = create_markdown_parser()

        malformed_markdown = """
# Summary
Summary text here

# Insights
This section is malformed without proper insight structure

# Questions
Also malformed

# Areas to Explore
- Item 1
"""

        result, error = parser.parse(malformed_markdown)

        # Should still parse what it can
        assert result is not None
        assert result["summary"] == "Summary text here"
        assert len(result["insights"]) == 0  # No valid insights found
        assert len(result["areas_to_explore"]) == 1

    def test_parse_empty_input(self):
        """Test parsing handles empty input."""
        parser = create_markdown_parser()

        result, error = parser.parse("")

        assert error != ""
        assert result is None

    def test_parse_with_multiline_fields(self):
        """Test parsing handles multiline field values."""
        parser = create_markdown_parser()

        markdown_with_multiline = """
# Summary
This is a multiline
summary that spans
multiple lines.

# Insights

## Insight 1
**Title:** Multiline Test
**Category:** technical_skills
**Description:** This is a description
that spans multiple lines
with lots of detail.
**Evidence:** Evidence also
spans lines
**Confidence:** high
**Impact:** positive

# Questions

# Recommendations

# Areas to Explore
- First area

# Data Limitations
- First limitation

# Confidence Explanation
Explanation here.
"""

        result, error = parser.parse(markdown_with_multiline)

        assert error == ""
        assert "This is a multiline" in result["summary"]
        assert "multiple lines" in result["summary"]
        assert len(result["insights"]) == 1
        assert "spans multiple lines" in result["insights"][0]["description"]
