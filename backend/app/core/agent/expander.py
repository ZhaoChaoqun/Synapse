"""
Search Expander Module

Handles intelligent recursive search expansion based on discovered entities and keywords.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.llm.router import LLMRouter, get_llm_router

logger = logging.getLogger(__name__)


@dataclass
class ExpansionCandidate:
    """A candidate keyword/entity for search expansion."""

    keyword: str
    source: str  # Where it was found: "content", "title", "author", "llm"
    relevance_score: float  # 0-1 relevance to original query
    frequency: int = 1  # How many times it appeared
    context: Optional[str] = None  # Surrounding context

    def __hash__(self):
        return hash(self.keyword.lower())

    def __eq__(self, other):
        if isinstance(other, ExpansionCandidate):
            return self.keyword.lower() == other.keyword.lower()
        return False


@dataclass
class ExpansionPlan:
    """Plan for search expansion."""

    candidates: List[ExpansionCandidate]
    priority_keywords: List[str]  # Top keywords to search
    estimated_value: float  # Expected value of expansion
    reason: str  # Why expansion is recommended

    def to_dict(self) -> Dict[str, Any]:
        return {
            "priority_keywords": self.priority_keywords,
            "total_candidates": len(self.candidates),
            "estimated_value": round(self.estimated_value, 2),
            "reason": self.reason,
        }


class SearchExpander:
    """
    Intelligent search expansion module.

    Analyzes collected data to discover:
    - Related entities (companies, products, people)
    - Emerging keywords and trends
    - Related topics worth exploring
    """

    # Known AI/tech entities for recognition
    KNOWN_ENTITIES = {
        "companies": [
            "DeepSeek", "OpenAI", "Anthropic", "Google", "Meta", "Microsoft",
            "百度", "阿里", "腾讯", "字节跳动", "华为", "商汤", "旷视",
            "Moonshot", "智谱", "百川", "零一万物", "MiniMax", "阶跃星辰",
        ],
        "products": [
            "GPT-4", "GPT-5", "Claude", "Gemini", "Llama", "Mistral",
            "文心一言", "通义千问", "Kimi", "豆包", "星火",
            "DeepSeek-V3", "DeepSeek-R1", "GLM-4",
        ],
        "concepts": [
            "RAG", "Agent", "多模态", "长上下文", "思维链", "强化学习",
            "RLHF", "DPO", "MoE", "Transformer", "推理优化",
        ],
    }

    # Patterns for entity extraction
    ENTITY_PATTERNS = [
        r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",  # CamelCase words
        r"([\u4e00-\u9fa5]{2,6}(?:公司|科技|AI|智能))",  # Chinese company names
        r"([A-Z]{2,6}(?:-\d+)?)",  # Acronyms like GPT-4
    ]

    def __init__(
        self,
        llm_router: Optional[LLMRouter] = None,
        max_candidates: int = 20,
    ):
        """
        Initialize SearchExpander.

        Args:
            llm_router: LLM router for advanced extraction
            max_candidates: Maximum candidates to track
        """
        self.llm = llm_router or get_llm_router()
        self.max_candidates = max_candidates
        self._seen_keywords: Set[str] = set()

    async def analyze(
        self,
        data: List[Dict[str, Any]],
        original_query: str,
        already_searched: List[str],
    ) -> ExpansionPlan:
        """
        Analyze collected data and generate expansion plan.

        Args:
            data: Collected data items
            original_query: The original search query
            already_searched: Keywords already searched

        Returns:
            ExpansionPlan with prioritized keywords
        """
        # Track what we've already searched
        self._seen_keywords = set(kw.lower() for kw in already_searched)
        self._seen_keywords.add(original_query.lower())

        # Extract candidates from different sources
        candidates: List[ExpansionCandidate] = []

        # 1. Extract from content
        content_candidates = self._extract_from_content(data, original_query)
        candidates.extend(content_candidates)

        # 2. Extract known entities
        entity_candidates = self._extract_known_entities(data)
        candidates.extend(entity_candidates)

        # 3. Extract from titles
        title_candidates = self._extract_from_titles(data, original_query)
        candidates.extend(title_candidates)

        # Deduplicate and merge
        merged = self._merge_candidates(candidates)

        # Filter already searched
        filtered = [
            c for c in merged
            if c.keyword.lower() not in self._seen_keywords
        ]

        # Score and rank
        scored = self._score_candidates(filtered, original_query)
        scored.sort(key=lambda x: x.relevance_score, reverse=True)

        # Take top candidates
        top_candidates = scored[:self.max_candidates]

        # Generate priority list
        priority_keywords = [c.keyword for c in top_candidates[:5]]

        # Calculate expected value
        estimated_value = self._estimate_expansion_value(top_candidates, data)

        # Generate reason
        reason = self._generate_expansion_reason(top_candidates, original_query)

        return ExpansionPlan(
            candidates=top_candidates,
            priority_keywords=priority_keywords,
            estimated_value=estimated_value,
            reason=reason,
        )

    def _extract_from_content(
        self,
        data: List[Dict[str, Any]],
        original_query: str,
    ) -> List[ExpansionCandidate]:
        """Extract candidates from content text."""
        candidates = []
        keyword_freq: Dict[str, int] = {}

        for item in data:
            content = (item.get("content", "") or "") + " " + (item.get("summary", "") or "")

            # Extract using patterns
            for pattern in self.ENTITY_PATTERNS:
                matches = re.findall(pattern, content)
                for match in matches:
                    if len(match) >= 2 and match.lower() not in self._seen_keywords:
                        keyword_freq[match] = keyword_freq.get(match, 0) + 1

        # Create candidates from frequent keywords
        for keyword, freq in keyword_freq.items():
            if freq >= 2:  # Appeared in multiple items
                candidates.append(ExpansionCandidate(
                    keyword=keyword,
                    source="content",
                    relevance_score=0.5,
                    frequency=freq,
                ))

        return candidates

    def _extract_known_entities(
        self,
        data: List[Dict[str, Any]],
    ) -> List[ExpansionCandidate]:
        """Extract known entities from data."""
        candidates = []
        found_entities: Dict[str, int] = {}

        all_text = " ".join(
            (item.get("content", "") or "") +
            (item.get("title", "") or "") +
            (item.get("summary", "") or "")
            for item in data
        ).lower()

        # Check each known entity
        for category, entities in self.KNOWN_ENTITIES.items():
            for entity in entities:
                if entity.lower() in all_text and entity.lower() not in self._seen_keywords:
                    count = all_text.count(entity.lower())
                    if count > 0:
                        found_entities[entity] = count

        # Create candidates
        for entity, count in found_entities.items():
            candidates.append(ExpansionCandidate(
                keyword=entity,
                source="known_entity",
                relevance_score=0.7,  # Known entities get higher base score
                frequency=count,
            ))

        return candidates

    def _extract_from_titles(
        self,
        data: List[Dict[str, Any]],
        original_query: str,
    ) -> List[ExpansionCandidate]:
        """Extract candidates from titles."""
        candidates = []

        for item in data:
            title = item.get("title", "") or ""

            # Extract capitalized phrases
            matches = re.findall(r"([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)", title)
            for match in matches:
                if (
                    len(match) >= 3 and
                    match.lower() not in self._seen_keywords and
                    match.lower() not in original_query.lower()
                ):
                    candidates.append(ExpansionCandidate(
                        keyword=match,
                        source="title",
                        relevance_score=0.6,
                        frequency=1,
                    ))

            # Extract Chinese key terms
            chinese_matches = re.findall(r"([\u4e00-\u9fa5]{2,8})", title)
            for match in chinese_matches:
                if (
                    match not in self._seen_keywords and
                    match not in original_query and
                    len(match) >= 2
                ):
                    candidates.append(ExpansionCandidate(
                        keyword=match,
                        source="title",
                        relevance_score=0.5,
                        frequency=1,
                    ))

        return candidates

    def _merge_candidates(
        self,
        candidates: List[ExpansionCandidate],
    ) -> List[ExpansionCandidate]:
        """Merge duplicate candidates."""
        merged: Dict[str, ExpansionCandidate] = {}

        for candidate in candidates:
            key = candidate.keyword.lower()
            if key in merged:
                # Merge: keep higher score, sum frequency
                existing = merged[key]
                existing.frequency += candidate.frequency
                existing.relevance_score = max(
                    existing.relevance_score,
                    candidate.relevance_score
                )
            else:
                merged[key] = candidate

        return list(merged.values())

    def _score_candidates(
        self,
        candidates: List[ExpansionCandidate],
        original_query: str,
    ) -> List[ExpansionCandidate]:
        """Score candidates based on relevance."""
        query_terms = set(original_query.lower().split())

        for candidate in candidates:
            score = candidate.relevance_score

            # Boost for frequency
            if candidate.frequency >= 5:
                score += 0.2
            elif candidate.frequency >= 3:
                score += 0.1

            # Boost for known entities
            if candidate.source == "known_entity":
                score += 0.15

            # Boost for partial query match
            candidate_terms = set(candidate.keyword.lower().split())
            if candidate_terms & query_terms:
                score += 0.1

            # Penalize very short or very long keywords
            if len(candidate.keyword) < 2:
                score -= 0.3
            elif len(candidate.keyword) > 30:
                score -= 0.2

            candidate.relevance_score = min(1.0, max(0.0, score))

        return candidates

    def _estimate_expansion_value(
        self,
        candidates: List[ExpansionCandidate],
        data: List[Dict[str, Any]],
    ) -> float:
        """Estimate the value of performing expansion searches."""
        if not candidates:
            return 0.0

        # Factors that increase value
        value = 0.5  # Base value

        # More high-quality candidates = higher value
        high_quality = sum(1 for c in candidates if c.relevance_score >= 0.7)
        value += min(0.3, high_quality * 0.1)

        # Known entities discovered = higher value
        known_entity_count = sum(1 for c in candidates if c.source == "known_entity")
        value += min(0.2, known_entity_count * 0.05)

        # Low data count = higher value for expansion
        if len(data) < 5:
            value += 0.1

        return min(1.0, value)

    def _generate_expansion_reason(
        self,
        candidates: List[ExpansionCandidate],
        original_query: str,
    ) -> str:
        """Generate human-readable reason for expansion."""
        if not candidates:
            return "未发现需要扩展的关键词"

        known_entities = [c for c in candidates if c.source == "known_entity"]
        frequent = [c for c in candidates if c.frequency >= 3]

        parts = []

        if known_entities:
            names = ", ".join(c.keyword for c in known_entities[:3])
            parts.append(f"发现相关实体: {names}")

        if frequent:
            names = ", ".join(c.keyword for c in frequent[:3])
            parts.append(f"高频关键词: {names}")

        if not parts:
            parts.append(f"发现 {len(candidates)} 个潜在扩展方向")

        return "; ".join(parts)

    async def extract_with_llm(
        self,
        data: List[Dict[str, Any]],
        original_query: str,
    ) -> List[ExpansionCandidate]:
        """
        Use LLM for advanced keyword extraction.

        Args:
            data: Collected data items
            original_query: The original search query

        Returns:
            List of LLM-extracted candidates
        """
        candidates = []

        try:
            # Prepare content for LLM
            content_summary = "\n".join(
                f"- {item.get('title', '无标题')}: {(item.get('summary') or item.get('content', ''))[:150]}..."
                for item in data[:8]
            )

            prompt = f"""分析以下关于"{original_query}"的内容，提取值得深入搜索的关键词:

