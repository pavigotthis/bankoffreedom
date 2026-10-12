"""Private, provider-independent 3DU configuration adapter. No MindPal runtime."""

import hashlib
import json

from .domain import MAP_KEYS, STAGES
from .mindpal import EMPATHY_FACTORS, PERSONA_DETAILS

STEP_IDS = [
    "evidence_classifier",
    "persona_identifier",
    "empathy_need_mapper",
    "user_journey_mapper",
]
MANDATORY = {
    "student": [
        "Student Responses",
        "Academic Information",
        "Activities and Interests",
        "Student Career Preferences",
        "Strengths",
        "Work Values",
        "Work Style",
        "Lifestyle Preferences",
        "Financial Constraints",
        "Geographical Constraints",
    ],
    "parent": ["Parent Responses", "Parent Career Preferences"],
    "mentor": ["Mentor Notes"],
    "educator": ["Educator Notes"],
}


def parse_configuration(raw):
    if len(raw) > 1024 * 1024:
        raise ValueError("Configuration exceeds the private upload limit")
    try:
        c = json.loads(raw)
        if c["format"] != "3du.mapping.configuration" or c["schema_version"] != 1:
            raise ValueError("Unsupported standalone format/version")
        if c["runtime"]["mindpal_required"] is not False:
            raise ValueError("A MindPal runtime dependency is prohibited")
        if [s["id"] for s in c["steps"]] != STEP_IDS:
            raise ValueError("Exactly four ordered mapping steps are required")
        for i, s in enumerate(c["steps"]):
            if s["order"] != i + 1 or s["depends_on"] != STEP_IDS[:i]:
                raise ValueError("Invalid step order or dependencies")
            for k in ["system_instructions", "task_instructions", "label"]:
                if not isinstance(s[k], str) or not s[k].strip():
                    raise ValueError("Missing private mapping instructions")
        d = c["definitions"]
        for k, count in [
            ("student_personas", 8),
            ("parent_personas", 5),
            ("empathy_categories", 17),
            ("evidence_types", 10),
            ("internal_journey_stages", 18),
            ("journey_stage_fields", 16),
            ("journey_markers", 6),
        ]:
            values = d[k]
            if (
                not isinstance(values, list)
                or len(values) != count
                or any(not isinstance(v, str) or not v.strip() or len(v) > 500 for v in values)
                or len(set(values)) != count
            ):
                raise ValueError("Invalid supplied enumeration: " + k)
        fields = c["inputs"]
        if len(fields) != 15 or len({f["id"] for f in fields}) != 15:
            raise ValueError("Fifteen unique role-owned inputs are required")
        for role, labels in MANDATORY.items():
            found = [f for f in fields if f["author_scope"] == role]
            if {f["label"] for f in found} != set(labels):
                raise ValueError("Input ownership mismatch for " + role)
            if any(f["type"] != "text" or f["required_for_submission"] is not True for f in found):
                raise ValueError("Mandatory text input required for " + role)
        educator = next(f for f in fields if f["label"] == "Educator Notes")
        if educator["activation"] != "blocked_pending_educator_scope":
            raise ValueError("Educator scope must remain blocked pending approval")
        previous = next(f for f in fields if f["label"] == "Previous Interaction Notes")
        if previous["required_for_submission"] is not False or previous["author_scope"] != [
            "involved_mentor",
            "authorized_educator",
            "assigned_admin",
        ]:
            raise ValueError("Previous interaction notes must be optional and staff-owned")
        r = c["public_report"]
        if (
            r["output_keys"] != MAP_KEYS
            or r["view_only"] is not True
            or r["identical_version_and_content"] is not True
            or r["expose_full_eighteen_stage_map"] is not False
            or r["evidence_classifier_public"] is not False
        ):
            raise ValueError("Six safe shared view-only outputs are required")
        p = c["publication"]
        if (
            p["initial_approval_order"] != ["assigned_admin", "involved_mentor"]
            or p["later_approvals"] != ["assigned_admin"]
            or p["same_exact_version_required"] is not True
            or p["no_mentor_bypass"] is not True
        ):
            raise ValueError("Initial exact-version two-approval rule cannot change")
        if c["portal"]["stage_names"] != STAGES or c["portal"]["always_accessible_stage"] != 9:
            raise ValueError("The nine-stage navigation cannot change")
        if (
            c["submission"]["maximum_submissions_per_entry"] != 2
            or c["submission"]["resubmission_updates_existing_entry"] is not True
        ):
            raise ValueError("Only one resubmission on the same entry is allowed")
        if any(k in c["runtime"] for k in ["api_key", "password", "token"]):
            raise ValueError("Use secure server-side environment credentials")
        return {
            "kind": "3du-standalone",
            "title": "3DU independent mapping configuration",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "contract": c,
            "steps": [
                {
                    "step": s["order"],
                    "node_id": s["id"],
                    "label": s["label"],
                    "system": s["system_instructions"],
                    "prompt": s["task_instructions"],
                }
                for s in c["steps"]
            ],
            "fields": [
                {
                    "id": f["id"],
                    "label": f["label"],
                    "type": "TEXT",
                    "required": f["required_for_submission"],
                }
                for f in fields
            ],
            "student_personas": d["student_personas"],
            "parent_personas": d["parent_personas"],
            "empathy_categories": d["empathy_categories"],
            "journey_stages": d["internal_journey_stages"],
            "journey_fields": d["journey_stage_fields"] + d["journey_markers"],
            "evidence_types": d["evidence_types"],
            "persona_details": PERSONA_DETAILS
            + ["functional_needs", "emotional_needs", "social_needs", "decision_behaviour"],
            "empathy_factors": EMPATHY_FACTORS,
            "remaining": c["unresolved"],
            "excluded_nodes": c["excluded"],
        }
    except (KeyError, TypeError, StopIteration, json.JSONDecodeError) as exc:
        raise ValueError("Malformed or incomplete standalone configuration") from exc


def apply_to_config(c, spec):
    c = dict(c)
    for key in [
        "student_personas",
        "parent_personas",
        "empathy_categories",
        "journey_stages",
        "journey_fields",
    ]:
        c[key] = spec[key]
    c["mapping_profile"] = {"kind": "3du-standalone", "source_sha256": spec["sha256"]}
    c["mapping_details"] = {
        k: spec[k] for k in ["evidence_types", "persona_details", "empathy_factors"]
    }
    return c
