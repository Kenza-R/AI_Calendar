#!/usr/bin/env python3
"""
Test script for assessment parser
"""

import sys
import os
from pathlib import Path
import re
from typing import List, Dict, Optional
import json

# ---------------------------------------------------------------------
# 0. Project path & env setup
# ---------------------------------------------------------------------
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Change to backend dir so .env etc. load correctly
os.chdir(backend_dir)

from app.config import settings
from openai import OpenAI
from app.utils.pdf_parser import parse_pdf, parse_text_document

# ---------------------------------------------------------------------
# 1. OpenAI client
# ---------------------------------------------------------------------
api_key_valid = settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-")
client = OpenAI(api_key=settings.OPENAI_API_KEY) if api_key_valid else None

# ---------------------------------------------------------------------
# 2. Regex helpers
# ---------------------------------------------------------------------

ASSESSMENT_HEADING_REGEX = re.compile(
    r"^(TESTS|ASSESSMENT METHODS|ASSESSMENT|EVALUATION|GRADING)\b",
    re.IGNORECASE | re.MULTILINE,
)

SECTION_BREAK_REGEX = re.compile(
    r"^(ATTENDANCE|DETAILED SCHEDULE|COURSE ETIQUETTE|HONOR CODE|TEXTBOOKS AND REQUIRED READINGS)\b",
    re.IGNORECASE | re.MULTILINE,
)


def extract_assessment_section(text: str) -> Optional[str]:
    """
    Try to extract only the assessment / tests section.
    If not found, return None.
    """
    m = ASSESSMENT_HEADING_REGEX.search(text)
    if not m:
        return None

    start = m.start()

    # find next major section
    m2 = SECTION_BREAK_REGEX.search(text, pos=start + 1)
    if m2:
        section = text[start:m2.start()].strip()
    else:
        section = text[start:].strip()

    if len(section) < 80:
        return None

    return section


# ---------------------------------------------------------------------
# 3. LLM helper to ENRICH each component with extra details
# ---------------------------------------------------------------------

def enrich_component_with_details(
    component: Dict,
    syllabus_text: str,
) -> Dict:
    """
    Second LLM pass:
    - Look through the (assessment-related) syllabus text.
    - Find where THIS component is described in more detail.
    - Enrich: description, keywords, count, raw_text.
    - DO NOT change: component_id, name, weight_percent, applies_to.
    """

    if not client:
        return component

    comp_json = json.dumps(component, ensure_ascii=False)

    prompt = f"""
You are given an extracted ASSESSMENT COMPONENT from a university syllabus,
and the syllabus TEXT (focusing mostly on assessment / tests).

Your job: enrich this component with ALL relevant details that the text
contains about it.

VERY IMPORTANT:
- DO NOT change these fields:
  - component_id
  - name
  - weight_percent
  - applies_to
- You MAY update:
  - type (if you can classify it more precisely)
  - count (e.g. number of deliverables, such as "two PPT presentations")
  - description (include case names, whether it is group work, etc.)
  - keywords (add all important names: cases like "Pacific Review – Disney/Pixar",
    "Global Supply Chain Management simulation", etc.)
  - raw_text (short excerpt where this component is described in most detail)

HOW TO THINK ABOUT IT:
- Search the TEXT for sentences or paragraphs that clearly describe this component.
- Often, the grading table lists just the name + %, but later paragraphs
  explain details, e.g.:

  - Strategy business simulation 20%
    Later: "Strategy simulation. Group assignment around the case 'Pacific Review – Disney/Pixar'.
            Two PPT presentations, each graded and each counting for 10% of the final grade."

  In that case:
  - Keep weight_percent = 20
  - Set count = 2 (two PPTs)
  - Ensure description mentions the Pacific Review – Disney/Pixar case and PPT presentations.
  - Add keywords like ["strategy simulation", "Pacific Review", "Disney", "Pixar", "PPT"].

- Do similar enrichment for:
  - Operations business simulation
  - Real-world case analysis
  - Peer evaluation
  - Participation
  - Final written exam

OUTPUT:
- Return ONE SINGLE JSON OBJECT representing the updated component.
- It MUST be valid JSON, no extra commentary.

ASSESSMENT / SYLLABUS TEXT:
\"\"\"{syllabus_text}\"\"\"


COMPONENT TO ENRICH:
{comp_json}
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You enrich assessment components using extra details from the syllabus. "
                        "You ALWAYS return ONLY valid JSON (one object)."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )

        raw = resp.choices[0].message.content.strip()

        try:
            updated = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                # If enrichment fails, fall back to original
                return component
            updated = json.loads(m.group(0))

        # Basic safety: keep invariant fields from the original
        for fixed_field in ["component_id", "name", "weight_percent", "applies_to"]:
            updated[fixed_field] = component[fixed_field]

        return updated

    except Exception as e:
        print(f"⚠️ Enrichment error for component '{component.get('name')}': {e}")
        return component


# ---------------------------------------------------------------------
# 4. LLM-based assessment extractor (2-pass: base + enrichment)
# ---------------------------------------------------------------------

def extract_assessment_components(text: str) -> List[Dict]:
    """
    Extract structured assessment components via LLM.

    Pass 1: extract components (names + weights + basic fields).
    Pass 2: for each component, enrich with additional details from the syllabus.
    """

    if not client:
        print("⚠️ No OpenAI API key — cannot extract assessments.")
        return []

    # Try regex section first
    section = extract_assessment_section(text)

    if section:
        print("✅ Found explicit assessment/test section via regex. Using that.\n")
    else:
        print("⚠️ No explicit assessment/test heading detected — using FULL syllabus text.\n")
        section = text  # fallback: let LLM find the grading info itself

    section = section[:12000]  # safety truncation

    prompt = f"""
