"""
Generator: parses LLM output (JSON or text) into AssemblyIntent.
The LLM is constrained to output TEMPLATE INSTANTIATIONS, not raw coordinates.
"""

import json
import re
from typing import Dict, Any, Optional
from .ontology import AssemblyIntent, PartSpec, PartType, Relation, RelationType
from .templates import FullStationTemplate, VibrationFeederTemplate, GantryPickPlaceTemplate, FixtureStationTemplate


class IntentParser:
    """Parses LLM output into structured AssemblyIntent."""

    @staticmethod
    def from_json(text: str) -> Optional[AssemblyIntent]:
        """Parse JSON output from LLM."""
        try:
            # Extract JSON block if wrapped in markdown
            match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                text = match.group(1)
            data = json.loads(text)
            return IntentParser._dict_to_intent(data)
        except Exception as e:
            print(f"JSON parse error: {e}")
            return None

    @staticmethod
    def _dict_to_intent(data: Dict[str, Any]) -> AssemblyIntent:
        intent = AssemblyIntent()

        # Check if this is a template instantiation
        template_name = data.get("template")
        if template_name == "full_station":
            parts, rels = FullStationTemplate.create(data.get("params", {}))
            intent.parts.extend(parts)
            intent.relations.extend(rels)
        elif template_name == "vibration_feeder":
            parts, rels = VibrationFeederTemplate.create(data.get("name", "vib"), data.get("params", {}))
            intent.parts.extend(parts)
            intent.relations.extend(rels)
        elif template_name == "gantry_pick_place":
            parts, rels = GantryPickPlaceTemplate.create(data.get("name", "gantry"), data.get("params", {}))
            intent.parts.extend(parts)
            intent.relations.extend(rels)
        elif template_name == "fixture_station":
            parts, rels = FixtureStationTemplate.create(data.get("name", "fix"), data.get("params", {}))
            intent.parts.extend(parts)
            intent.relations.extend(rels)
        else:
            # Manual part definitions
            for part_data in data.get("parts", []):
                part = PartSpec(
                    name=part_data["name"],
                    part_type=PartType(part_data["type"]),
                    params=part_data.get("params", {}),
                )
                intent.parts.append(part)

            for rel_data in data.get("relations", []):
                rel = Relation(
                    rel_type=RelationType(rel_data["type"]),
                    source=rel_data["source"],
                    target=rel_data["target"],
                    axis=rel_data.get("axis"),
                    min_dist=rel_data.get("min_dist"),
                )
                intent.relations.append(rel)

        # Override/add global params
        intent.global_params.update(data.get("global_params", {}))
        return intent

    @staticmethod
    def from_natural_language(text: str) -> Optional[AssemblyIntent]:
        """
        Fallback: parse natural language into a best-effort intent.
        This is a simple heuristic parser for testing without LLM.
        """
        text_lower = text.lower()

        # Detect station type
        if "vibration" in text_lower or "bowl" in text_lower:
            if "gantry" in text_lower or "pick" in text_lower:
                return IntentParser._parse_full_station(text_lower)
            else:
                return IntentParser._parse_vibration_feeder(text_lower)
        elif "gantry" in text_lower:
            return IntentParser._parse_gantry(text_lower)
        elif "fixture" in text_lower:
            return IntentParser._parse_fixture(text_lower)

        return None

    @staticmethod
    def _parse_full_station(text: str) -> AssemblyIntent:
        params = {}
        # Extract dimensions
        w_match = re.search(r'(\d+)\s*mm?\s*wide', text)
        if w_match:
            params["station_width"] = int(w_match.group(1))
        d_match = re.search(r'(\d+)\s*mm?\s*deep', text)
        if d_match:
            params["station_depth"] = int(d_match.group(1))

        # Extract bowl diameter
        bowl_match = re.search(r'bowl\s*(?:dia)?\s*(\d+)', text)
        if bowl_match:
            params["bowl_diameter"] = int(bowl_match.group(1))

        # Extract gantry span
        span_match = re.search(r'span\s*(\d+)', text)
        if span_match:
            params["gantry_span"] = int(span_match.group(1))

        # Extract stroke
        stroke_match = re.search(r'stroke\s*(\d+)', text)
        if stroke_match:
            params["vertical_stroke"] = int(stroke_match.group(1))

        parts, relations = FullStationTemplate.create(params)
        intent = AssemblyIntent()
        intent.parts.extend(parts)
        intent.relations.extend(relations)
        return intent

    @staticmethod
    def _parse_vibration_feeder(text: str) -> AssemblyIntent:
        params = {}
        bowl_match = re.search(r'(\d+)\s*mm?\s*(?:dia|diameter)', text)
        if bowl_match:
            params["bowl_diameter"] = int(bowl_match.group(1))
        parts, relations = VibrationFeederTemplate.create("vib", params)
        intent = AssemblyIntent()
        intent.parts.extend(parts)
        intent.relations.extend(relations)
        return intent

    @staticmethod
    def _parse_gantry(text: str) -> AssemblyIntent:
        params = {}
        span_match = re.search(r'span\s*(\d+)', text)
        if span_match:
            params["span"] = int(span_match.group(1))
        h_match = re.search(r'height\s*(\d+)', text)
        if h_match:
            params["column_height"] = int(h_match.group(1))
        parts, relations = GantryPickPlaceTemplate.create("gantry", params)
        intent = AssemblyIntent()
        intent.parts.extend(parts)
        intent.relations.extend(relations)
        return intent

    @staticmethod
    def _parse_fixture(text: str) -> AssemblyIntent:
        parts, relations = FixtureStationTemplate.create("fix", {})
        intent = AssemblyIntent()
        intent.parts.extend(parts)
        intent.relations.extend(relations)
        return intent


def build_intent_from_llm_output(llm_text: str) -> Optional[AssemblyIntent]:
    """Main entry point: try JSON first, then NL fallback."""
    intent = IntentParser.from_json(llm_text)
    if intent is not None:
        return intent
    return IntentParser.from_natural_language(llm_text)
