"""Confirmed domain constants; absent product specifications stay absent."""

from typing import Any

from jsonschema import Draft202012Validator

STAGES = [
    "Create Profile",
    "Take Assessments",
    "Discover Interests & Strengths",
    "Explore Career Paths",
    "Find Relevant Mentors",
    "Attend Sessions",
    "Complete Activities",
    "Get to know yourself",
    "Track Progress",
]
LOCKED = "This stage will open once you complete the previous stage."
PENDING = "Your mentor and the 3DU team are reviewing your insights. Your results will appear here once approved."
MAP_KEYS = [
    "student_persona",
    "parent_persona",
    "student_empathy",
    "parent_empathy",
    "student_journey",
    "parent_journey",
]
EVIDENCE_TYPES = [
    "fact",
    "preference",
    "behavior",
    "quotation",
    "constraint",
    "expectation",
    "assumption",
    "contradiction",
    "missing evidence",
]
INPUT_TYPES = [
    "response",
    "educator note",
    "mentor note",
    "academic information",
    "activity",
    "interest",
    "career preference",
    "strength",
    "work value",
    "work style",
    "lifestyle preference",
    "financial constraint",
    "geographical constraint",
    "previous interaction note",
]
DEFAULT_CONFIG: dict[str, Any] = {
    "stage_rules": {},
    "readiness": None,
    "student_personas": [],
    "parent_personas": [],
    "empathy_categories": [],
    "journey_stages": [],
    "journey_fields": [],
}


def obj(props, required=None):
    return {
        "type": "object",
        "properties": props,
        "required": required if required is not None else list(props),
        "additionalProperties": False,
    }


TEXT = {"type": "string", "maxLength": 20000}
SHORT = {"type": "string", "minLength": 1, "maxLength": 500}
STRINGS = {"type": "array", "items": SHORT, "maxItems": 100}
CONF = {"type": "number", "minimum": 0, "maximum": 1}
IDS = {
    "type": "array",
    "items": {"type": "integer", "minimum": 1},
    "uniqueItems": True,
    "maxItems": 500,
}


def validate(schema, value):
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda e: str(e.path))
    if errors:
        e = errors[0]
        raise ValueError(f"{'/'.join(map(str, e.path)) or 'data'}: {e.message}")
    return value


def config_validate(c):
    rule = obj(
        {
            "approvers": {
                "type": "array",
                "items": {"enum": ["admin", "mentor"]},
                "minItems": 1,
                "uniqueItems": True,
            },
            "requires_submission": {"type": "boolean"},
            "required_draft_fields": STRINGS,
            "description": SHORT,
        }
    )
    ready = obj(
        {
            "required_stages": {
                "type": "array",
                "items": {"type": "integer", "minimum": 1, "maximum": 8},
                "minItems": 1,
                "uniqueItems": True,
            },
            "assessment_criterion": SHORT,
            "mentor_interview_criterion": SHORT,
            "activity_criterion": SHORT,
        }
    )
    validate(
        obj(
            {
                "mapping_details": obj(
                    {
                        "evidence_types": STRINGS,
                        "persona_details": STRINGS,
                        "empathy_factors": STRINGS,
                    }
                ),
                "mapping_profile": obj(
                    {"kind": {"const": "mindpal-four-step"}, "source_sha256": SHORT}
                ),
                "stage_rules": {
                    "type": "object",
                    "patternProperties": {"^[1-8]$": rule},
                    "additionalProperties": False,
                },
                "readiness": {"anyOf": [{"type": "null"}, ready]},
                "student_personas": STRINGS,
                "parent_personas": STRINGS,
                "empathy_categories": STRINGS,
                "journey_stages": {
                    "type": "array",
                    "items": SHORT,
                    "maxItems": 18,
                    "uniqueItems": True,
                },
                "journey_fields": STRINGS,
            },
            required=list(DEFAULT_CONFIG),
        ),
        c,
    )
    for k in ["student_personas", "parent_personas", "empathy_categories", "journey_fields"]:
        if len(c[k]) != len(set(c[k])):
            raise ValueError(f"{k}: duplicates are not permitted")
    if c["journey_stages"] and len(c["journey_stages"]) != 18:
        raise ValueError("Exactly eighteen analytical journey stages are required")
    return c


def mapping_gaps(c, step=None):
    required = {
        1: [],
        2: ["student_personas", "parent_personas"],
        3: ["empathy_categories"],
        4: ["journey_fields"],
    }
    if step is not None:
        return [k for k in required[step] if not c[k]] + (
            ["eighteen journey_stages"] if step == 4 and len(c["journey_stages"]) != 18 else []
        )
    return [
        k
        for k in ["student_personas", "parent_personas", "empathy_categories", "journey_fields"]
        if not c[k]
    ] + ([] if len(c["journey_stages"]) == 18 else ["eighteen journey_stages"])


