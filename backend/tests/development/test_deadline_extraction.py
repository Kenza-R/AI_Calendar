"""
Standalone script to test deadline & class-session extraction from PDF files
Uses a snippet-based approach for reliability across different syllabi.
"""
import sys
import os
from pathlib import Path
import json
import re
from typing import List, Dict, Optional

# Add backend directory to path for imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Change to backend directory for .env loading
os.chdir(backend_dir)

from app.utils.pdf_parser import parse_pdf, parse_text_document
from app.config import settings
from openai import OpenAI

# Initialize OpenAI client
api_key_valid = settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-")
client = OpenAI(api_key=settings.OPENAI_API_KEY) if api_key_valid else None

# --- Trigger lists for post-filtering ---
HARD_DEADLINE_TRIGGERS = [
    "due",
    "submit",
    "submission",
    "hand in",
    "exam",
    "test",
    "assessment",
    "quiz",
    "final",
    "midterm",
    "paper",
    "project",
    "assignment",
    "deadline",
]

READING_TRIGGERS = [
    "read ",
    "reading",
    "readings",
    "chapter",
    "chap.",
    "pp.",
    "required reading",
    "recommended reading",
    "read before class",
    "preparatory",
    "mandatory",
]

# Date regex:
#  - numeric: 6/9, 06/09, 6.9.22, 13/10/2023   (NO hyphen to avoid '1-5' chapter junk)
#  - text:    Sept 11, Sep 11, September 11
DATE_REGEX = re.compile(
    r"\b("
    r"(\d{1,2})[/.](\d{1,2})(?:[/.](\d{2,4}))?"  # numeric dd/mm(/yyyy)?
    r"|"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+\d{1,2}"  # short month names + day
    r"|"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}"  # long names + day
    r")\b",
    re.IGNORECASE,
)


def get_date_snippets(text: str, before: int = 1, after: int = 3) -> List[str]:
    """
    Extract coarse snippets of text around lines that contain at least one date.
    Each snippet usually contains one or more dates plus local context.
    """
    lines = text.splitlines()
    snippets: List[str] = []
    seen_lines = set()

    for i, line in enumerate(lines):
        if DATE_REGEX.search(line) and i not in seen_lines:
            start = max(0, i - before)
            end = min(len(lines), i + 1 + after)
            snippet = "\n".join(lines[start:end]).strip()
            if snippet:
                snippets.append(snippet)
                # Mark these lines as seen to avoid duplicates
                for j in range(start, end):
                    seen_lines.add(j)

    return snippets


def is_valid_date_token(token: str) -> bool:
    """
    Decide if a raw DATE_REGEX match is a 'real' date token we care about.
    Used both for extraction and for smart splitting.
    """
    token = token.strip()

    # Skip ugly cross-line stuff like "February \n\n22"
    if "\n" in token:
        return False

    # Numeric formats: dd/mm(/yyyy) or dd.mm(/yyyy)
    m_num = re.match(r"^(\d{1,2})[/.](\d{1,2})(?:[/.](\d{2,4}))?$", token)
    if m_num:
        # Reject things like "1/2", "2/2" etc. (almost always part/section numbers)
        if re.match(r"^[1-9]/[1-9]$", token):
            return False

        day, month = int(m_num.group(1)), int(m_num.group(2))
        return 1 <= day <= 31 and 1 <= month <= 12

    # Short month names: "Sept 11"
    if re.match(
        r"(?i)^(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}$",
        token,
    ):
        return True

    # Long month names: "September 11"
    if re.match(
        r"(?i)^(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}$",
        token,
    ):
        return True

    return False


