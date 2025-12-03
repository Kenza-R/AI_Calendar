"""
CrewAI-based script to test deadline & class-session extraction from PDF files.

Pipeline:
  1) Parse syllabus PDF -> raw text
  2) Preprocess -> indexed lines + date candidates
  3) Agent 1 (Segmentation): build schedule_blocks + non_schedule_blocks
  4) Agent 2 (Extraction): for each schedule_block, extract tasks
  5) Deterministic flatten + inline DEADLINE: parsing
  6) Agent 3 (QA): global consistency check vs assessment components
"""

import sys
import os
from pathlib import Path
import json
import re
from typing import List, Dict, Optional

# --- Backend setup (same as your current script) ---
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from app.utils.pdf_parser import parse_pdf, parse_text_document
from app.config import settings

# Optional: your existing assessment parser
try:
    from app.utils.test_assessment_parser import extract_assessment_components
except ImportError:
    extract_assessment_components = None

# --- CrewAI imports ---
from crewai import Agent, Task, Crew

# ---------------------------------------------------------------------
# OpenAI / LLM setup for CrewAI
# ---------------------------------------------------------------------
api_key_valid = settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-")
if not api_key_valid:
    print("❌ OPENAI_API_KEY missing or invalid in settings.")
    sys.exit(1)

# Make sure CrewAI can see the key
os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
# Optional: choose model (CrewAI defaults to gpt-4o-mini if not set)
os.environ.setdefault("OPENAI_MODEL_NAME", "gpt-4o-mini")


# ---------------------------------------------------------------------
# Date regex + helpers (reused from your script)
# ---------------------------------------------------------------------
DATE_REGEX = re.compile(
    r"\b("
    r"(\d{1,2})[/.](\d{1,2})(?:[/.](\d{2,4}))?"  # numeric dd/mm(/yyyy)?
    r"|"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+\d{1,2}"  # short month
    r"|"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}"  # long month
    r")\b",
    re.IGNORECASE,
)


def is_valid_date_token(token: str) -> bool:
    token = token.strip()

    if "\n" in token:
        return False

    m_num = re.match(r"^(\d{1,2})[/.](\d{1,2})(?:[/.](\d{2,4}))?$", token)
    if m_num:
        # Reject simple "1/2", "2/2" style part numbers
        if re.match(r"^[1-9]/[1-9]$", token):
            return False
        day, month = int(m_num.group(1)), int(m_num.group(2))
        return 1 <= day <= 31 and 1 <= month <= 12

    if re.match(
        r"(?i)^(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}$",
        token,
    ):
        return True

    if re.match(
        r"(?i)^(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}$",
        token,
    ):
        return True

    return False


def build_indexed_lines(text: str) -> List[Dict]:
    """Split text into lines with indices for the segmentation agent."""
    lines = text.splitlines()
    return [{"index": i, "text": line} for i, line in enumerate(lines)]


def extract_date_candidates(indexed_lines: List[Dict]) -> List[Dict]:
    """Find all valid date tokens with their line index."""
    candidates: List[Dict] = []
    for line in indexed_lines:
        idx = line["index"]
        txt = line["text"]
        for m in DATE_REGEX.finditer(txt):
            token = m.group(0).strip()
            if is_valid_date_token(token):
                candidates.append(
                    {
                        "date_string": token,
                        "line_index": idx,
                        "raw_match": token,
                    }
                )
    return candidates


def extract_inline_deadlines_from_text(text: str) -> List[Dict]:
    """
    Look for explicit 'DEADLINE' mentions in the raw text and turn them
    into administrative hard_deadline items.
    """
    items: List[Dict] = []

    lowered = text.lower()
    idx = 0
    while True:
        pos = lowered.find("deadline", idx)
        if pos == -1:
            break

        tail = text[pos:]

        date_match = None
        for m in DATE_REGEX.finditer(tail):
            token = m.group(0).strip()
            if is_valid_date_token(token):
                date_match = m
                break

        if date_match is None:
            idx = pos + len("deadline")
            continue

        date_string = date_match.group(0).strip()
        first_line = tail.split("\n", 1)[0]

        if "DEADLINE:" in first_line:
            after = first_line.split("DEADLINE:", 1)[1].strip()
        elif "deadline:" in first_line:
            after = first_line.split("deadline:", 1)[1].strip()
        else:
            after = first_line[len("deadline") :].strip()

        description = " ".join(after.split())
        title = "Administrative deadline"
        if "attending" in first_line.lower() and "non-attending" in first_line.lower():
            title = "Confirm attending / non-attending status"

        items.append(
            {
                "kind": "hard_deadline",
                "date": date_string,
                "type": "administrative",
                "title": title,
                "description": description,
            }
        )

        idx = pos + len("deadline")

    return items


