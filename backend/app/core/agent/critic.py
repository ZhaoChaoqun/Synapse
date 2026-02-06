"""
Critic Module

Provides critical evaluation of collected intelligence data.
Assesses credibility, identifies gaps, and suggests improvements.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.core.llm.router import LLMRouter, get_llm_router

logger = logging.getLogger(__name__)


@dataclass
class CritiqueResult:
    """Result of a critical evaluation."""

    overall_score: float  # 0-1 quality score
    credibility_score: float  # 0-1 credibility score
    coverage_score: float  # 0-1 topic coverage score
    issues: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    missing_aspects: List[str] = field(default_factory=list)
    recommended_searches: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "overall_score": round(self.overall_score, 2),
            "credibility_score": round(self.credibility_score, 2),
            "coverage_score": round(self.coverage_score, 2),
            "issues": self.issues,
            "suggestions": self.suggestions,
            "missing_aspects": self.missing_aspects,
            "recommended_searches": self.recommended_searches,
            "summary": self.summary,
        }

    @property
    def needs_improvement(self) -> bool:
        """Check if the data needs improvement."""
        return self.overall_score < 0.7 or len(self.missing_aspects) > 0

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are critical issues."""
        return any(issue.get("severity") == "critical" for issue in self.issues)


class Critic:
    """
    Critical evaluation module for Agent intelligence.

    Evaluates:
    - Credibility of sources
    - Coverage completeness
    - Data quality
    - Potential biases
    - Information gaps
    """

    # Credibility factors by platform
    PLATFORM_BASE_CREDIBILITY = {
        "zhihu": 0.7,  # Generally good quality discussions
        "wechat": 0.6,  # Varies widely
        "xiaohongshu": 0.5,  # More consumer-focused
        "douyin": 0.4,  # Entertainment-focused
    }

    # Author credibility indicators
    CREDIBILITY_INDICATORS = {
        "verified": 0.15,
        "high_followers": 0.1,
        "expert_label": 0.2,
        "original_content": 0.1,
    }

    def __init__(self, llm_router: Optional[LLMRouter] = None):
        """
        Initialize Critic.

        Args:
            llm_router: LLM router for advanced evaluation
        """
        self.llm = llm_router or get_llm_router()

    async def evaluate(
        self,
        data: List[Dict[str, Any]],
        original_query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> CritiqueResult:
        """
        Evaluate collected intelligence data.

        Args:
            data: Collected data items
            original_query: The original search query
            context: Additional context

        Returns:
            CritiqueResult with evaluation scores and suggestions
        """
        if not data:
            return CritiqueResult(
                overall_score=0.0,
                credibility_score=0.0,
                coverage_score=0.0,
                issues=[{"type": "no_data", "severity": "critical", "message": "没有收集到任何数据"}],
                suggestions=["尝试扩展搜索关键词", "检查平台连接状态"],
                summary="数据收集失败，需要重新执行搜索",
            )

        # Evaluate different aspects
        credibility_score, credibility_issues = self._evaluate_credibility(data)
        coverage_score, coverage_gaps = self._evaluate_coverage(data, original_query)
        quality_score, quality_issues = self._evaluate_quality(data)

        # Calculate overall score
        overall_score = (
            credibility_score * 0.4 +
            coverage_score * 0.35 +
            quality_score * 0.25
        )

        # Combine issues
        all_issues = credibility_issues + quality_issues

        # Generate suggestions
        suggestions = self._generate_suggestions(
            credibility_score, coverage_score, quality_score, coverage_gaps
        )

        # Generate recommended searches
        recommended_searches = self._generate_search_recommendations(
            original_query, coverage_gaps, data
        )

        # Generate summary
        summary = self._generate_summary(
            overall_score, credibility_score, coverage_score, len(data)
        )

        return CritiqueResult(
            overall_score=overall_score,
            credibility_score=credibility_score,
            coverage_score=coverage_score,
            issues=all_issues,
            suggestions=suggestions,
            missing_aspects=coverage_gaps,
            recommended_searches=recommended_searches,
            summary=summary,
        )

    def _evaluate_credibility(
        self, data: List[Dict[str, Any]]
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """Evaluate credibility of data sources."""
        if not data:
            return 0.0, []

        scores = []
        issues = []

        for item in data:
            platform = item.get("platform", "unknown")
            base_score = self.PLATFORM_BASE_CREDIBILITY.get(platform, 0.5)

            # Adjust based on metrics
            metrics = item.get("metrics", {})

            # High engagement indicates relevance
            engagement = metrics.get("voteup", 0) + metrics.get("likes", 0)
            if engagement > 1000:
                base_score += 0.1
            elif engagement > 100:
                base_score += 0.05

            # Author factors
            author = item.get("author", "")
            if "专家" in author or "分析师" in author:
                base_score += 0.1

            # Check for issues
            content = item.get("content", "") or item.get("summary", "")
            if len(content) < 50:
                issues.append({
                    "type": "low_content",
                    "severity": "warning",
                    "item_id": item.get("id"),
                    "message": "内容过短，可能缺乏深度",
                })
                base_score -= 0.1

            # Check for promotional content
            if self._is_promotional(content):
                issues.append({
                    "type": "promotional",
                    "severity": "warning",
                    "item_id": item.get("id"),
                    "message": "可能为推广内容",
                })
                base_score -= 0.15

            scores.append(max(0, min(1, base_score)))

        avg_score = sum(scores) / len(scores) if scores else 0

        # Penalize if too few sources
        if len(data) < 3:
            issues.append({
                "type": "few_sources",
                "severity": "warning",
                "message": f"仅有 {len(data)} 个数据源，建议增加更多来源",
            })
            avg_score *= 0.9

        return avg_score, issues

    def _evaluate_coverage(
        self, data: List[Dict[str, Any]], query: str
    ) -> Tuple[float, List[str]]:
        """Evaluate topic coverage completeness."""
        # Define expected coverage aspects based on query type
        expected_aspects = self._infer_expected_aspects(query)

        # Check which aspects are covered
        covered = set()
        all_content = " ".join(
            (item.get("content", "") or "") + " " + (item.get("title", "") or "")
            for item in data
        ).lower()

        for aspect, keywords in expected_aspects.items():
            if any(kw.lower() in all_content for kw in keywords):
                covered.add(aspect)

        # Calculate coverage score
        if not expected_aspects:
            return 0.7, []  # Default if we can't determine expected aspects

        coverage_ratio = len(covered) / len(expected_aspects)
        missing = [aspect for aspect in expected_aspects if aspect not in covered]

        return coverage_ratio, missing

    def _evaluate_quality(
        self, data: List[Dict[str, Any]]
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """Evaluate data quality."""
        if not data:
            return 0.0, []

        issues = []
        quality_scores = []

        for item in data:
            score = 0.7  # Base score

            # Check content length
            content = item.get("content", "") or item.get("summary", "")
            if len(content) > 500:
                score += 0.15
            elif len(content) > 200:
                score += 0.1

            # Check for URL (linked to original)
            if item.get("url"):
                score += 0.05

            # Check for timestamp
            if item.get("published_at"):
                score += 0.05

            # Check for duplicates (simplified)
            title = item.get("title", "")
            duplicate_count = sum(
                1 for other in data
                if other.get("title", "") == title and other.get("id") != item.get("id")
            )
            if duplicate_count > 0:
                score -= 0.1 * duplicate_count
                issues.append({
                    "type": "duplicate",
                    "severity": "info",
                    "item_id": item.get("id"),
                    "message": "发现重复内容",
                })

            quality_scores.append(max(0, min(1, score)))

        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

        # Check platform diversity
        platforms = set(item.get("platform") for item in data)
        if len(platforms) < 2:
            issues.append({
                "type": "low_diversity",
                "severity": "warning",
                "message": "数据来源单一，建议增加其他平台",
            })
            avg_quality *= 0.95

        return avg_quality, issues

    def _infer_expected_aspects(self, query: str) -> Dict[str, List[str]]:
        """Infer expected coverage aspects from query."""
        query_lower = query.lower()

        # Default aspects for AI/tech queries
        aspects = {}

        if any(kw in query_lower for kw in ["ai", "人工智能", "模型", "llm"]):
            aspects = {
                "技术特点": ["技术", "架构", "算法", "模型", "参数"],
                "性能表现": ["性能", "效果", "评测", "benchmark", "测试"],
                "应用场景": ["应用", "场景", "用例", "案例"],
                "市场分析": ["市场", "竞争", "份额", "趋势"],
            }

        if any(kw in query_lower for kw in ["公司", "企业", "融资"]):
            aspects["融资情况"] = ["融资", "估值", "投资", "vc"]
            aspects["团队背景"] = ["创始人", "团队", "背景", "经历"]

        if any(kw in query_lower for kw in ["产品", "功能", "更新"]):
            aspects["产品功能"] = ["功能", "特性", "feature", "能力"]
            aspects["用户反馈"] = ["用户", "反馈", "评价", "体验"]
            aspects["定价策略"] = ["价格", "定价", "收费", "免费"]

        return aspects if aspects else {
            "基本信息": ["是什么", "介绍", "简介"],
            "详细分析": ["分析", "解读", "深度"],
        }

    def _is_promotional(self, content: str) -> bool:
        """Check if content appears to be promotional."""
        promotional_signals = [
            "限时优惠", "立即购买", "点击链接", "扫码",
            "优惠券", "折扣", "促销", "广告",
        ]
        content_lower = content.lower()
        return any(signal in content_lower for signal in promotional_signals)

    def _generate_suggestions(
        self,
        credibility: float,
        coverage: float,
        quality: float,
        gaps: List[str],
    ) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []

        if credibility < 0.6:
            suggestions.append("建议增加权威来源的数据，如行业报告或专家观点")

        if coverage < 0.7 and gaps:
            suggestions.append(f"信息覆盖不完整，缺少以下方面: {', '.join(gaps[:3])}")

        if quality < 0.6:
            suggestions.append("数据质量有待提高，建议筛选更详细的内容")

        if credibility >= 0.7 and coverage >= 0.7 and quality >= 0.7:
            suggestions.append("数据质量良好，可以进行综合分析")

        return suggestions

    def _generate_search_recommendations(
        self,
        original_query: str,
        gaps: List[str],
        data: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate recommended follow-up searches."""
        recommendations = []

        # Add searches for coverage gaps
        for gap in gaps[:2]:
            recommendations.append(f"{original_query} {gap}")

        # Extract entities for deeper search
        all_content = " ".join(
            item.get("content", "") or item.get("summary", "")
            for item in data
        )

        # Simple entity extraction (could be enhanced with NER)
        potential_entities = []
        for item in data:
            author = item.get("author", "")
            if author and len(author) < 20:
                if author not in potential_entities:
                    potential_entities.append(author)

        # Add entity-specific searches
        for entity in potential_entities[:1]:
            if entity not in original_query:
                recommendations.append(f"{entity} {original_query.split()[0]}")

        return recommendations[:3]

    def _generate_summary(
        self,
        overall: float,
        credibility: float,
        coverage: float,
        data_count: int,
    ) -> str:
        """Generate evaluation summary."""
        quality_level = "优秀" if overall >= 0.8 else "良好" if overall >= 0.6 else "一般" if overall >= 0.4 else "较差"

        return (
            f"数据评估结果: {quality_level} (综合评分: {overall:.0%})\n"
            f"共收集 {data_count} 条数据，"
            f"可信度 {credibility:.0%}，覆盖度 {coverage:.0%}"
        )

    async def evaluate_with_llm(
        self,
        data: List[Dict[str, Any]],
        original_query: str,
    ) -> CritiqueResult:
        """
        Use LLM for advanced evaluation (more expensive but thorough).

        Args:
            data: Collected data items
            original_query: The original search query

        Returns:
            CritiqueResult with LLM-enhanced evaluation
        """
        # First do rule-based evaluation
        base_result = await self.evaluate(data, original_query)

        # If data quality is acceptable, skip LLM evaluation to save tokens
        if base_result.overall_score >= 0.8 and not base_result.has_critical_issues:
            return base_result

        # Use LLM for deeper analysis
        try:
            # Prepare content summary for LLM
            content_summary = "\n".join(
                f"- [{item.get('platform')}] {item.get('title', '无标题')}: {(item.get('summary') or item.get('content', ''))[:100]}..."
                for item in data[:10]
            )

            prompt = f"""请评估以下关于"{original_query}"的情报数据质量:

{content_summary}

请从以下角度评估:
1. 信息是否全面覆盖了主题的关键方面?
2. 数据来源是否可信?
3. 是否存在明显的信息缺口?
4. 建议补充搜索哪些关键词?

请用JSON格式返回评估结果。"""

            response = await self.llm.generate(
                prompt,
                task_type="analyze",
                system_prompt="你是一个专业的情报分析师，擅长评估信息质量。",
            )

            # Parse LLM response and enhance base result
            # (Simplified - would need proper JSON parsing in production)
            if "缺口" in response.content or "不足" in response.content:
                base_result.suggestions.append("LLM分析发现: 需要补充更多角度的信息")

        except Exception as e:
            logger.warning(f"LLM evaluation failed: {e}")

        return base_result


# Global instance
_critic: Optional[Critic] = None


def get_critic() -> Critic:
    """Get the global Critic instance."""
    global _critic
    if _critic is None:
        _critic = Critic()
    return _critic
