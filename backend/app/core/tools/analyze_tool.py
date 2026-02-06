"""
Analyze Tool

Analyzes collected data using LLM.
"""

from typing import Any, Dict, List, TYPE_CHECKING

from app.core.tools.base import BaseTool, ToolParameter, ToolResult

if TYPE_CHECKING:
    from app.core.llm.router import LLMRouter


ANALYZE_SYSTEM_PROMPT = """你是一个专业的情报分析师，负责分析和总结收集到的信息。

分析时请注意：
1. 提取关键信息和核心观点
2. 识别信息来源的可信度（官方公告 > 专业分析 > 用户评论）
3. 发现信息之间的矛盾或冲突
4. 标注时效性（信息是否过时）
5. 提炼行动建议

请以结构化的 JSON 格式返回分析结果。"""


class AnalyzeTool(BaseTool):
    """
    Data analysis tool using LLM.

    Analyzes collected data for sentiment, key points, and insights.
    """

    def __init__(self, llm_router: "LLMRouter"):
        self.llm = llm_router

    @property
    def name(self) -> str:
        return "analyze"

    @property
    def description(self) -> str:
        return "分析收集到的数据，提取关键信息、情感倾向和重要洞察。"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="data",
                type="array",
                description="要分析的数据列表",
            ),
            ToolParameter(
                name="analysis_type",
                type="string",
                description="分析类型: sentiment, summary, extract_entities, full",
                required=False,
                enum=["sentiment", "summary", "extract_entities", "full"],
            ),
        ]

    async def execute(
        self,
        data: List[Dict[str, Any]],
        analysis_type: str = "summary",
        **kwargs,
    ) -> ToolResult:
        """Execute data analysis."""
        if not data:
            return ToolResult.ok(data={"analysis": "没有数据需要分析", "items": []})

        # Prepare data for analysis
        data_text = self._prepare_data_for_analysis(data)

        # Build analysis prompt based on type
        prompt = self._build_analysis_prompt(data_text, analysis_type)

        try:
            # Use light model for basic analysis, heavy for full analysis
            task = "simple_qa" if analysis_type in ("sentiment", "summary") else "deep_analysis"

            result = await self.llm.generate(
                prompt=prompt,
                task=task,
                system_instruction=ANALYZE_SYSTEM_PROMPT,
                temperature=0.3,
            )

            # Parse analysis result
            analysis = self._parse_analysis_result(result["text"], analysis_type)
            tokens_used = result["usage"]["prompt_tokens"] + result["usage"]["completion_tokens"]

            return ToolResult.ok(
                data=analysis,
                tokens_used=tokens_used,
            )

        except Exception as e:
            return ToolResult.fail(f"分析失败: {str(e)}")

    def _prepare_data_for_analysis(self, data: List[Dict[str, Any]]) -> str:
        """Prepare data as text for LLM analysis."""
        texts = []
        for i, item in enumerate(data[:20], 1):  # Limit to 20 items
            platform = item.get("platform", "unknown")
            title = item.get("title", "无标题")
            summary = item.get("summary", "")
            author = item.get("author", "未知")

            texts.append(
                f"[{i}] 平台: {platform}\n"
                f"    标题: {title}\n"
                f"    作者: {author}\n"
                f"    摘要: {summary}\n"
            )

        return "\n".join(texts)

    def _build_analysis_prompt(self, data_text: str, analysis_type: str) -> str:
        """Build analysis prompt based on type."""
        base = f"请分析以下收集到的信息：\n\n{data_text}\n\n"

        if analysis_type == "sentiment":
            return base + """请分析每条信息的情感倾向，并返回 JSON 格式：
{
    "overall_sentiment": "positive/negative/neutral",
    "sentiment_score": 0.0-1.0,
    "items": [{"id": 1, "sentiment": "positive/negative/neutral", "confidence": 0.0-1.0}]
}"""

        elif analysis_type == "summary":
            return base + """请总结这些信息的核心内容，返回 JSON 格式：
{
    "main_points": ["要点1", "要点2", ...],
    "key_entities": ["实体1", "实体2", ...],
    "timeline": "时间线描述",
    "brief_summary": "100字以内的简短总结"
}"""

        elif analysis_type == "extract_entities":
            return base + """请提取所有提到的实体（公司、产品、人物），返回 JSON 格式：
{
    "companies": [{"name": "公司名", "mentions": 次数, "context": "相关上下文"}],
    "products": [{"name": "产品名", "company": "所属公司", "mentions": 次数}],
    "persons": [{"name": "人名", "role": "角色", "mentions": 次数}]
}"""

        else:  # full
            return base + """请进行全面分析，返回 JSON 格式：
{
    "summary": "综合摘要",
    "main_points": ["要点列表"],
    "sentiment": {"overall": "positive/negative/neutral", "score": 0.0-1.0},
    "entities": {"companies": [], "products": [], "persons": []},
    "credibility_assessment": {"high": [], "medium": [], "low": []},
    "contradictions": ["发现的矛盾信息"],
    "recommendations": ["建议的后续行动"]
}"""

    def _parse_analysis_result(self, text: str, analysis_type: str) -> Dict[str, Any]:
        """Parse LLM analysis result."""
        import json

        # Try to extract JSON from response
        text = text.strip()
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Return text as-is if JSON parsing fails
            return {
                "raw_analysis": text,
                "parsing_failed": True,
            }