def split_snippet_by_valid_dates(snippet: str) -> List[str]:
    """
    Within a large snippet containing many dates (like a detailed schedule grid),
    split it into smaller chunks, each starting at one valid date token and ending
    before the next valid date token.
    """
    valid_matches: List[re.Match] = []
    for m in DATE_REGEX.finditer(snippet):
        token = m.group(0).strip()
        if is_valid_date_token(token):
            valid_matches.append(m)

    if not valid_matches:
        return [snippet]

    chunks: List[str] = []
    for i, m in enumerate(valid_matches):
        start = m.start()
        end = valid_matches[i + 1].start() if i + 1 < len(valid_matches) else len(snippet)
        chunk = snippet[start:end].strip()
        if chunk:
            chunks.append(chunk)

    return chunks


def extract_date_strings(snippet: str) -> List[str]:
    """
    Extract valid date-like strings (day + month) from a snippet
    and ignore things like academic years or chapter ranges.
    """
    matches = DATE_REGEX.findall(snippet)
    date_strings: List[str] = []

    for match in matches:
        full_match = match[0].strip()
        if is_valid_date_token(full_match):
            date_strings.append(full_match)

    # Deduplicate
    return list(set(date_strings))


def analyze_snippet(
    snippet: str,
    assessment_context: Optional[str] = None,
) -> Optional[List[Dict]]:
    """
    Call the LLM on a snippet (may contain multiple dates + context)
    and get an array of date-level items.

    If assessment_context is provided, the LLM will be aware of graded
    components and can properly classify them as hard deadlines rather
    than preparatory reading.
    """
    if not client:
        return None

    date_strings = extract_date_strings(snippet)
    if not date_strings:
        return None

    unique_dates = sorted(set(date_strings))
    date_hint = ", ".join(unique_dates)

    # Add assessment context if provided
    assessment_info = ""
    if assessment_context:
        assessment_info = f"""

GRADED ASSESSMENT COMPONENTS:
The following are graded assignments/exams from the TESTS / grading section:
{assessment_context}

If the snippet mentions any of these graded components, classify them as
'hard_deadline' with type 'assignment', 'exam', 'project' or 'assessment' as appropriate,
NOT as preparatory reading.
"""

    prompt = f"""
You are processing a short excerpt from a university syllabus. The text is
shown below. It contains one or more explicit date strings.

Your job is to identify ONLY the concrete student tasks/deadlines in this snippet,
GROUPED BY DATE STRING.

The allowed date strings for this snippet are:
{date_hint}{assessment_info}

### IMPORTANT RULES

1. What counts as a HARD DEADLINE
   - Only create "hard_deadline" items if the text near that date contains
     verbs such as: "due", "submit", "submission", "hand in", "exam",
     "test", "assessment", "quiz", "final", "midterm", "paper", "project",
     "assignment", "deadline".
   - If the date is only used for a class meeting, a review session, or
     "Course and Grading Structure" WITHOUT any of those verbs, do NOT
     invent a deadline. Either treat it as "class_session" or "ignore".
   - If there are MULTIPLE assignments/assessments/projects mentioned for
     the same date, create a separate hard_deadline entry for EACH distinct
     deliverable (e.g., “Second Research Project Review (Final)” and
     “Third Research Project: Interim Report” should be two items).

2. What counts as READING TASKS
   - Only create reading tasks for items under headings like:
     "Readings", "Readings for Discussion", "Read before class",
     "Required Reading", "Recommended Reading", "Preparatory", "Mandatory".
   - Also include recommended readings explicitly marked as such (e.g.,
     "not required but recommended") and you may label them with type
     "reading_optional".
   - Do NOT create reading tasks from bullets under "Topics", "Timing",
     or other lecture content sections unless the text explicitly says
     "Read", "Reading", "Chapter", "Ch.", "Chap." or clearly names a
     book/article or chapter/section.

3. In-Class Assessments
   - If the snippet mentions "In-Class Assessment" or "in-class skills
     assessment", you MUST create at least one graded "hard_deadline"
     of type "assessment" on that date for each such occurrence,
     even if you also represent the session as "class_session".
     For example, title could be:
       "In-Class Assessment: Valuation of Property Types (1)".

4. Avoid generic umbrella deadlines
   - Do NOT create vague tasks like "Submit primary research assignments"
     unless the snippet explicitly says that ALL of them are due on that
     exact date. Prefer the specific names used by the syllabus
     ("Special Assignment #1", "First Research Project", etc.).

5. Multi-date phrases
   - When a sentence mentions multiple dates (e.g., a class on one date
     and something "due" on a different date), assign the deadline to the
     date that appears in the same "due/submit" phrase (e.g., "due Oct. 3"
     must be assigned to "Oct. 3", NOT to the earlier class date).

6. Do NOT hallucinate
   - Use ONLY the date strings above; do not invent new dates.
   - Do not create tasks that cannot be clearly justified from the text.

### OUTPUT FORMAT

Return a JSON ARRAY. Each element corresponds to ONE date string and has:

{{
  "kind": "class_session" | "hard_deadline" | "ignore",
  "date_string": "<one of: {date_hint}>",
  "session_title": "optional, for class_session",

  "prep_tasks": [
    {{"title": "...", "type": "reading_preparatory" | "reading_optional" | "reading_mandatory"}}
  ],

  "mandatory_tasks": [
    {{"title": "...", "type": "reading_mandatory" | "reading_optional"}}
  ],

  "hard_deadlines": [
    {{
      "title": "...",
      "type": "assignment" | "exam" | "project" | "assessment" | "administrative",
      "description": "max 120 chars",
      "assessment_name": "optional, exact name from the graded components list if this matches one"
    }}
  ]
}}

If nothing useful for a given date, you may omit that date entirely or set
"kind": "ignore" and empty lists.

Syllabus snippet:
\"\"\"{snippet}\"\"\""""

    try:
        response = client.chat.completions.create(
            # Use a stronger model for extraction reliability
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You strictly extract structured tasks from syllabus snippets "
                        "without hallucinating new dates. Always return a JSON array."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )

        raw = response.choices[0].message.content.strip()

        try:
            arr = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\[.*\]", raw, re.DOTALL)
            if not m:
                return None
            arr = json.loads(m.group(0))

        if not isinstance(arr, list):
            arr = [arr]

        return arr

    except Exception as e:
        print(f"⚠️  Error analyzing snippet: {e}")
        return None


