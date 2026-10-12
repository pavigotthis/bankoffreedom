"""Import a supplied workflow as private server data, never executable instructions."""

import hashlib
import json
import re

LABELS = [
    "Evidence Classifier",
    "Persona Identifier",
    "Empathy and Need Mapper",
    "User-Journey Mapper",
]
PERSONA_DETAILS = ["goals", "pain_points", "behavioral_traits", "trust_requirements"]
EMPATHY_CATEGORIES = [
    "Says",
    "Thinks",
    "Does",
    "Feels",
    "Sees",
    "Hears",
    "Pains",
    "Gains",
    "Functional jobs",
    "Emotional jobs",
    "Social jobs",
    "explicit needs",
    "latent needs",
    "trust needs",
    "privacy needs",
    "support needs",
]
EMPATHY_FACTORS = [
    "warmth",
    "engagement",
    "discovery quality",
    "convenience",
    "parent transparency",
    "student privacy",
    "psychological safety",
    "continuity",
]
JOURNEY_FIELDS = [
    "goals",
    "actions",
    "touchpoints",
    "thoughts",
    "emotions",
    "pain points",
    "needs",
    "evidence required",
    "decisions",
    "risks",
    "failure points",
    "success measures",
    "moments of truth",
    "drop-off risks",
    "conflicts",
    "warmth points",
    "automation opportunities",
]
STUDENT_FIELDS = {
    "Student Responses": "response",
    "Academic Information": "academic information",
    "Activities and Interests": "activity",
    "Student Career Preferences": "career preference",
    "Strengths": "strength",
    "Work Values": "work value",
    "Work Style": "work style",
    "Lifestyle Preferences": "lifestyle preference",
    "Financial Constraints": "financial constraint",
    "Geographical Constraints": "geographical constraint",
}
PARENT_FIELDS = {"Parent Responses": "response", "Parent Career Preferences": "career preference"}


