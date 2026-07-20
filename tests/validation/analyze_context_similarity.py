#!/usr/bin/env python3
"""
Analyze similarity between different context outputs.
Helps identify which contexts are most differentiated and which need improvement.
"""

import json
import os
from difflib import SequenceMatcher
from typing import Dict, List, Set

import numpy as np
from pathlib import Path



VALIDATION_DIR = Path(__file__).resolve().parent
class ContextSimilarityAnalyzer:
    """Analyze similarity between different context outputs."""

    def __init__(self):
        self.results = {}

    def load_results(self, results_file: str = None):
        """Load test results from file or recent tests."""
        if results_file and os.path.exists(results_file):
            with open(results_file, "r") as f:
                self.results = json.load(f)
        else:
            # Load most recent results
            validation_dir = str(VALIDATION_DIR)
            json_files = [f for f in os.listdir(validation_dir) if f.endswith(".json")]
            if json_files:
                latest = max(
                    json_files,
                    key=lambda f: os.path.getmtime(os.path.join(validation_dir, f)),
                )
                with open(os.path.join(validation_dir, latest), "r") as f:
                    self.results = json.load(f)

    def calculate_question_similarity(
        self, questions1: List[str], questions2: List[str]
    ) -> float:
        """Calculate similarity between two sets of questions."""
        if not questions1 or not questions2:
            return 0.0

        # Convert to lowercase for comparison
        q1_lower = [q.lower() for q in questions1]
        q2_lower = [q.lower() for q in questions2]

        # Calculate average similarity
        similarities = []

        for q1 in q1_lower:
            max_sim = 0
            for q2 in q2_lower:
                sim = SequenceMatcher(None, q1, q2).ratio()
                max_sim = max(max_sim, sim)
            similarities.append(max_sim)

        return sum(similarities) / len(similarities) if similarities else 0

    def extract_key_terms(self, questions: List[str]) -> Set[str]:
        """Extract key terms from questions."""
        # Key technical and behavioral terms to look for
        key_terms = {
            # Technical terms
            "architecture",
            "performance",
            "scalability",
            "testing",
            "security",
            "database",
            "api",
            "microservices",
            "deployment",
            "monitoring",
            # Process terms
            "agile",
            "scrum",
            "kanban",
            "ci/cd",
            "devops",
            "workflow",
            "documentation",
            "code review",
            "standards",
            "best practices",
            # Behavioral terms
            "team",
            "collaborate",
            "communicate",
            "leadership",
            "mentor",
            "conflict",
            "feedback",
            "learning",
            "growth",
            "culture",
            # Context-specific terms
            "startup",
            "enterprise",
            "client",
            "deadline",
            "community",
            "open source",
            "contributor",
            "maintainer",
            "volunteer",
            "compliance",
            "regulation",
            "process",
            "governance",
        }

        found_terms = set()

        for question in questions:
            q_lower = question.lower()
            for term in key_terms:
                if term in q_lower:
                    found_terms.add(term)

        return found_terms

    def analyze_theme_overlap(
        self, themes1: List[str], themes2: List[str]
    ) -> Dict[str, any]:
        """Analyze overlap between themes."""
        set1 = set(themes1)
        set2 = set(themes2)

        overlap = set1.intersection(set2)
        unique1 = set1 - set2
        unique2 = set2 - set1

        total = len(set1.union(set2))
        overlap_ratio = len(overlap) / total if total > 0 else 0

        return {
            "overlap": list(overlap),
            "unique_to_first": list(unique1),
            "unique_to_second": list(unique2),
            "overlap_ratio": overlap_ratio,
            "jaccard_similarity": (
                len(overlap) / len(set1.union(set2)) if set1.union(set2) else 0
            ),
        }

    def analyze_metric_distribution_similarity(self, dist1: Dict, dist2: Dict) -> float:
        """Calculate similarity between metric distributions."""
        categories = set(dist1.keys()).union(set(dist2.keys()))

        if not categories:
            return 0.0

        # Calculate cosine similarity
        vec1 = [dist1.get(cat, 0) for cat in categories]
        vec2 = [dist2.get(cat, 0) for cat in categories]

        if sum(vec1) == 0 or sum(vec2) == 0:
            return 0.0

        # Normalize
        total1 = sum(vec1)
        total2 = sum(vec2)
        vec1_norm = [v / total1 for v in vec1]
        vec2_norm = [v / total2 for v in vec2]

        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(vec1_norm, vec2_norm))

        return dot_product

    def generate_similarity_matrix(
        self, contexts: List[str], tier: str
    ) -> Dict[str, any]:
        """Generate similarity matrix for contexts."""
        n = len(contexts)

        # Initialize matrices
        question_sim_matrix = np.zeros((n, n))
        theme_sim_matrix = np.zeros((n, n))
        metric_sim_matrix = np.zeros((n, n))

        # Get results for each context
        context_results = {}
        for result in self.results:
            if isinstance(result, dict) and result.get("tier") == tier:
                context = result.get("context")
                if context in contexts:
                    context_results[context] = result

        # Calculate similarities
        for i, ctx1 in enumerate(contexts):
            for j, ctx2 in enumerate(contexts):
                if i == j:
                    # Same context = 100% similar
                    question_sim_matrix[i][j] = 1.0
                    theme_sim_matrix[i][j] = 1.0
                    metric_sim_matrix[i][j] = 1.0
                    continue

                if ctx1 in context_results and ctx2 in context_results:
                    res1 = context_results[ctx1]
                    res2 = context_results[ctx2]

                    # Question similarity
                    q1 = res1.get("top_questions", [])
                    q2 = res2.get("top_questions", [])
                    question_sim_matrix[i][j] = self.calculate_question_similarity(
                        q1, q2
                    )

                    # Theme similarity
                    themes1 = res1.get("question_themes", [])
                    themes2 = res2.get("question_themes", [])
                    theme_analysis = self.analyze_theme_overlap(themes1, themes2)
                    theme_sim_matrix[i][j] = theme_analysis["jaccard_similarity"]

                    # Metric distribution similarity
                    if "metric_analysis" in res1 and "metric_analysis" in res2:
                        dist1 = res1["metric_analysis"].get("distribution", {})
                        dist2 = res2["metric_analysis"].get("distribution", {})
                        metric_sim_matrix[i][j] = (
                            self.analyze_metric_distribution_similarity(dist1, dist2)
                        )

        return {
            "contexts": contexts,
            "question_similarity": question_sim_matrix.tolist(),
            "theme_similarity": theme_sim_matrix.tolist(),
            "metric_similarity": metric_sim_matrix.tolist(),
            "average_similarity": {
                "questions": np.mean(question_sim_matrix[np.triu_indices(n, k=1)]),
                "themes": np.mean(theme_sim_matrix[np.triu_indices(n, k=1)]),
                "metrics": np.mean(metric_sim_matrix[np.triu_indices(n, k=1)]),
            },
        }

    def find_most_differentiated(self, similarity_matrix: Dict) -> Dict[str, any]:
        """Find most and least differentiated context pairs."""
        contexts = similarity_matrix["contexts"]
        n = len(contexts)

        # Combine all similarity measures
        combined_sim = np.zeros((n, n))

        q_sim = np.array(similarity_matrix["question_similarity"])
        t_sim = np.array(similarity_matrix["theme_similarity"])
        m_sim = np.array(similarity_matrix["metric_similarity"])

        # Weight: questions 50%, themes 30%, metrics 20%
        combined_sim = 0.5 * q_sim + 0.3 * t_sim + 0.2 * m_sim

        # Find most different pairs (lowest similarity)
        most_different_pairs = []
        least_different_pairs = []

        for i in range(n):
            for j in range(i + 1, n):
                similarity = combined_sim[i][j]
                pair = (contexts[i], contexts[j], similarity)

                if similarity < 0.3:  # Less than 30% similar
                    most_different_pairs.append(pair)
                elif similarity > 0.7:  # More than 70% similar
                    least_different_pairs.append(pair)

        # Sort by similarity
        most_different_pairs.sort(key=lambda x: x[2])
        least_different_pairs.sort(key=lambda x: x[2], reverse=True)

        return {
            "most_differentiated": most_different_pairs[:5],
            "least_differentiated": least_different_pairs[:5],
            "differentiation_score": 1
            - similarity_matrix["average_similarity"]["questions"],
        }

    def generate_report(self):
        """Generate comprehensive similarity report."""
        print("\n" + "=" * 80)
        print("📊 CONTEXT SIMILARITY ANALYSIS REPORT")
        print("=" * 80)

        contexts = ["startup", "enterprise", "agency", "open_source"]
        tiers = ["free", "starter", "growth", "scale"]

        # Analyze each tier
        for tier in tiers:
            print(f"\n🏷️  {tier.upper()} TIER ANALYSIS")
            print("-" * 60)

            similarity_matrix = self.generate_similarity_matrix(contexts, tier)
            differentiation = self.find_most_differentiated(similarity_matrix)

            # Display average similarities
            avg_sim = similarity_matrix["average_similarity"]
            print("\n📈 Average Similarity Scores:")
            print(f"  • Questions: {avg_sim['questions']:.1%}")
            print(f"  • Themes: {avg_sim['themes']:.1%}")
            print(f"  • Metrics: {avg_sim['metrics']:.1%}")
            print(
                f"  • Differentiation Score: {differentiation['differentiation_score']:.1%}"
            )

            # Most differentiated pairs
            print("\n✅ Most Differentiated Context Pairs:")
            for ctx1, ctx2, sim in differentiation["most_differentiated"][:3]:
                print(f"  • {ctx1} vs {ctx2}: {(1-sim)*100:.0f}% different")

            # Least differentiated pairs
            if differentiation["least_differentiated"]:
                print("\n⚠️  Least Differentiated Context Pairs:")
                for ctx1, ctx2, sim in differentiation["least_differentiated"][:3]:
                    print(f"  • {ctx1} vs {ctx2}: {sim*100:.0f}% similar")

            # Detailed matrix
            print("\n📊 Similarity Matrix (Questions):")
            print(f"{'':12}", end="")
            for ctx in contexts:
                print(f"{ctx[:8]:>10}", end="")
            print()

            q_sim = similarity_matrix["question_similarity"]
            for i, ctx1 in enumerate(contexts):
                print(f"{ctx1[:10]:12}", end="")
                for j, ctx2 in enumerate(contexts):
                    if i == j:
                        print(f"{'---':>10}", end="")
                    else:
                        print(f"{q_sim[i][j]*100:>9.0f}%", end="")
                print()

        # Cross-tier analysis
        print("\n" + "=" * 60)
        print("🔄 CROSS-TIER ANALYSIS")
        print("=" * 60)

        # Find which tiers have most context differentiation
        tier_scores = {}
        for tier in tiers:
            matrix = self.generate_similarity_matrix(contexts, tier)
            diff = self.find_most_differentiated(matrix)
            tier_scores[tier] = diff["differentiation_score"]

        print("\n📊 Context Differentiation by Tier:")
        sorted_tiers = sorted(tier_scores.items(), key=lambda x: x[1], reverse=True)
        for tier, score in sorted_tiers:
            print(f"  • {tier.upper()}: {score:.1%} differentiation")

        # Recommendations
        print("\n💡 RECOMMENDATIONS:")
        print("-" * 40)

        # Find problematic pairs
        for tier in tiers:
            matrix = self.generate_similarity_matrix(contexts, tier)
            diff = self.find_most_differentiated(matrix)

            if diff["least_differentiated"]:
                print(f"\n{tier.upper()} tier improvements needed:")
                for ctx1, ctx2, sim in diff["least_differentiated"][:2]:
                    if sim > 0.8:
                        print(f"  ⚠️  {ctx1} and {ctx2} are {sim*100:.0f}% similar")
                        print(f"     → Add more {ctx1}-specific prompts")
                        print(f"     → Emphasize unique {ctx2} characteristics")


def main():
    """Run similarity analysis."""
    analyzer = ContextSimilarityAnalyzer()

    # Load results (you'll need to run tests first)
    analyzer.load_results()

    if not analyzer.results:
        print("❌ No test results found. Please run context tests first:")
        print("   poetry run python tests/validation/test_context_by_tier.py")
        return

    # Generate report
    analyzer.generate_report()

    # Save analysis
    output_file = str(VALIDATION_DIR / "CONTEXT_SIMILARITY_ANALYSIS.json")

    analysis_results = {"tiers": {}}

    for tier in ["free", "starter", "growth", "scale"]:
        contexts = ["startup", "enterprise", "agency", "open_source"]
        matrix = analyzer.generate_similarity_matrix(contexts, tier)
        diff = analyzer.find_most_differentiated(matrix)

        analysis_results["tiers"][tier] = {
            "similarity_matrix": matrix,
            "differentiation": diff,
        }

    with open(output_file, "w") as f:
        json.dump(analysis_results, f, indent=2)

    print(f"\n💾 Detailed analysis saved to: {output_file}")


if __name__ == "__main__":
    main()