# ---------------------------------------------------------------------
# Flattening helper: convert Agent 2 outputs into canonical items list
# ---------------------------------------------------------------------
def flatten_extraction_results(block_results: List[List[Dict]]) -> List[Dict]:
    """
    block_results: list of per-block JSON arrays (each returned by extraction agent).
    Returns a flat list of items with:
      - kind: "class_session" | "hard_deadline"
      - date
      - type
      - title
      - description (optional)
      - readings (for class_session)
      - assessment_name (optional)
    """
    items: List[Dict] = []

    for per_block in block_results:
        if not per_block:
            continue

        for item in per_block:
            if not isinstance(item, dict):
                continue

            kind = item.get("kind")
            date_string = item.get("date_string")
            if not date_string or kind == "ignore":
                continue

            # --- Hard deadlines ---
            if kind == "hard_deadline":
                for t in item.get("hard_deadlines", []):
                    title = (t.get("title") or "").strip()
                    if not title:
                        continue
                    deadline_type = t.get("type", "assignment")
                    description = (t.get("description") or "").strip()

                    obj: Dict = {
                        "kind": "hard_deadline",
                        "date": date_string,
                        "type": deadline_type,
                        "title": title,
                    }
                    if description:
                        obj["description"] = description
                    assessment_name = t.get("assessment_name")
                    if assessment_name:
                        obj["assessment_name"] = assessment_name
                    items.append(obj)

            # --- Class sessions ---
            elif kind == "class_session":
                session_title = (item.get("session_title") or "").strip()
                if not session_title:
                    session_title = f"Class session on {date_string}"

                readings: List[Dict] = []

                # Preparatory readings
                for t in item.get("prep_tasks", []) or []:
                    r_title = (t.get("title") or "").strip()
                    if not r_title:
                        continue
                    readings.append(
                        {
                            "title": r_title,
                            "kind": "prep",
                            "reading_type": t.get("type", "reading_preparatory"),
                        }
                    )

                # Mandatory / optional readings
                for t in item.get("mandatory_tasks", []) or []:
                    r_title = (t.get("title") or "").strip()
                    if not r_title:
                        continue
                    readings.append(
                        {
                            "title": r_title,
                            "kind": "mandatory",
                            "reading_type": t.get("type", "reading_mandatory"),
                        }
                    )

                items.append(
                    {
                        "kind": "class_session",
                        "date": date_string,
                        "type": "class_session",
                        "title": session_title,
                        "readings": readings,
                    }
                )

    # De-duplicate by (date, type, title)
    unique_items: List[Dict] = []
    seen = set()
    for it in items:
        key = (it.get("date"), it.get("type"), it.get("title"))
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(it)

    return unique_items


# ---------------------------------------------------------------------
# CrewAI Agents
# ---------------------------------------------------------------------
segmentation_agent = Agent(
    llm="gpt-4o-mini",
    role="Syllabus Segmentation Agent",
    goal=(
        "Segment a messy, PDF-extracted syllabus into clean, date-based schedule blocks "
        "and non-schedule blocks that later agents can reliably interpret."
    ),
    backstory=(
        "You specialize in understanding complex, badly formatted university syllabi. "
        "PDF extraction often breaks tables, wraps lines strangely, and scatters schedule "
        "information across multiple lines. You reconstruct this into coherent blocks.\n\n"
        "You do NOT interpret the pedagogical meaning of the text and you do NOT extract "
        "assignments or deadlines. You focus on:\n"
        "- Identifying which lines belong to the course schedule (weeks, sessions, dates).\n"
        "- Grouping consecutive lines into schedule blocks where each block corresponds to "
        "a single primary date.\n"
        "- Separating other relevant text into non-schedule blocks (e.g., 'Assessment & Grading').\n\n"
        "You never invent dates; you rely on provided date candidates and explicit date strings "
        "in the text."
    ),
    allow_delegation=False,
    verbose=True,
)