def step_schema(n, c):
    trace = {
        "supporting_evidence": IDS,
        "confidence": CONF,
        "missing_evidence": STRINGS,
        "assumptions_to_validate": STRINGS,
    }
    if n == 1:
        row = obj(
            {
                "evidence_id": {"type": "integer"},
                "original_statement": TEXT,
                "stakeholder": {"enum": ["student", "parent", "educator", "mentor"]},
                "source": SHORT,
                "evidence_type": {
                    "enum": c.get("mapping_details", {}).get("evidence_types", EVIDENCE_TYPES)
                },
                "career_dimension": SHORT,
                "sentiment": SHORT,
                "confidence": CONF,
                "contradiction_status": SHORT,
            }
        )
        return obj({"evidence": {"type": "array", "items": row}, "gaps": STRINGS})
    if n == 2:

        def persona(role):
            return obj(
                dict(
                    trace,
                    selected_hypothesis={
                        "anyOf": [{"type": "null"}, {"enum": c[role + "_personas"]}]
                    },
                    alternatives={
                        "type": "array",
                        "items": {"enum": c[role + "_personas"]},
                        "uniqueItems": True,
                    },
                    needs=STRINGS,
                    barriers=STRINGS,
                )
            )

        result = obj({"student": persona("student"), "parent": persona("parent")})
        if c.get("mapping_profile"):
            from .mindpal import PERSONA_DETAILS

            for role in ["student", "parent"]:
                for key in c.get("mapping_details", {}).get("persona_details", PERSONA_DETAILS):
                    result["properties"][role]["properties"][key] = STRINGS
                    result["properties"][role]["required"].append(key)
        return result
    if n == 3:
        row = obj(
            dict(
                trace,
                category={"enum": c["empathy_categories"]},
                source=SHORT,
                text=TEXT,
                validation_status={"enum": ["needs validation", "reviewed"]},
            )
        )
        if c.get("mapping_details"):
            row["properties"]["insight_basis"] = {
                "enum": [
                    "supported by supplied evidence",
                    "assumption requiring validation",
                    "missing evidence",
                ]
            }
            row["required"].append("insight_basis")
        result = obj(
            {
                role: {
                    "type": "array",
                    "items": row,
                    "minItems": len(c["empathy_categories"]),
                    "maxItems": len(c["empathy_categories"]),
                }
                for role in ["student", "parent"]
            }
        )
        if c.get("mapping_profile"):
            from .mindpal import EMPATHY_FACTORS

            factor = obj(
                dict(
                    trace,
                    text=TEXT,
                    source=SHORT,
                    validation_status={"enum": ["needs validation", "reviewed"]},
                )
            )
            result["properties"]["factors"] = obj(
                {
                    role: obj(
                        {
                            key: factor
                            for key in c.get("mapping_details", {}).get(
                                "empathy_factors", EMPATHY_FACTORS
                            )
                        }
                    )
                    for role in ["student", "parent"]
                }
            )
            result["required"].append("factors")
        return result
    row = obj(
        dict(
            trace,
            stage={"enum": c["journey_stages"]},
            fields=obj({k: TEXT for k in c["journey_fields"]}),
        )
    )
    return obj(
        {
            role: {"type": "array", "items": row, "minItems": 18, "maxItems": 18}
            for role in ["student", "parent"]
        }
    )


def validate_output(n, c, out, inputs):
    validate(step_schema(n, c), out)
    records = {e["id"]: e for e in inputs}
    if n == 1:
        if len(out["evidence"]) != len(records) or {
            e["evidence_id"] for e in out["evidence"]
        } != set(records):
            raise ValueError("Every snapshot statement must appear exactly once")
        for e in out["evidence"]:
            r = records[e["evidence_id"]]
            if (
                any(e[k] != r[k] for k in ["stakeholder", "source"])
                or e["original_statement"] != r["statement"]
            ):
                raise ValueError("Original statement and source attribution must be preserved")
            if r["type"] == "assumption" and e["evidence_type"].lower() in ("fact", "stated fact"):
                raise ValueError("An assumption cannot become a fact")
            if r["type"] == "missing evidence" and e["evidence_type"].lower() != "missing evidence":
                raise ValueError("Missing evidence must remain explicitly missing")

    def refs(v):
        if isinstance(v, dict):
            for k, x in v.items():
                if k == "supporting_evidence" and not set(x) <= set(records):
                    raise ValueError("Unknown evidence reference")
                refs(x)
        elif isinstance(v, list):
            for x in v:
                refs(x)

    refs(out)
    if n == 2 and c.get("mapping_profile"):
        for role in ["student", "parent"]:
            persona = out[role]
            if persona["selected_hypothesis"] is not None and not any(
                records[i]["stakeholder"] == role
                and records[i]["type"] not in ("missing evidence", "assumption")
                and bool(records[i]["statement"].strip())
                for i in persona["supporting_evidence"]
            ):
                raise ValueError(
                    "A persona requires evidence from that stakeholder that is non-missing and not an assumption"
                )
            if persona["selected_hypothesis"] is None and not persona["missing_evidence"]:
                raise ValueError("An unselected persona must explain insufficient evidence")
    if n in (3, 4):
        key, options = (
            ("category", c["empathy_categories"]) if n == 3 else ("stage", c["journey_stages"])
        )
        for role in ["student", "parent"]:
            if [x[key] for x in out[role]] != options:
                raise ValueError("Categories/stages must match approved enumeration in order")
    return out


def validate_maps(c, maps):
    row = obj({"label": SHORT, "text": TEXT})
    validate(
        obj(
            {
                k: obj(
                    {"summary": SHORT, "items": {"type": "array", "items": row, "maxItems": 100}}
                )
                for k in MAP_KEYS
            }
        ),
        maps,
    )
    for role in ["student", "parent"]:
        if maps[role + "_persona"]["items"]:
            raise ValueError("Public persona uses a provisional summary only")
        for suffix, options in [
            ("empathy", c["empathy_categories"]),
            ("journey", c["journey_stages"]),
        ]:
            if [x["label"] for x in maps[role + "_" + suffix]["items"]] != options:
                raise ValueError("Public maps must match the supplied categories/stages")
    return maps
