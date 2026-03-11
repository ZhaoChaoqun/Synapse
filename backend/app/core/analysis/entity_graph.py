"""
Entity Graph Generator

Extracts entities from collected data and builds relationship graphs.
"""

import re
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import Counter


@dataclass
class Entity:
    """Represents an entity (company, product, person, etc.)"""
    id: str
    name: str
    type: str  # company, product, person, concept, topic
    mentions: int = 1
    sentiment: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "mentions": self.mentions,
            "sentiment": self.sentiment,
            "description": self.description,
        }


@dataclass
class EntityRelation:
    """Represents a relationship between two entities"""
    source_id: str
    target_id: str
    relation_type: str  # related, owns, competes, partners, mentions
    strength: float = 0.5  # 0-1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sourceId": self.source_id,
            "targetId": self.target_id,
            "relationType": self.relation_type,
            "strength": self.strength,
        }


@dataclass
class EntityGraph:
    """Complete entity graph with nodes and edges"""
    entities: List[Entity] = field(default_factory=list)
    relations: List[EntityRelation] = field(default_factory=list)
    center_entity: Optional[str] = None
    generated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "relations": [r.to_dict() for r in self.relations],
            "centerEntity": self.center_entity,
            "generatedAt": self.generated_at,
        }


class EntityGraphGenerator:
    """
    Generates entity relationship graphs from collected data.

    Uses pattern matching and co-occurrence analysis to find entities
    and their relationships.
    """

    # Known AI/tech entities with their types
    KNOWN_ENTITIES: Dict[str, Dict[str, str]] = {
        # Companies
        "deepseek": {"name": "DeepSeek", "type": "company"},
        "openai": {"name": "OpenAI", "type": "company"},
        "anthropic": {"name": "Anthropic", "type": "company"},
        "google": {"name": "Google", "type": "company"},
        "meta": {"name": "Meta", "type": "company"},
        "microsoft": {"name": "Microsoft", "type": "company"},
        "百度": {"name": "百度", "type": "company"},
        "阿里": {"name": "阿里巴巴", "type": "company"},
        "阿里巴巴": {"name": "阿里巴巴", "type": "company"},
        "腾讯": {"name": "腾讯", "type": "company"},
        "字节跳动": {"name": "字节跳动", "type": "company"},
        "字节": {"name": "字节跳动", "type": "company"},
        "华为": {"name": "华为", "type": "company"},
        "商汤": {"name": "商汤科技", "type": "company"},
        "moonshot": {"name": "Moonshot AI", "type": "company"},
        "月之暗面": {"name": "Moonshot AI", "type": "company"},
        "智谱": {"name": "智谱AI", "type": "company"},
        "百川": {"name": "百川智能", "type": "company"},
        "零一万物": {"name": "零一万物", "type": "company"},
        "minimax": {"name": "MiniMax", "type": "company"},
        "阶跃星辰": {"name": "阶跃星辰", "type": "company"},

        # Products
        "gpt-4": {"name": "GPT-4", "type": "product"},
        "gpt-5": {"name": "GPT-5", "type": "product"},
        "gpt4": {"name": "GPT-4", "type": "product"},
        "claude": {"name": "Claude", "type": "product"},
        "gemini": {"name": "Gemini", "type": "product"},
        "llama": {"name": "Llama", "type": "product"},
        "mistral": {"name": "Mistral", "type": "product"},
        "文心一言": {"name": "文心一言", "type": "product"},
        "通义千问": {"name": "通义千问", "type": "product"},
        "kimi": {"name": "Kimi", "type": "product"},
        "豆包": {"name": "豆包", "type": "product"},
        "星火": {"name": "星火", "type": "product"},
        "deepseek-v3": {"name": "DeepSeek-V3", "type": "product"},
        "deepseek-r1": {"name": "DeepSeek-R1", "type": "product"},
        "glm-4": {"name": "GLM-4", "type": "product"},
        "qwen": {"name": "Qwen", "type": "product"},
        "千问": {"name": "Qwen", "type": "product"},

        # Concepts
        "rag": {"name": "RAG", "type": "concept"},
        "agent": {"name": "AI Agent", "type": "concept"},
        "多模态": {"name": "多模态", "type": "concept"},
        "思维链": {"name": "思维链(CoT)", "type": "concept"},
        "cot": {"name": "思维链(CoT)", "type": "concept"},
        "强化学习": {"name": "强化学习", "type": "concept"},
        "rlhf": {"name": "RLHF", "type": "concept"},
        "moe": {"name": "MoE", "type": "concept"},
        "transformer": {"name": "Transformer", "type": "concept"},
        "大模型": {"name": "大语言模型", "type": "concept"},
        "llm": {"name": "大语言模型", "type": "concept"},
    }

    # Company-Product relationships
    PRODUCT_OWNERS: Dict[str, str] = {
        "GPT-4": "OpenAI",
        "GPT-5": "OpenAI",
        "Claude": "Anthropic",
        "Gemini": "Google",
        "Llama": "Meta",
        "文心一言": "百度",
        "通义千问": "阿里巴巴",
        "Kimi": "Moonshot AI",
        "豆包": "字节跳动",
        "DeepSeek-V3": "DeepSeek",
        "DeepSeek-R1": "DeepSeek",
        "GLM-4": "智谱AI",
        "Qwen": "阿里巴巴",
    }

    def __init__(self, query: str = ""):
        self.query = query
        self._entity_map: Dict[str, Entity] = {}
        self._relations: List[EntityRelation] = []
        self._cooccurrence: Dict[Tuple[str, str], int] = Counter()

    def _generate_id(self, name: str) -> str:
        """Generate a stable ID for an entity"""
        return hashlib.md5(name.lower().encode()).hexdigest()[:8]

    def _normalize_name(self, name: str) -> Optional[Dict[str, str]]:
        """Normalize entity name and get its info"""
        key = name.lower().strip()
        return self.KNOWN_ENTITIES.get(key)

    def _extract_entities_from_text(self, text: str) -> List[str]:
        """Extract potential entity names from text"""
        found = []
        text_lower = text.lower()

        # Check known entities
        for key, info in self.KNOWN_ENTITIES.items():
            if key in text_lower:
                found.append(info["name"])

        return list(set(found))

    def _add_entity(self, name: str, entity_type: str) -> Entity:
        """Add or update an entity"""
        entity_id = self._generate_id(name)

        if entity_id in self._entity_map:
            self._entity_map[entity_id].mentions += 1
        else:
            self._entity_map[entity_id] = Entity(
                id=entity_id,
                name=name,
                type=entity_type,
                mentions=1,
            )

        return self._entity_map[entity_id]

    def _add_cooccurrence(self, entity1: str, entity2: str):
        """Record co-occurrence of two entities"""
        if entity1 == entity2:
            return

        # Sort to ensure consistent key
        pair = tuple(sorted([entity1, entity2]))
        self._cooccurrence[pair] += 1

    def process_data(self, data: List[Dict[str, Any]]) -> EntityGraph:
        """
        Process collected data and generate entity graph.

        Args:
            data: List of collected items (search results)

        Returns:
            EntityGraph with entities and relations
        """
        from datetime import datetime

        # Reset state
        self._entity_map = {}
        self._relations = []
        self._cooccurrence = Counter()

        # Add query as center topic if provided
        center_entity_id = None
        if self.query:
            center = self._add_entity(self.query, "topic")
            center_entity_id = center.id

        # Process each data item
        for item in data:
            # Combine all text fields
            text = " ".join([
                item.get("title", "") or "",
                item.get("content", "") or "",
                item.get("summary", "") or "",
            ])

            # Extract entities
            entities_in_item = self._extract_entities_from_text(text)

            # Add entities and record co-occurrences
            for name in entities_in_item:
                info = self._normalize_name(name)
                if info:
                    self._add_entity(info["name"], info["type"])

                    # Co-occurrence with other entities in same item
                    for other_name in entities_in_item:
                        if other_name != name:
                            other_info = self._normalize_name(other_name)
                            if other_info:
                                self._add_cooccurrence(info["name"], other_info["name"])

        # Build relations from co-occurrences
        self._build_relations_from_cooccurrence()

        # Add product-owner relations
        self._add_product_owner_relations()

        # Create graph
        graph = EntityGraph(
            entities=list(self._entity_map.values()),
            relations=self._relations,
            center_entity=center_entity_id,
            generated_at=datetime.now().isoformat(),
        )

        return graph

    def _build_relations_from_cooccurrence(self):
        """Build relations based on co-occurrence counts"""
        if not self._cooccurrence:
            return

        max_count = max(self._cooccurrence.values()) if self._cooccurrence else 1

        for (name1, name2), count in self._cooccurrence.items():
            id1 = self._generate_id(name1)
            id2 = self._generate_id(name2)

            # Only add if both entities exist
            if id1 in self._entity_map and id2 in self._entity_map:
                # Normalize strength based on max count
                strength = min(1.0, 0.3 + (count / max_count) * 0.7)

                self._relations.append(EntityRelation(
                    source_id=id1,
                    target_id=id2,
                    relation_type="related",
                    strength=strength,
                ))

    def _add_product_owner_relations(self):
        """Add ownership relations between products and companies"""
        for product_name, company_name in self.PRODUCT_OWNERS.items():
            product_id = self._generate_id(product_name)
            company_id = self._generate_id(company_name)

            # Only add if both exist in our graph
            if product_id in self._entity_map and company_id in self._entity_map:
                self._relations.append(EntityRelation(
                    source_id=company_id,
                    target_id=product_id,
                    relation_type="owns",
                    strength=1.0,
                ))


def generate_entity_graph(
    data: List[Dict[str, Any]],
    query: str = "",
) -> Dict[str, Any]:
    """
    Generate entity graph from collected data.

    Args:
        data: Collected search results
        query: Original query (becomes center node)

    Returns:
        Entity graph as dictionary
    """
    generator = EntityGraphGenerator(query)
    graph = generator.process_data(data)
    return graph.to_dict()