def extract_inline_deadlines_from_text(text: str) -> List[Dict]:
    """
    Look for explicit 'DEADLINE' mentions in the raw text and turn them
    into administrative hard_deadline items. Example patterns:

      DEADLINE: Sunday, Sept 11, 2022 please send an email ...
    """
    items: List[Dict] = []

    lowered = text.lower()
    idx = 0
    while True:
        pos = lowered.find("deadline", idx)
        if pos == -1:
            break

        tail = text[pos:]

        # Try to find the first valid date token AFTER the word "deadline"
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

        # Take only the first line after 'deadline' for description
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


def extract_all_tasks_from_syllabus(
    text: str,
    show_snippets: bool = False,
    assessment_components: Optional[List[Dict]] = None,
) -> List[Dict]:
    """Main pipeline: extract snippets, analyze each, flatten into items.

    Items can be:
      - hard deadlines (assignments, exams, projects, assessments, admin)
      - class_sessions (one per class date, with readings bundled)
    """

    # 1. Extract coarse big snippets that contain dates
    big_snippets = get_date_snippets(text)

    # Smart splitting:
    # - For schedule grids (e.g., "DETAILED SCHEDULE", "DAY INSTRUCTOR" headers),
    #   split into per-date mini-snippets so the model can reliably attach
    #   readings to each class.
    # - For all other snippets (narrative + deadlines, etc.), keep the big
    #   snippet intact so multi-date "due X" phrases stay together.
    snippets: List[str] = []
    for big in big_snippets:
        lower = big.lower()
        is_schedule_grid = "detailed schedule" in lower or "day instructor" in lower

        if is_schedule_grid:
            mini = split_snippet_by_valid_dates(big)
            snippets.extend(mini)
        else:
            snippets.append(big)

    print(f"📍 Found {len(big_snippets)} snippets containing dates")
    print(f"📍 After smart splitting: {len(snippets)} snippets to analyze\n")

    # Build assessment context string if provided
    assessment_context = None
    if assessment_components:
        lines = []
        for comp in assessment_components:
            name = comp.get("name", "Unknown")
            comp_type = comp.get("type", "assignment")
            weight = comp.get("weight_percent", 0)
            lines.append(f"- {name} ({comp_type}, {weight}% of grade)")
        assessment_context = "\n".join(lines)
        print(f"📋 Using {len(assessment_components)} assessment components for context\n")

    # Optional debugging: show snippets
    if show_snippets:
        print("=" * 80)
        print("EXTRACTED SNIPPETS:")
        print("=" * 80)
        for i, snippet in enumerate(snippets, 1):
            print(f"\n--- Snippet #{i} ---")
            print(snippet)
            print("-" * 40)
        print("\n")

    # 3. Analyze each snippet with the LLM, passing assessment context
    snippet_items_pairs: List[tuple[str, List[Dict]]] = []

    for i, snippet in enumerate(snippets, 1):
        print(f"Analyzing snippet {i}/{len(snippets)}...", end="\r")
        result = analyze_snippet(snippet, assessment_context)
        if result:
            snippet_items_pairs.append((snippet, result))

    total_llm_items = sum(len(r) for _, r in snippet_items_pairs)
    print(f"\n✅ Analyzed {len(snippets)} snippets, gathered {total_llm_items} date-items\n")

    # 4. Flatten into individual items (deadlines + class sessions)
    items: List[Dict] = []

    for snippet_text, llm_items in snippet_items_pairs:
        lower_snippet = snippet_text.lower()
        has_reading_trigger = any(rt in lower_snippet for rt in READING_TRIGGERS)
        has_hard_trigger = any(ht in lower_snippet for ht in HARD_DEADLINE_TRIGGERS)

        for item in llm_items:
            if not isinstance(item, dict):
                print(f"⚠️  Skipping malformed item of type {type(item)}")
                continue

            kind = item.get("kind")
            date_string = item.get("date_string")

            if not date_string or kind == "ignore":
                continue

            # --- Hard deadlines ---
            if kind == "hard_deadline":
                # Require a hard-deadline trigger word somewhere in the snippet
                if not has_hard_trigger:
                    continue

                for t in item.get("hard_deadlines", []):
                    title = (t.get("title") or "").strip()
                    if not title:
                        continue
                    deadline_type = t.get("type", "deadline")
                    description = t.get("description", "").strip()

                    obj: Dict = {
                        "kind": "hard_deadline",
                        "date": date_string,
                        "type": deadline_type,
                        "title": title,
                        "description": description,
                    }
                    assessment_name = t.get("assessment_name")
                    if assessment_name:
                        obj["assessment_name"] = assessment_name
                    items.append(obj)

            # --- Class sessions (one item per date, readings bundled) ---
            elif kind == "class_session":
                session_title = (item.get("session_title") or "").strip()
                if not session_title:
                    session_title = f"Class session on {date_string}"

                readings: List[Dict] = []

                if has_reading_trigger:
                    # Preparatory readings
                    for t in item.get("prep_tasks", []):
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

                    # Mandatory/optional readings
                    for t in item.get("mandatory_tasks", []):
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

    # 5. Add inline 'DEADLINE:'-style admin deadlines from raw text
    inline_deadlines = extract_inline_deadlines_from_text(text)
    items.extend(inline_deadlines)

    # 6. Simple de-duplication by (date, type, title)
    unique_items: List[Dict] = []
    seen_keys = set()
    for it in items:
        key = (it.get("date"), it.get("type"), it.get("title"))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_items.append(it)

    return unique_items