extraction_agent = Agent(
    llm="gpt-4o-mini",
    role="Syllabus Task Extraction Agent",
    goal=(
        "Interpret each date-based schedule block from the syllabus and extract structured "
        "class sessions, readings, and hard deadlines, using only dates and information "
        "explicitly present in the text."
    ),
    backstory=(
        "You are an expert at reading university syllabi and turning unstructured schedule "
        "entries into structured tasks.\n\n"
        "You receive one schedule block at a time, already segmented by the Segmentation Agent. "
        "Each block contains a primary date string and all the raw text around that date "
        "(week labels, topics, readings, notes, etc.), plus a list of graded assessment components.\n\n"
        "You identify class sessions, preparatory readings, mandatory/optional readings, and hard "
        "deadlines (due dates for assignments, exams, quizzes, projects). You link hard deadlines "
        "back to known graded components when possible.\n\n"
        "You never invent dates and never hallucinate tasks not justified by the text."
    ),
    allow_delegation=False,
    verbose=True,
)

qa_agent = Agent(
    llm="gpt-4o-mini",
    role="Syllabus QA & Consistency Agent",
    goal=(
        "Globally audit the extracted syllabus items and grading components to ensure that "
        "all graded components have corresponding deadlines, detect inconsistencies or "
        "duplicates, and produce a clear QA report plus a validated list of items."
    ),
    backstory=(
        "You act as a rigorous auditor for the syllabus extraction pipeline. Previous agents "
        "have segmented the document and extracted class sessions and deadlines. You now look "
        "at the entire picture to check for completeness and consistency.\n\n"
        "You verify coverage of graded components, detect missing deadlines, conflicting dates, "
        "unmatched deadlines, and any grading mismatches. You are conservative and do not invent "
        "new assessments or dates."
    ),
    allow_delegation=False,
    verbose=True,
)

workload_estimation_agent = Agent(
    llm="gpt-4o-mini",
    role="Academic Workload Estimation Agent",
    goal=(
        "Analyze each deadline, assignment, reading, and task to estimate the time required "
        "for completion, providing realistic workload estimates in hours to help students "
        "plan their schedules effectively."
    ),
    backstory=(
        "You are an experienced academic advisor who understands student workloads across "
        "different types of assignments and tasks. You have deep knowledge of how long typical "
        "academic activities take:\n\n"
        "- Reading assignments (pages per hour, comprehension levels)\n"
        "- Written assignments (research papers, essays, reports by length and complexity)\n"
        "- Exams and quizzes (study time based on material coverage)\n"
        "- Projects (scope, research, implementation, writing)\n"
        "- Presentations (preparation, practice, slides)\n"
        "- Problem sets and homework\n"
        "- Class preparation and participation\n\n"
        "You consider factors like:\n"
        "- Assignment type and deliverable format\n"
        "- Complexity and depth required\n"
        "- Research or reading involved\n"
        "- Typical student capabilities\n"
        "- Industry-standard time estimates for academic work\n\n"
        "You provide conservative, realistic estimates that help students avoid underestimating "
        "their workload. You express estimates in hours and can break down complex tasks into "
        "sub-components when helpful."
    ),
    allow_delegation=False,
    verbose=True,
)

