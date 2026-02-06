"""
Synthesize Tool

Synthesizes collected data into a coherent intelligence report.
"""

from typing import Any, Dict, List, TYPE_CHECKING

from app.core.tools.base import BaseTool, ToolParameter, ToolResult

if TYPE_CHECKING:
    from app.core.llm.router import LLMRouter


SYNTHESIZE_SYSTEM_PROMPT = """你是一个专业的情报综合分析师。你的任务是将收集到的所有信息综合成一份简洁、有洞察力的情报报告。

报告要求：
1. 开门见山，直接给出核心发现
2. 分点列出关键信息
3. 标注信息可信度
4. 指出需要关注的风险或机会
5. 提供可执行的建议

报告结构：
- 核心发现（1-2句话总结）
- 关键要点（3-5个要点）
- 市场动态
- 风险与机会
- 建议行动

请以 JSON 格式返回。"""


class SynthesizeTool(BaseTool):
    """
    Synthesis tool using LLM.

    Combines all collected and analyzed data into a final intelligence report.
    """

    def __init__(self, llm_router: "LLMRouter"):
        self.llm = llm_router

    @property
    def name(self) -> str:
        return "synthesize"

    @property
    def description(self) -> str:
        return "综合所有收集和分析的数据，生成最终的情报报告。"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="collected_data",
                type="array",
                description="收集到的原始数据",
            ),
            ToolParameter(
                name="analysis_results",
                type="object",
                description="分析结果",
                required=False,
            ),
            ToolParameter(
                name="original_command",
                type="string",
                description="原始用户命令",
            ),
        ]

    async def execute(
        self,
        collected_data: List[Dict[str, Any]],
        original_command: str,
        analysis_results: Dict[str, Any] = None,
        **kwargs,
    ) -> ToolResult:
        """Execute synthesis."""
        # Prepare context for synthesis
        context = self._prepare_synthesis_context(
            collected_data, analysis_results, original_command
        )

        prompt = f"""基于以下收集和分析的信息，请生成一份情报报告。

原始任务: {original_command}

收集的信息:
{context}

请生成 JSON 格式的情报报告：
{{
    "executive_summary": "执行摘要（50字以内）",
    "key_findings": ["关键发现1", "关键发现2", ...],
    "market_dynamics": {{
        "trends": ["趋势描述"],
        "sentiment": "整体情绪倾向",
        "hot_topics": ["热门话题"]
    }},
    "risks_and_opportunities": {{
        "risks": ["风险点"],
        "opportunities": ["机会点"]
    }},
    "recommendations": ["建议1", "建议2", ...],
    "data_quality": {{
        "total_sources": 数量,
        "high_credibility": 数量,
        "coverage": "覆盖情况描述"
    }}
}}"""

        try:
            # Use heavy model for synthesis (needs deep reasoning)
            result = await self.llm.generate(
                prompt=prompt,
                task="synthesis",
                system_instruction=SYNTHESIZE_SYSTEM_PROMPT,
                temperature=0.4,
                max_tokens=2000,
            )

            # Parse synthesis result
            report = self._parse_synthesis_result(result["text"])
            tokens_used = result["usage"]["prompt_tokens"] + result["usage"]["completion_tokens"]

            return ToolResult.ok(
                data=report,
                tokens_used=tokens_used,
            )

        except Exception as e:
            return ToolResult.fail(f"综合分析失败: {str(e)}")

    def _prepare_synthesis_context(
        self,
        collected_data: List[Dict[str, Any]],
        analysis_results: Dict[str, Any] = None,
        original_command: str = "",
    ) -> str:
        """Prepare context string for synthesis."""
        parts = []

        # Add collected data summary
        if collected_data:
            parts.append(f"## 收集的数据 (共 {len(collected_data)} 条)")
            for i, item in enumerate(collected_data[:15], 1):  # Limit to 15
                platform = item.get("platform", "unknown")
                title = item.get("title", "无标题")
                summary = item.get("summary", "")[:200]
                parts.append(f"{i}. [{platform}] {title}: {summary}")

        # Add analysis results
        if analysis_results:
            parts.append("\n## 分析结果")
            if "main_points" in analysis_results:
                parts.append("主要发现:")
                for point in analysis_results["main_points"]:
                    parts.append(f"  - {point}")

            if "sentiment" in analysis_results:
                parts.append(f"情感分析: {analysis_results['sentiment']}")

            if "entities" in analysis_results:
                entities = analysis_results["entities"]
                if entities.get("companies"):
                    parts.append(f"提及公司: {', '.join(e.get('name', '') for e in entities['companies'][:5])}")

        return "\n".join(parts)

    def _parse_synthesis_result(self, text: str) -> Dict[str, Any]:
        """Parse LLM synthesis result."""
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
            # Return a structured fallback if parsing fails
            return {
                "executive_summary": text[:200] if len(text) > 200 else text,
                "key_findings": ["分析结果解析失败，请查看原始输出"],
                "raw_output": text,
                "parsing_failed": True,
            }
