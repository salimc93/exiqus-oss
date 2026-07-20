#!/usr/bin/env python3
"""
Analyze differentiation metrics for marketing claims.
Generates concrete, quantifiable differentiators.
"""

import json
import os
from datetime import datetime
from typing import Dict, List

import numpy as np
from pathlib import Path



VALIDATION_DIR = Path(__file__).resolve().parent
class MarketingMetricsAnalyzer:
    """Generate marketing-ready differentiation metrics."""

    def __init__(self):
        self.tier_weights = {
            "free": 1.0,  # High volume, low revenue
            "starter": 2.0,  # Entry point
            "growth": 3.5,  # Sweet spot
            "scale": 5.0,  # High value
        }

        self.context_importance = {
            "startup": 4.0,  # High growth market
            "enterprise": 5.0,  # Highest value
            "agency": 3.5,  # Good volume
            "open_source": 2.5,  # Lower commercial value
        }

    def calculate_customer_value_score(
        self, differentiation_score: float, tier: str, context: str
    ) -> float:
        """Calculate customer value score for prioritization."""
        tier_weight = self.tier_weights.get(tier, 1.0)
        context_weight = self.context_importance.get(context, 1.0)

        # Normalize to 0-100 scale
        value_score = differentiation_score * tier_weight * context_weight * 4

        return min(100, value_score)

    def generate_marketing_claims(self, similarity_data: Dict) -> Dict[str, any]:
        """Generate concrete marketing claims from data."""
        claims = {
            "headline_metrics": [],
            "tier_specific_claims": {},
            "context_specific_claims": {},
            "competitive_advantages": [],
            "proof_points": [],
        }

        # Analyze each tier
        for tier, data in similarity_data.get("tiers", {}).items():
            if not data.get("differentiation"):
                continue

            diff_score = data["differentiation"]["differentiation_score"]

            # Generate tier-specific claims
            if diff_score > 0.6:  # 60%+ unique insights
                unique_percentage = int(diff_score * 100)
                claims["tier_specific_claims"][tier] = {
                    "primary": f"{unique_percentage}% unique insights per hiring context",
                    "supporting": [
                        f"AI adapts questions with {unique_percentage}% differentiation",
                        f"Context-aware analysis with {unique_percentage}% unique recommendations",
                        "Tailored metrics focusing on what matters for your context",
                    ],
                }

                # Add headline metric if it's a premium tier
                if tier in ["growth", "scale"]:
                    claims["headline_metrics"].append(
                        {
                            "metric": f"{unique_percentage}% Context Differentiation",
                            "tier": tier.upper(),
                            "tagline": f"Our AI delivers {unique_percentage}% unique insights for each hiring context",
                        }
                    )

        # Find best differentiated pairs
        best_pairs = []
        for tier, data in similarity_data.get("tiers", {}).items():
            if (
                "differentiation" in data
                and "most_differentiated" in data["differentiation"]
            ):
                for ctx1, ctx2, sim in data["differentiation"]["most_differentiated"][
                    :3
                ]:
                    diff = (1 - sim) * 100
                    if diff > 70:  # 70%+ different
                        best_pairs.append(
                            {
                                "contexts": f"{ctx1} vs {ctx2}",
                                "difference": diff,
                                "tier": tier,
                                "claim": f"{int(diff)}% different insights between {ctx1} and {ctx2} hiring",
                            }
                        )

        # Sort by difference
        best_pairs.sort(key=lambda x: x["difference"], reverse=True)

        # Generate competitive advantages
        if best_pairs:
            top_diff = best_pairs[0]["difference"]
            claims["competitive_advantages"].extend(
                [
                    f"Up to {int(top_diff)}% differentiation between hiring contexts",
                    "Only AI recruitment tool with quantifiable context adaptation",
                    "Proven context-aware intelligence, not generic questions",
                    f"Average {int(np.mean([p['difference'] for p in best_pairs[:5]]))}% unique insights per context",
                ]
            )

        # Context-specific claims
        context_scores = self._calculate_context_differentiation_scores(similarity_data)
        for context, score in context_scores.items():
            if score > 0.5:
                unique_pct = int(score * 100)
                claims["context_specific_claims"][context] = {
                    "primary": f"{unique_pct}% unique {context} insights",
                    "details": self._get_context_specific_benefits(context, unique_pct),
                }

        # Generate proof points
        claims["proof_points"] = self._generate_proof_points(similarity_data)

        return claims

    def _calculate_context_differentiation_scores(
        self, similarity_data: Dict
    ) -> Dict[str, float]:
        """Calculate average differentiation score for each context."""
        context_scores = {}
        contexts = ["startup", "enterprise", "agency", "open_source"]

        for context in contexts:
            scores = []
            for tier_data in similarity_data.get("tiers", {}).values():
                if "similarity_matrix" in tier_data:
                    matrix = tier_data["similarity_matrix"]
                    if context in matrix.get("contexts", []):
                        idx = matrix["contexts"].index(context)
                        # Get average similarity with other contexts
                        q_sim = matrix["question_similarity"][idx]
                        avg_sim = np.mean(
                            [q_sim[i] for i in range(len(q_sim)) if i != idx]
                        )
                        scores.append(1 - avg_sim)  # Convert to differentiation

            if scores:
                context_scores[context] = np.mean(scores)

        return context_scores

    def _get_context_specific_benefits(
        self, context: str, unique_pct: int
    ) -> List[str]:
        """Get context-specific benefit statements."""
        benefits = {
            "startup": [
                f"{unique_pct}% startup-specific questions about agility and growth",
                "Identifies candidates who thrive in fast-paced environments",
                "Assesses ability to wear multiple hats effectively",
            ],
            "enterprise": [
                f"{unique_pct}% enterprise-focused questions on scale and process",
                "Evaluates compliance and governance understanding",
                "Identifies leaders who can navigate complex organizations",
            ],
            "agency": [
                f"{unique_pct}% agency-specific questions about client management",
                "Assesses project juggling and deadline management skills",
                "Identifies candidates who excel at context switching",
            ],
            "open_source": [
                f"{unique_pct}% community-focused questions",
                "Evaluates collaboration in distributed teams",
                "Identifies candidates with strong documentation skills",
            ],
        }

        return benefits.get(context, [])

    def _generate_proof_points(self, similarity_data: Dict) -> List[Dict[str, str]]:
        """Generate specific proof points for marketing."""
        proof_points = []

        # Count total unique question variations
        total_contexts = 4
        total_tiers = 4
        total_combinations = total_contexts * total_tiers

        # Calculate average differentiation across all tiers
        all_diff_scores = []
        for tier_data in similarity_data.get("tiers", {}).values():
            if "differentiation" in tier_data:
                all_diff_scores.append(
                    tier_data["differentiation"]["differentiation_score"]
                )

        if all_diff_scores:
            avg_diff = np.mean(all_diff_scores) * 100

            proof_points.extend(
                [
                    {
                        "metric": f"{int(avg_diff)}%",
                        "description": "Average differentiation across all contexts",
                        "detail": f"Each hiring context receives {int(avg_diff)}% unique insights",
                    },
                    {
                        "metric": f"{total_combinations}",
                        "description": "Unique context-tier combinations",
                        "detail": "Tailored analysis for every scenario",
                    },
                ]
            )

        # Find tier with highest differentiation
        best_tier = None
        best_score = 0
        for tier, data in similarity_data.get("tiers", {}).items():
            if "differentiation" in data:
                score = data["differentiation"]["differentiation_score"]
                if score > best_score:
                    best_score = score
                    best_tier = tier

        if best_tier:
            proof_points.append(
                {
                    "metric": f"{int(best_score * 100)}%",
                    "description": f"Peak differentiation in {best_tier.upper()} tier",
                    "detail": "Premium tiers deliver maximum context adaptation",
                }
            )

        return proof_points

    def generate_priority_matrix(self, similarity_data: Dict) -> List[Dict[str, any]]:
        """Generate optimization priority matrix."""
        priorities = []

        for tier, tier_data in similarity_data.get("tiers", {}).items():
            if "differentiation" not in tier_data:
                continue

            # Check least differentiated pairs
            for ctx1, ctx2, sim in tier_data["differentiation"].get(
                "least_differentiated", []
            ):
                diff_score = 1 - sim

                # Calculate value scores for both contexts
                value1 = self.calculate_customer_value_score(diff_score, tier, ctx1)
                value2 = self.calculate_customer_value_score(diff_score, tier, ctx2)
                avg_value = (value1 + value2) / 2

                # Only include if similarity is too high (>60%)
                if sim > 0.6:
                    priorities.append(
                        {
                            "tier": tier,
                            "contexts": f"{ctx1}-{ctx2}",
                            "current_similarity": f"{sim*100:.0f}%",
                            "current_differentiation": f"{diff_score*100:.0f}%",
                            "customer_value_score": avg_value,
                            "priority": (
                                "HIGH"
                                if avg_value > 50
                                else "MEDIUM" if avg_value > 25 else "LOW"
                            ),
                            "action": f"Increase differentiation between {ctx1} and {ctx2} in {tier} tier",
                        }
                    )

        # Sort by customer value score
        priorities.sort(key=lambda x: x["customer_value_score"], reverse=True)

        return priorities

    def generate_marketing_report(self, similarity_data: Dict):
        """Generate comprehensive marketing metrics report."""
        print("\n" + "=" * 80)
        print("📊 MARKETING DIFFERENTIATION METRICS")
        print("=" * 80)

        claims = self.generate_marketing_claims(similarity_data)

        # Headline metrics
        if claims["headline_metrics"]:
            print("\n🌟 HEADLINE METRICS FOR MARKETING:")
            print("-" * 60)
            for metric in claims["headline_metrics"][:3]:
                print(f"\n{metric['tier']} Tier:")
                print(f"  📈 {metric['metric']}")
                print("  💬 \"{metric['tagline']}\"")

        # Competitive advantages
        if claims["competitive_advantages"]:
            print("\n🏆 COMPETITIVE ADVANTAGES:")
            print("-" * 60)
            for i, advantage in enumerate(claims["competitive_advantages"], 1):
                print(f"{i}. {advantage}")

        # Proof points
        if claims["proof_points"]:
            print("\n✅ PROOF POINTS:")
            print("-" * 60)
            for proof in claims["proof_points"]:
                print(f"\n• {proof['metric']}: {proof['description']}")
                print(f"  → {proof['detail']}")

        # Context-specific claims
        if claims["context_specific_claims"]:
            print("\n🎯 CONTEXT-SPECIFIC CLAIMS:")
            print("-" * 60)
            for context, data in claims["context_specific_claims"].items():
                print(f"\n{context.upper()}:")
                print(f"  Primary: {data['primary']}")
                for benefit in data["details"][:2]:
                    print(f"  • {benefit}")

        # Priority optimization matrix
        priorities = self.generate_priority_matrix(similarity_data)
        if priorities:
            print("\n⚡ OPTIMIZATION PRIORITIES:")
            print("-" * 60)
            print(
                f"{'Tier':8} {'Contexts':20} {'Similarity':12} {'Value Score':12} {'Priority':10}"
            )
            print("-" * 72)

            for p in priorities[:5]:  # Top 5 priorities
                print(
                    f"{p['tier']:8} {p['contexts']:20} {p['current_similarity']:12} "
                    f"{p['customer_value_score']:11.1f} {p['priority']:10}"
                )

        # Marketing readiness
        print("\n📣 MARKETING READINESS:")
        print("-" * 60)

        # Check if we can make the 60%+ claim
        ready_tiers = []
        for tier, claims_data in claims["tier_specific_claims"].items():
            if (
                "60%" in claims_data["primary"]
                or int(claims_data["primary"].split("%")[0]) >= 60
            ):
                ready_tiers.append(tier)

        if ready_tiers:
            print(
                f"✅ Ready to claim '60%+ unique insights' for: {', '.join([t.upper() for t in ready_tiers])}"
            )
        else:
            print("⚠️  Need more differentiation to claim '60%+ unique insights'")

        # Save report
        report_data = {
            "generated_at": datetime.now().isoformat(),
            "claims": claims,
            "priorities": priorities,
            "ready_for_60_percent_claim": len(ready_tiers) > 0,
            "ready_tiers": ready_tiers,
        }

        output_file = str(VALIDATION_DIR / "MARKETING_METRICS.json")
        with open(output_file, "w") as f:
            json.dump(report_data, f, indent=2)

        print(f"\n💾 Marketing metrics saved to: {output_file}")


def main():
    """Generate marketing metrics from similarity analysis."""
    # Load similarity analysis results
    similarity_file = str(VALIDATION_DIR / "CONTEXT_SIMILARITY_ANALYSIS.json")

    if not os.path.exists(similarity_file):
        print("❌ No similarity analysis found. Run these commands first:")
        print("  1. poetry run python tests/validation/test_context_by_tier.py")
        print("  2. poetry run python tests/validation/analyze_context_similarity.py")
        return

    with open(similarity_file, "r") as f:
        similarity_data = json.load(f)

    # Generate marketing metrics
    analyzer = MarketingMetricsAnalyzer()
    analyzer.generate_marketing_report(similarity_data)


if __name__ == "__main__":
    main()