# Main execution
if __name__ == "__main__":
    print("=" * 80)
    print("📅 DEADLINE EXTRACTION TEST (Snippet-Based)")
    print("=" * 80)
    print()

    # Check if file path is provided
    if len(sys.argv) < 2:
        # If no argument, look for the most recent file in uploads folder
        uploads_dir = Path(__file__).parent.parent.parent / "uploads"
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
                print("Usage: python test_deadline_extraction.py <path_to_pdf>")
                sys.exit(1)
        else:
            print("❌ Uploads folder not found")
            print("Usage: python test_deadline_extraction.py <path_to_pdf>")
            sys.exit(1)
    else:
        file_path = Path(sys.argv[1])

    # Check if file exists
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)

    # Parse the file
    print("🔍 Step 1: Parsing PDF...")
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

    # Extract assessment components first (optional but recommended)
    print("🤖 Step 2a: Extracting assessment components...")
    assessment_components = None
    try:
        from app.utils.test_assessment_parser import extract_assessment_components

        assessment_components = extract_assessment_components(text)
        if assessment_components:
            print(f"   Found {len(assessment_components)} graded components:")
            for comp in assessment_components:
                print(f"      - {comp['name']} ({comp['weight_percent']}%)")
        print()
    except Exception as e:
        print(f"   ⚠️  Could not extract assessments: {e}")
        print("   Continuing without assessment context...\n")

    # Extract deadlines + class sessions
    print("🤖 Step 2b: Extracting deadlines and class sessions using snippet-based approach...")
    print(f"OpenAI API Key configured: {'Yes ✅' if api_key_valid else 'No ❌'}")
    if api_key_valid:
        print(f"   Using API key: {settings.OPENAI_API_KEY[:15]}...")
    print()

    if not client:
        print("❌ Cannot proceed without OpenAI API key")
        sys.exit(1)

    # Ask if user wants to see snippets
    show_snippets_input = input(
        "🔍 Show extracted snippets for debugging? (y/n): "
    ).lower().strip()
    show_snippets = show_snippets_input == "y"
    print()

    try:
        items = extract_all_tasks_from_syllabus(
            text,
            show_snippets=show_snippets,
            assessment_components=assessment_components,
        )

        print("=" * 80)
        print(f"📋 EXTRACTED {len(items)} ITEMS (deadlines + class sessions)")
        print("=" * 80)
        print()

        if not items:
            print("⚠️  No items found.")
        else:
            for i, item in enumerate(items, 1):
                print(f"Item #{i}:")
                print(f"  📅 Date:        {item.get('date', 'N/A')}")
                print(f"  🏷️  Type:        {item.get('type', 'N/A')}")
                print(f"  📌 Title:       {item.get('title', 'N/A')}")
                desc = item.get("description")
                if desc:
                    print(f"  📝 Description: {desc}")
                if "assessment_name" in item:
                    print(f"  🎯 Assessment:  {item['assessment_name']}")

                # Print readings for class sessions
                if item.get("type") == "class_session":
                    readings = item.get("readings") or []
                    if readings:
                        print("  📚 Readings:")
                        for r in readings:
                            kind = r.get("kind", "prep")
                            if kind == "mandatory":
                                label = "mandatory"
                            elif kind == "optional":
                                label = "optional"
                            else:
                                label = "prep"
                            r_title = r.get("title", "Untitled reading")
                            r_type = r.get("reading_type", "reading")
                            print(f"    - [{label}] {r_title} ({r_type})")

                print()

        print("=" * 80)
        print(f"✅ Extraction complete! Found {len(items)} items")
        print("=" * 80)

        # Option to save to JSON
        if items:
            print()
            save_option = input(
                "💾 Save results to JSON file? (y/n): "
            ).lower().strip()
            if save_option == "y":
                output_file = (
                    Path(__file__).parent.parent.parent
                    / "uploads"
                    / f"{file_path.stem}_tasks.json"
                )
                with open(output_file, "w") as f:
                    json.dump(items, f, indent=2)
                print(f"✅ Saved to: {output_file}")

    except Exception as e:
        print(f"❌ Error extracting tasks: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