# ---------------------------------------------------------------------
# CrewAI Tasks
# ---------------------------------------------------------------------
segmentation_task = Task(
    description=(
        "You are the Segmentation / Structuring Agent for a university syllabus.\n\n"
        "INPUTS YOU RECEIVE:\n"
        "- Full syllabus text with line indices: {indexed_lines}\n"
        "- A list of date candidates extracted via regex, each with a line index: {date_candidates}\n"
        "- Optionally, rough section hints (e.g. where the 'Course Schedule' or 'Grading' "
        "sections start and end): {sections_hint}\n\n"
        "YOUR GOAL:\n"
        "1. Identify all parts of the syllabus that describe the course schedule, class meetings, "
        "and date-based events (e.g., tables, 'Week 1', 'Session 2', 'Detailed Schedule').\n"
        "2. Group consecutive lines into coherent schedule blocks, where each block corresponds to "
        "a single primary date_string.\n"
        "3. For each schedule block:\n"
        "   - Include all lines that clearly belong to that date's session (week label, date, topic, readings, notes).\n"
        "   - Ignore purely decorative headers/footers and column labels like 'Day / Instructor / Topic'.\n"
        "4. Also group non-schedule content that might be relevant later (e.g., 'Assessment & Grading', "
        "'Exams', 'Policies') into non_schedule_blocks.\n"
        "5. Do NOT interpret the meaning of the content or extract deadlines/readings; your job is only "
        "to segment and group text into blocks.\n"
        "6. Do NOT invent dates. Only use date strings that appear in {date_candidates} or in the text.\n\n"
        "OUTPUT FORMAT:\n"
        "Return a single JSON object with:\n"
        "{\n"
        "  \"schedule_blocks\": [\n"
        "    {\n"
        "      \"date_string\": \"<canonical date string>\",\n"
        "      \"line_indices\": [list of ints],\n"
        "      \"raw_block\": \"concatenated raw text for this block\"\n"
        "    },\n"
        "    ...\n"
        "  ],\n"
        "  \"non_schedule_blocks\": [\n"
        "    {\n"
        "      \"title\": \"short label, e.g. 'Assessment & Grading' or 'Unknown section'\",\n"
        "      \"line_indices\": [list of ints],\n"
        "      \"raw_block\": \"concatenated raw text\"\n"
        "    },\n"
        "    ...\n"
        "  ]\n"
        "}\n"
    ),
    expected_output=(
        "A single JSON object with the keys 'schedule_blocks' and 'non_schedule_blocks', "
        "as described in the instructions."
    ),
    agent=segmentation_agent,
)

extraction_task = Task(
    description=(
        "You are the Schedule Interpretation / Task Extraction Agent.\n\n"
        "INPUTS YOU RECEIVE:\n"
        "- One schedule block object from the segmentation step: {schedule_block}\n"
        "- A list of graded assessment components extracted from the syllabus: {assessment_components}\n\n"
        "YOUR GOAL FOR THIS SINGLE BLOCK:\n"
        "1. Read the raw_block and identify:\n"
        "   - Class session information (topic, title, week label, etc.).\n"
        "   - Preparatory readings or 'read before class' items.\n"
        "   - Mandatory or optional readings explicitly identified as readings.\n"
        "   - Hard deadlines: anything clearly due, to be submitted, exam dates, quizzes, tests, projects, etc.\n"
        "2. Use ONLY date strings that appear explicitly in this block. Do NOT invent new dates.\n"
        "3. If the block mentions a graded assessment component (by name or close variant), link it "
        "via 'assessment_name' in the corresponding hard_deadline.\n\n"
        "OUTPUT FORMAT:\n"
        "Return a JSON ARRAY. Each element has:\n"
        "{\n"
        "  \"kind\": \"class_session\" | \"hard_deadline\" | \"ignore\",\n"
        "  \"date_string\": \"<one of the allowed date strings>\",\n"
        "  \"session_title\": \"optional, for class_session\",\n"
        "  \"prep_tasks\": [ {\"title\": \"...\", \"type\": \"reading_preparatory\" | \"reading_optional\" | \"reading_mandatory\"} ],\n"
        "  \"mandatory_tasks\": [ {\"title\": \"...\", \"type\": \"reading_mandatory\" | \"reading_optional\"} ],\n"
        "  \"hard_deadlines\": [\n"
        "    {\n"
        "      \"title\": \"...\",\n"
        "      \"type\": \"assignment\" | \"exam\" | \"project\" | \"assessment\" | \"administrative\",\n"
        "      \"description\": \"short description (max 120 chars)\",\n"
        "      \"assessment_name\": \"optional, name from assessment_components if matched\"\n"
        "    }\n"
        "  ]\n"
        "}\n"
    ),
    expected_output=(
        "A valid JSON array of objects, each describing either a 'class_session' or 'hard_deadline' "
        "for this block."
    ),
    agent=extraction_agent,
)