You are analyzing a university course syllabus.

Your task: find and extract ALL assessment / grading components that contribute to
the final grade. This includes, for both ATTENDING and NON-ATTENDING students:

- exams
- quizzes / tests
- group projects
- simulations
- participation
- peer evaluation
- extra points or bonuses
- separate grading schemes for attending / non-attending

CRITICAL DETAIL REQUIREMENTS:
- If a component is later described in more detail (e.g. in a "Business simulations"
  paragraph), you MUST incorporate those details into:
  - "description"
  - "keywords"
  - "count" (number of deliverables)
- If a project is later given a case name (e.g. "Pacific Review – Disney/Pixar"),
  add that to "keywords" and mention it in "description".

OUTPUT RULES:
- Output ONLY a JSON ARRAY of components.
- NO explanations, no natural-language text outside JSON.

Each component must include:

- "component_id": slugified lowercase id
- "name": exact name from syllabus
- "type": one of
    "exam" | "quiz" | "project" | "simulation" | "case_work"
    | "participation" | "assignment" | "bonus" | "other"
- "weight_percent": number (no % sign)
- "count": number of deliverables or null
- "applies_to": "attending" | "non_attending" | "all"
- "description": 1–2 sentences
- "keywords": list
- "raw_text": short excerpt from syllabus

Be exhaustive. If something has a separate % weight, make a separate component.

TEXT:
\"\"\"{section}\"\"\""""

    try:
        # ------------------------
        # PASS 1: base extraction
        # ------------------------
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract structured assessment components from course syllabi. "
                        "You ALWAYS return ONLY valid JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )

        raw = resp.choices[0].message.content.strip()

        # Strict JSON extraction with fallback
        try:
            components = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\[.*\]", raw, re.DOTALL)
            if not m:
                print("⚠️ JSON parsing error in assessment extraction.")
                return []
            components = json.loads(m.group(0))

        ALLOWED_TYPES = {
            "exam",
            "quiz",
            "project",
            "simulation",
            "case_work",
            "participation",
            "assignment",
            "bonus",
            "other",
        }

        base_cleaned: List[Dict] = []
        for c in components:
            if not isinstance(c, dict):
                continue
            if "name" not in c or "weight_percent" not in c:
                continue

            # Defaults
            c.setdefault(
                "component_id",
                re.sub(r"[^a-z0-9]+", "_", c["name"].lower()).strip("_"),
            )
            c.setdefault("type", "other")
            c.setdefault("count", None)
            c.setdefault("applies_to", "all")
            c.setdefault("description", "")
            c.setdefault("keywords", [])
            c.setdefault("raw_text", "")

            # Normalize type
            t = str(c.get("type", "other")).lower().strip()
            if t not in ALLOWED_TYPES:
                # preserve some info as keyword if weird type label
                if "peer" in t:
                    c["keywords"] = list(set(c.get("keywords", []) + ["peer evaluation"]))
                c["type"] = "other"
            else:
                c["type"] = t

            # Convert weight to float
            try:
                c["weight_percent"] = float(c["weight_percent"])
            except Exception:
                continue

            base_cleaned.append(c)

        if not base_cleaned:
            return []

        # ------------------------
        # PASS 2: enrichment
        # ------------------------
        print(f"🔁 Enriching {len(base_cleaned)} components with detailed info...\n")

        enriched_components: List[Dict] = []
        for c in base_cleaned:
            enriched = enrich_component_with_details(c, section)
            # Make sure weight is still numeric
            try:
                enriched["weight_percent"] = float(enriched["weight_percent"])
            except Exception:
                enriched["weight_percent"] = c["weight_percent"]
            enriched_components.append(enriched)

        return enriched_components

    except Exception as e:
        print(f"❌ Error in assessment extraction: {e}")
        return []


# ---------------------------------------------------------------------
# 5. Main script execution
# ---------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 80)
    print("📄 ASSESSMENT / TEST PARSER")
    print("=" * 80)

    # choose the most recent uploaded PDF automatically
    uploads_dir = backend_dir / "uploads"
    pdf_files = sorted(uploads_dir.glob("*.pdf"), key=lambda x: x.stat().st_mtime, reverse=True)

    if not pdf_files:
        print("❌ No PDFs found in uploads/")
        sys.exit(1)

    file_path = pdf_files[0]
    print(f"📄 Using most recent PDF: {file_path.name}\n")

    # Parse PDF
    print("🔍 Step 1: Parsing file...")
    try:
        with open(file_path, "rb") as f:
            content = f.read()

        if file_path.suffix.lower() == ".pdf":
            text = parse_pdf(content)
        else:
            text = parse_text_document(content, file_path.suffix.lower())

        print(f"✅ Parsed {len(text)} characters.\n")

    except Exception as e:
        print(f"❌ Failed to parse file: {e}")
        sys.exit(1)

    # Extract components
    print("🔍 Step 2: Extracting assessment components...")
    components = extract_assessment_components(text)

    print("\n" + "=" * 80)
    print(f"📋 FOUND {len(components)} ASSESSMENT COMPONENTS")
    print("=" * 80 + "\n")

    for i, c in enumerate(components, 1):
        print(f"Component #{i}")
        print(f"  Name:          {c['name']}")
        print(f"  ID:            {c['component_id']}")
        print(f"  Weight:        {c['weight_percent']}%")
        print(f"  Type:          {c['type']}")
        print(f"  Applies to:    {c['applies_to']}")
        print(f"  Count:         {c['count']}")
        print(f"  Keywords:      {c['keywords']}")
        print(f"  Raw excerpt:   {c['raw_text'][:200]}...")
        print("")

    print("✅ Done.\n")