def parse_export(raw):
    if len(raw) > 1024 * 1024:
        raise ValueError("Workflow export is too large")
    try:
        body = json.loads(raw)
        nodes = body["Nodes"]
        edges = body["Edges"]
        if not isinstance(nodes, list) or len(nodes) > 100 or not isinstance(edges, list):
            raise ValueError("Invalid workflow graph")
        by_label = {n["label"]: n for n in nodes}
        if len({n["id"] for n in nodes}) != len(nodes):
            raise ValueError("Duplicate node IDs")
        intake = by_label["Input Collection"]["HumanInputNode"]["Fields"]
        if len({f["label"] for f in intake}) != len(intake):
            raise ValueError("Duplicate intake labels")
        if not set(STUDENT_FIELDS | PARENT_FIELDS) <= {f["label"] for f in intake}:
            raise ValueError("Required intake field definitions are missing")
        steps = []
        for n, label in enumerate(LABELS, 1):
            node = by_label[label]
            agent = node["AgentNode"]
            steps.append(
                {
                    "step": n,
                    "node_id": node["id"],
                    "label": label,
                    "prompt": agent["prompt"],
                    "system": agent["Agent"]["system"],
                }
            )
        prompt = steps[1]["prompt"]
        student = re.search(r"student options \(([^)]+)\)", prompt)
        parent = re.search(r"parent options \(([^)]+)\)", prompt)
        if not student or not parent:
            raise ValueError("Explicit persona option lists are missing")
        empathy_prompt = steps[2]["prompt"]
        required_groups = [
            "Says, Thinks, Does, Feels, Sees, Hears, Pains, Gains",
            "Functional/Emotional/Social jobs",
            "explicit/latent/trust/privacy/support needs",
        ]
        if not all(group in empathy_prompt for group in required_groups):
            raise ValueError("Unrecognized empathy categories; explicit review is required")
        fields = [
            {k: f[k] for k in ("id", "label", "required", "order", "type")}
            for f in sorted(intake, key=lambda x: x["order"])
        ]
        field_ids = {f["id"] for f in fields}
        step_ids = {s["node_id"] for s in steps}
        if len(field_ids) != len(fields):
            raise ValueError("Duplicate intake field IDs")
        for step in steps:
            if (
                not set(re.findall(r"workflowHumanInputFieldId=([a-zA-Z0-9]+)", step["prompt"]))
                <= field_ids
            ):
                raise ValueError("Mapping prompt references a missing intake field")
            if not set(re.findall(r"workflowNodeId=([a-zA-Z0-9]+)", step["prompt"])) <= step_ids:
                raise ValueError(
                    "Requested four-step prompt depends on an excluded or missing node"
                )
        if any(f["type"] != "TEXT" for f in fields):
            raise ValueError("Only the supplied text intake contract is supported")
        ids = {n["id"] for n in nodes}
        dangling = sorted(
            {e[k] for e in edges for k in ("sourceNodeId", "targetNodeId") if e[k] not in ids}
        )
        referenced = set(re.findall(r"workflowNodeId=([a-zA-Z0-9]+)", raw.decode()))
        missing_refs = sorted(referenced - ids)
        return {
            "title": body.get("title", "Imported mapping workflow"),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "steps": steps,
            "fields": fields,
            "student_personas": [x.strip() for x in student[1].split(",")],
            "parent_personas": [x.strip() for x in parent[1].split(",")],
            "empathy_categories": EMPATHY_CATEGORIES,
            "empathy_factors": EMPATHY_FACTORS,
            "journey_fields": JOURNEY_FIELDS,
            "journey_stages": [],
            "remaining": [
                "Exact eighteen journey stage names and order",
                "Assessment, interview and activity readiness criteria",
                "Classification taxonomy/confidence calibration",
                "AI provider credentials",
            ],
            "excluded_nodes": [
                n["label"] for n in nodes if n["label"] not in LABELS + ["Input Collection"]
            ],
            "missing_referenced_nodes": missing_refs,
            "dangling_edges": dangling,
            "adapter_notes": [
                "Slash-group empathy categories expanded into individual labels",
                "JSON schemas are engineering adapters, not supplied validated instruments",
                "All eighteen journey stages remain missing; no production substitutions",
            ],
        }
    except (KeyError, TypeError, AttributeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid or incomplete MindPal export") from exc


def supplement_mapping(spec, raw_prompt):
    """Read only the four named sections; other pasted instructions cannot expand scope."""
    if len(raw_prompt) > 1024 * 1024:
        raise ValueError("Mapping prompt is too large")
    text = raw_prompt.decode("utf-8-sig").replace("\r\n", "\n")
    sections = {}
    for number, title, content in re.findall(
        r"^# \d+\. Node (\d+): ([^\n]+)\n(.*?)(?=^# \d+\.|\Z)", text, re.M | re.S
    ):
        if int(number) in range(1, 5):
            sections[int(number)] = (title.strip(), content.strip())
    if set(sections) != {1, 2, 3, 4} or [sections[n][0] for n in range(1, 5)] != LABELS:
        raise ValueError("All four exact mapping sections are required")
    stages_match = re.search(
        r"Use these stages:\s*(.*?)(?=For every stage show:)", sections[4][1], re.S
    )
    if not stages_match:
        raise ValueError("Explicit eighteen journey stages are required")
    numbered = re.findall(r"^(\d+)\. (.+)$", stages_match[1], re.M)
    if [int(n) for n, _ in numbered] != list(range(1, 19)) or len(
        {label for _, label in numbered}
    ) != 18:
        raise ValueError("Journey stages must be eighteen distinct names in explicit order")

    def bullets(content, start, end):
        part = content.split(start, 1)[1].split(end, 1)[0]
        result = re.findall(r"^- (.+)$", part, re.M)
        if not result:
            raise ValueError("Required mapping enumeration is empty")
        return result

    try:
        for role, start, end in [
            ("student", "Student persona options:", "Parent persona options:"),
            ("parent", "Parent persona options:", "For each selected persona show:"),
        ]:
            values = bullets(sections[2][1], start, end)
            if values != spec[role + "_personas"]:
                raise ValueError("Persona lists conflict between export and supplied prompt")
        evidence_types = bullets(sections[1][1], "Evidence types:", "Output a table")
        categories = bullets(sections[3][1], "Include:", "For every insight show:")
        fields = bullets(sections[4][1], "For every stage show:", "Mark:")
        markers = bullets(sections[4][1], "Mark:", "__END__")
        factors = bullets(sections[3][1], "Separate these concepts:", "Define warmth as:")
        warmth = bullets(sections[3][1], "Define warmth as:", "__END__")
    except (IndexError, KeyError) as exc:
        raise ValueError("Incomplete supplied mapping prompt") from exc
    if "Allow blank inputs." not in text:
        raise ValueError("Blank-input behavior must be explicit")
    result = dict(spec)
    result["export_sha256"] = spec["sha256"]
    result["prompt_sha256"] = hashlib.sha256(raw_prompt).hexdigest()
    result["sha256"] = hashlib.sha256(
        (spec["sha256"] + result["prompt_sha256"]).encode()
    ).hexdigest()
    result["journey_stages"] = [label for _, label in numbered]
    result["journey_fields"] = fields + markers
    result["empathy_categories"] = categories
    result["empathy_factors"] = factors + ["Psychological safety", "Continuity across interactions"]
    result["warmth_definition"] = warmth
    result["evidence_types"] = evidence_types
    result["persona_details"] = [
        "goals",
        "pain_points",
        "functional_needs",
        "emotional_needs",
        "social_needs",
        "decision_behaviour",
        "trust_requirements",
    ]
    result["fields"] = [dict(field, required=False) for field in spec["fields"]]
    result["steps"] = [dict(step, prompt=sections[step["step"]][1]) for step in spec["steps"]]
    result["remaining"] = [
        "Assessment/interview/activity readiness criteria",
        "Confidence calibration",
        "AI provider credentials/model",
        "Live-data policy and linking readiness",
    ]
    result["adapter_notes"] = [
        "Exact mapping prompt supplements exported abbreviated instructions",
        "Blank inputs allowed; missing evidence retained",
        "Only four mapping nodes active",
        "Analytical shortlisting/alignment stage names do not activate ranking or scores",
    ]
    return result


def intake_context(snapshot, spec):
    fields: dict[str, list] = {
        f["label"]: [] for f in spec["fields"] if f["label"] != "Mentor Database"
    }
    for row in snapshot["evidence"]:
        label = row["source"].removeprefix("Intake: ").split(" [actor=", 1)[0]
        if label in fields:
            fields[label].append(
                {
                    "evidence_id": row["id"],
                    "stakeholder": row["stakeholder"],
                    "statement": row["statement"],
                }
            )
    return fields


def compiled_instructions(step, spec):
    """Replace platform-specific references using stable IDs, without running the graph."""
    field_ids = {f["id"]: f["label"] for f in spec["fields"]}
    node_ids = {s["node_id"]: str(s["step"]) for s in spec["steps"]}

    def replace(match):
        kind, key = match[1], match[2]
        if kind == "WORKFLOW_HUMAN_INPUT_FIELD":
            return "input.intake_fields[" + json.dumps(field_ids[key]) + "]"
        return "input.upstream[" + json.dumps(node_ids[key]) + "]"

    prompt = re.sub(
        r"@\[[^\]]+\]\(type=(WORKFLOW_HUMAN_INPUT_FIELD|WORKFLOW_NODE)&(?:workflowHumanInputFieldId|workflowNodeId)=([a-zA-Z0-9]+)\)",
        replace,
        spec["steps"][step - 1]["prompt"],
    )
    return spec["steps"][step - 1]["system"] + "\n\n" + prompt


def report_draft(outputs, concise=False):
    """Explicit six-map preview, excluding source evidence, confidence and private factors."""
    maps: dict[str, dict] = {}
    for role in ["student", "parent"]:
        hypothesis = outputs[2][role]["selected_hypothesis"]
        maps[role + "_persona"] = {
            "summary": "Provisional summary: "
            + (hypothesis or "Insufficient evidence for a persona"),
            "items": [],
        }
        maps[role + "_empathy"] = {
            "summary": "A provisional empathy and needs summary.",
            "items": [{"label": row["category"], "text": row["text"]} for row in outputs[3][role]],
        }
        maps[role + "_journey"] = {
            "summary": "An exploration journey based on the available information.",
            "items": [
                {
                    "label": row["stage"],
                    "text": "\n".join(
                        key.title() + ": " + row["fields"][key]
                        for key in [
                            "goals",
                            "actions",
                            "touchpoints",
                            "needs",
                            "Stakeholder goal",
                            "Action",
                            "Touchpoint",
                            "Need",
                        ]
                        if key in row["fields"]
                    ),
                }
                for row in outputs[4][role]
            ],
        }
    if concise:
        for role in ["student", "parent"]:
            maps[role + "_journey"] = {
                "summary": "Journey summary requires admin editing before approval.",
                "items": [],
            }
    return maps