qa_task = Task(
    description=(
        "You are the Global QA & Consistency Agent for a syllabus extraction pipeline.\n\n"
        "INPUTS YOU RECEIVE:\n"
        "- A flat list of all extracted items (class sessions + deadlines): {merged_tasks}\n"
        "- The list of graded assessment components extracted from the syllabus: {assessment_components}\n"
        "- Optionally, a preliminary mapping between components and tasks: {preliminary_mapping}\n"
        "- Raw text of non-schedule sections (e.g., 'Assessment & Grading'): {non_schedule_text}\n\n"
        "YOUR GOAL:\n"
        "1. Check coverage: For each assessment component, is there at least one corresponding 'hard_deadline'?\n"
        "2. Identify missing assessments: components that appear in grading but have no dated hard_deadline.\n"
        "3. Detect duplicates or conflicts: the same exam/assignment with multiple dates, etc.\n"
        "4. Identify unmatched deadlines: hard_deadlines that do not clearly map to any graded component.\n"
        "5. Perform global sanity checks (e.g., a 40% Final Exam that never appears in the schedule).\n"
        "6. Optionally adjust obvious misclassifications (e.g., 'Final Exam' marked as 'assignment' instead of 'exam'), "
        "but do NOT invent new assessments or dates.\n\n"
        "OUTPUT FORMAT:\n"
        "Return a single JSON object:\n"
        "{\n"
        "  \"validated_items\": [ /* final list of items, possibly slightly corrected */ ],\n"
        "  \"missing_assessments\": [ {\"component_name\": \"...\", \"reason\": \"...\"} ],\n"
        "  \"unmatched_deadlines\": [ {\"title\": \"...\", \"date\": \"...\", \"reason\": \"...\"} ],\n"
        "  \"inconsistencies\": [ {\"type\": \"duplicate_deadline\" | \"conflicting_type\" | \"grading_mismatch\" | \"other\", \"details\": \"...\"} ],\n"
        "  \"other_anomalies\": [ {\"type\": \"...\", \"details\": \"...\"} ],\n"
        "  \"summary\": \"Short natural language summary of QA findings.\"\n"
        "}\n"
    ),
    expected_output=(
        "A single JSON object with 'validated_items', 'missing_assessments', "
        "'unmatched_deadlines', 'inconsistencies', 'other_anomalies', and 'summary'."
    ),
    agent=qa_agent,
)

workload_estimation_task = Task(
    description=(
        "You are the Academic Workload Estimation Agent.\n\n"
        "INPUTS YOU RECEIVE:\n"
        "- A list of validated items from the syllabus: {validated_items}\n"
        "- Assessment components with their types and weights: {assessment_components}\n"
        "- Full syllabus text for additional context: {full_text}\n\n"
        "YOUR GOAL:\n"
        "For each item (deadline, reading, assignment, exam, project, etc.), estimate the realistic "
        "time a student would need to complete it successfully.\n\n"
        "ESTIMATION GUIDELINES:\n"
        "- **Readings**: Consider pages/chapters mentioned. Typical academic reading: 15-25 pages/hour "
        "for moderate difficulty, 10-15 pages/hour for dense material. Add time for note-taking.\n"
        "- **Essays/Papers**: 2-4 hours per page for research + writing + revision. 3-4 page paper = 8-15 hours.\n"
        "- **Exams**: Study time = 2-4 hours per hour of exam, depending on coverage and difficulty. "
        "Midterms typically 6-12 hours study, finals 15-25 hours.\n"
        "- **Projects**: Small projects 10-20 hours, major projects 30-60+ hours including research, "
        "implementation, writing, and presentation prep.\n"
        "- **Presentations**: 1-2 hours per minute of presentation (research + slides + practice).\n"
        "- **Problem Sets**: 3-8 hours depending on complexity and number of problems.\n"
        "- **Class Preparation**: 1-2 hours per class session for readings and prep.\n"
        "- **Reflection/Journal**: 1-3 hours depending on depth required.\n\n"
        "Consider factors like:\n"
        "- Weight/importance (higher weight = more thorough preparation needed)\n"
        "- Complexity indicators in the description\n"
        "- Whether it requires research, analysis, or creative work\n"
        "- Whether it's group work (adjust accordingly)\n"
        "- Any specified length or scope requirements\n\n"
        "OUTPUT FORMAT:\n"
        "Return a JSON array with all items including workload estimates:\n"
        "[\n"
        "  {\n"
        "    \"date\": \"Oct 22\",\n"
        "    \"type\": \"assignment\",\n"
        "    \"title\": \"Research Paper\",\n"
        "    \"description\": \"...\",\n"
        "    \"estimated_hours\": 15,\n"
        "    \"workload_breakdown\": \"Research (5h) + Writing (7h) + Revision (3h)\",\n"
        "    \"confidence\": \"high\" | \"medium\" | \"low\",\n"
        "    \"notes\": \"Additional context or assumptions for the estimate\",\n"
        "    ... /* all other original fields */\n"
        "  },\n"
        "  ...\n"
        "]\n\n"
        "Be realistic and slightly conservative. Students should be able to complete the work in the "
        "estimated time without rushing."
    ),
    expected_output=(
        "A JSON array of all items with added workload estimation fields: 'estimated_hours', "
        "'workload_breakdown', 'confidence', and 'notes'."
    ),
    agent=workload_estimation_agent,
)