{content_summary}

请提取:
1. 相关公司/产品名称
2. 重要技术概念
3. 关键人物
4. 值得追踪的话题

以JSON数组格式返回关键词列表，每个最多10个字。"""

            response = await self.llm.generate(
                prompt,
                task_type="extract",
                system_prompt="你是一个信息提取专家。只返回JSON数组，不要其他内容。",
            )

            # Parse response (simplified)
            import json
            try:
                keywords = json.loads(response.content)
                if isinstance(keywords, list):
                    for kw in keywords[:10]:
                        if isinstance(kw, str) and len(kw) >= 2:
                            candidates.append(ExpansionCandidate(
                                keyword=kw,
                                source="llm",
                                relevance_score=0.75,
                                frequency=1,
                            ))
            except json.JSONDecodeError:
                # Try to extract keywords from text
                for line in response.content.split("\n"):
                    line = line.strip().strip("-").strip()
                    if 2 <= len(line) <= 20:
                        candidates.append(ExpansionCandidate(
                            keyword=line,
                            source="llm",
                            relevance_score=0.6,
                            frequency=1,
                        ))

        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")

        return candidates


# Global instance
_search_expander: Optional[SearchExpander] = None


def get_search_expander() -> SearchExpander:
    """Get the global SearchExpander instance."""
    global _search_expander
    if _search_expander is None:
        _search_expander = SearchExpander()
    return _search_expander