# ---------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------
def main():
    print("=" * 80)
    print("📅 DEADLINE EXTRACTION TEST (CrewAI, 4-Agent Pipeline with Workload Estimation)")
    print("=" * 80)
    print()

    # ----- 1) File selection -----
    if len(sys.argv) < 2:
        uploads_dir = backend_dir / "uploads"
        if uploads_dir.exists():
            pdf_files = sorted(
                uploads_dir.glob("*.pdf"),
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            )
            if pdf_files:
                file_path = pdf_files[0]
                print(f"📄 Using most recent PDF: {file_path.name}\n")
            else:
                print("❌ No PDF files found in uploads folder")
                print("Usage: python test_deadline_extraction_crewai.py <path_to_pdf>")
                sys.exit(1)
        else:
            print("❌ Uploads folder not found")
            print("Usage: python test_deadline_extraction_crewai.py <path_to_pdf>")
            sys.exit(1)
    else:
        file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)

    # ----- 2) Parse PDF/text -----
    print("🔍 Step 1: Parsing file...")
    try:
        with open(file_path, "rb") as f:
            content = f.read()

        if file_path.suffix.lower() == ".pdf":
            text = parse_pdf(content)
        else:
            text = parse_text_document(content, file_path.suffix.lower())

        print(f"✅ Parsed {len(text)} characters\n")
    except Exception as e:
        print(f"❌ Error parsing file: {e}")
        sys.exit(1)

    # ----- 3) Extract assessment components (optional) -----
    print("🤖 Step 2a: Extracting assessment components...")
    assessment_components = []
    if extract_assessment_components is not None:
        try:
            assessment_components = extract_assessment_components(text) or []
            if assessment_components:
                print(f"   Found {len(assessment_components)} graded components:")
                for comp in assessment_components:
                    print(
                        f"      - {comp.get('name', 'Unnamed')} "
                        f"({comp.get('weight_percent', 0)}%)"
                    )
            else:
                print("   No graded components found.")
            print()
        except Exception as e:
            print(f"   ⚠️ Could not extract assessments: {e}")
            print("   Continuing without assessment context...\n")
            assessment_components = []
    else:
        print("   (No assessment parser available, skipping)\n")

    # ----- 4) Preprocess for Agent 1 -----
    indexed_lines = build_indexed_lines(text)
    date_candidates = extract_date_candidates(indexed_lines)
    sections_hint = []  # you can add heuristics later

    # For the agent, we send stringified forms
    seg_inputs = {
        "indexed_lines": json.dumps(indexed_lines, indent=2),
        "date_candidates": json.dumps(date_candidates, indent=2),
        "sections_hint": json.dumps(sections_hint, indent=2),
    }

    print("🤖 Step 2b: Segmenting syllabus into schedule and non-schedule blocks (Agent 1)...")
    seg_crew = Crew(
        agents=[segmentation_agent],
        tasks=[segmentation_task],
        verbose=True,
        memory=False,
    )
    seg_result_raw = seg_crew.kickoff(inputs=seg_inputs)

    # Handle CrewOutput object (new CrewAI version returns object instead of string)
    if hasattr(seg_result_raw, 'raw'):
        seg_result_str = seg_result_raw.raw
    elif hasattr(seg_result_raw, 'json'):
        seg_result_str = seg_result_raw.json
    else:
        seg_result_str = str(seg_result_raw)

    try:
        seg_data = json.loads(seg_result_str.strip())
    except Exception:
        # Try to extract JSON if wrapped in text
        m = re.search(r"\{.*\}", seg_result_str, re.DOTALL)
        if not m:
            print("❌ Could not parse segmentation output as JSON.")
            print(seg_result_str)
            sys.exit(1)
        seg_data = json.loads(m.group(0))

    schedule_blocks = seg_data.get("schedule_blocks", []) or []
    non_schedule_blocks = seg_data.get("non_schedule_blocks", []) or []
    print(f"   ➜ Found {len(schedule_blocks)} schedule blocks")
    print(f"   ➜ Found {len(non_schedule_blocks)} non-schedule blocks\n")

    if not schedule_blocks:
        print("⚠️ No schedule blocks found. Exiting.")
        sys.exit(0)

    # ----- 5) Agent 2 for each schedule block -----
    print("🤖 Step 3: Extracting tasks from each schedule block (Agent 2)...")

    extraction_crew = Crew(
        agents=[extraction_agent],
        tasks=[extraction_task],
        verbose=True,
        memory=False,
    )

    extraction_inputs = []
    for block in schedule_blocks:
        extraction_inputs.append(
            {
                "schedule_block": json.dumps(block, indent=2),
                "assessment_components": json.dumps(assessment_components, indent=2),
            }
        )

    # kickoff_for_each will run the crew once per element in extraction_inputs
    extraction_results_raw = extraction_crew.kickoff_for_each(inputs=extraction_inputs)

    # Parse each result (JSON array) into Python objects
    per_block_items: List[List[Dict]] = []
    for idx, res in enumerate(extraction_results_raw):
        if not res:
            per_block_items.append([])
            continue
        
        # Handle CrewOutput object
        if hasattr(res, 'raw'):
            res_str = res.raw
        elif hasattr(res, 'json'):
            res_str = res.json
        else:
            res_str = str(res)
        
        try:
            arr = json.loads(res_str.strip())
        except Exception:
            m = re.search(r"\[.*\]", res_str, re.DOTALL)
            if not m:
                print(f"⚠️ Could not parse extraction output for block #{idx+1}, skipping.")
                per_block_items.append([])
                continue
            arr = json.loads(m.group(0))
        if not isinstance(arr, list):
            arr = [arr]
        per_block_items.append(arr)

    # ----- 6) Flatten + inline DEADLINE parsing -----
    print("🤖 Step 4: Flattening Agent 2 outputs + inline 'DEADLINE:' parsing...")
    merged_items = flatten_extraction_results(per_block_items)

    inline_admin = extract_inline_deadlines_from_text(text)
    merged_items.extend(inline_admin)

    # Final de-dup
    final_items: List[Dict] = []
    seen = set()
    for it in merged_items:
        key = (it.get("date"), it.get("type"), it.get("title"))
        if key in seen:
            continue
        seen.add(key)
        final_items.append(it)

    print(f"   ➜ After flattening and inline parsing: {len(final_items)} items\n")

    if not final_items:
        print("⚠️ No items found after extraction.")
        sys.exit(0)

    # ----- 7) Agent 3: QA & Consistency -----
    print("🤖 Step 5: Running global QA & consistency checks (Agent 3)...")

    non_schedule_text = "\n\n".join(
        block.get("raw_block", "") for block in non_schedule_blocks
    )
    preliminary_mapping = {}  # you can add deterministic mapping later

    qa_inputs = {
        "merged_tasks": json.dumps(final_items, indent=2),
        "assessment_components": json.dumps(assessment_components, indent=2),
        "preliminary_mapping": json.dumps(preliminary_mapping, indent=2),
        "non_schedule_text": non_schedule_text,
    }

    qa_crew = Crew(
        agents=[qa_agent],
        tasks=[qa_task],
        verbose=True,
        memory=False,
    )
    qa_result_raw = qa_crew.kickoff(inputs=qa_inputs)

    # Handle CrewOutput object
    if hasattr(qa_result_raw, 'raw'):
        qa_result_str = qa_result_raw.raw
    elif hasattr(qa_result_raw, 'json'):
        qa_result_str = qa_result_raw.json
    else:
        qa_result_str = str(qa_result_raw)

    try:
        qa_data = json.loads(qa_result_str.strip())
    except Exception:
        m = re.search(r"\{.*\}", qa_result_str, re.DOTALL)
        if not m:
            print("⚠️ Could not parse QA output as JSON. Using pre-QA items only.")
            qa_data = {"validated_items": final_items}
        else:
            qa_data = json.loads(m.group(0))

    validated_items = qa_data.get("validated_items") or final_items

    # ----- 8) Workload estimation (Agent 4) -----
    print("🤖 Step 6: Estimating workload for all tasks (Agent 4)...")
    workload_inputs = {
        "validated_items": json.dumps(validated_items, indent=2),
        "assessment_components": json.dumps(assessment_components, indent=2),
        "full_text": text[:5000],  # First 5000 chars for context
    }

    workload_crew = Crew(
        agents=[workload_estimation_agent],
        tasks=[workload_estimation_task],
        verbose=True,
        memory=False,
    )
    workload_result_raw = workload_crew.kickoff(inputs=workload_inputs)

    # Handle CrewOutput object
    if hasattr(workload_result_raw, 'raw'):
        workload_result_str = workload_result_raw.raw
    elif hasattr(workload_result_raw, 'json'):
        workload_result_str = workload_result_raw.json
    else:
        workload_result_str = str(workload_result_raw)

    try:
        items_with_workload = json.loads(workload_result_str.strip())
    except Exception:
        m = re.search(r"\[.*\]", workload_result_str, re.DOTALL)
        if not m:
            print("⚠️ Could not parse workload output as JSON. Using validated items without workload.")
            items_with_workload = validated_items
        else:
            items_with_workload = json.loads(m.group(0))

    if not isinstance(items_with_workload, list):
        print("⚠️ Workload output was not a list. Using validated items without workload.")
        items_with_workload = validated_items

    print(f"✅ Added workload estimates to {len(items_with_workload)} items\n")

    # ----- 9) Print summary & details -----
    print("=" * 80)
    print(f"📋 FINAL RESULTS: {len(items_with_workload)} ITEMS WITH WORKLOAD ESTIMATES")
    print("=" * 80)
    print()

    for i, item in enumerate(items_with_workload, 1):
        print(f"Item #{i}:")
        print(f"  📅 Date:        {item.get('date', 'N/A')}")
        print(f"  🏷️  Type:        {item.get('type', 'N/A')}")
        print(f"  📌 Title:       {item.get('title', 'N/A')}")
        desc = item.get("description")
        if desc:
            print(f"  📝 Description: {desc}")
        if "assessment_name" in item:
            print(f"  🎯 Assessment:  {item['assessment_name']}")
        
        # Display workload estimate
        if "estimated_hours" in item:
            hours = item.get("estimated_hours")
            confidence = item.get("confidence", "N/A")
            print(f"  ⏱️  Estimated Time: {hours} hours (confidence: {confidence})")
            if "workload_breakdown" in item:
                print(f"      Breakdown: {item['workload_breakdown']}")
            if "notes" in item and item["notes"]:
                print(f"      Notes: {item['notes']}")
        
        if item.get("type") == "class_session":
            readings = item.get("readings") or []
            if readings:
                print("  📚 Readings:")
                for r in readings:
                    r_title = r.get("title", "Untitled reading")
                    r_type = r.get("reading_type", "reading")
                    print(f"    - {r_title} ({r_type})")
        print()

    print("=" * 80)
    print("🧪 QA SUMMARY")
    print("=" * 80)
    summary = qa_data.get("summary")
    if summary:
        print(summary)
    else:
        print("(No QA summary available.)")
    print()

    if qa_data.get("missing_assessments"):
        print("⚠️ Missing assessments:")
        for m_item in qa_data["missing_assessments"]:
            print(f"  - {m_item.get('component_name')}: {m_item.get('reason')}")
        print()

    if qa_data.get("unmatched_deadlines"):
        print("⚠️ Unmatched deadlines:")
        for u in qa_data["unmatched_deadlines"]:
            print(
                f"  - {u.get('title')} on {u.get('date')}: {u.get('reason', 'no reason given')}"
            )
        print()

    if qa_data.get("inconsistencies"):
        print("⚠️ Inconsistencies:")
        for inc in qa_data["inconsistencies"]:
            print(f"  - [{inc.get('type')}] {inc.get('details')}")
        print()

    # ----- 10) Optional: save JSON -----
    save_option = input("💾 Save final items with workload estimates to JSON file? (y/n): ").lower().strip()
    if save_option == "y":
        output_dir = backend_dir / "uploads"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{file_path.stem}_tasks_with_workload.json"
        with open(output_file, "w") as f:
            json.dump(
                {
                    "items_with_workload": items_with_workload,
                    "qa_report": qa_data,
                    "total_estimated_hours": sum(
                        item.get("estimated_hours", 0) for item in items_with_workload
                    ),
                },
                f,
                indent=2,
            )
        print(f"✅ Saved to: {output_file}")


if __name__ == "__main__":
    main()
