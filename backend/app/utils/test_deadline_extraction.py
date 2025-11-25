#!/usr/bin/env python3
#!/usr/bin/env python3
"""
Standalone script to test deadline extraction from PDF files
Uses snippet-based approach for reliability across different syllabi
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

# Matches:
#  - 6/9, 06/09, 6-9-2022, 6.9.22, 13/10/2023
#  - Sept 11, Sep 11, September 11
DATE_REGEX = re.compile(
    r"\b("
    r"(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?"  # numeric dd/mm(/yyyy)?
    r"|"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+\d{1,2}"  # short month names
    r"|"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}"  # long names
    r")\b",
    re.IGNORECASE,
)


def get_date_snippets(text: str, before: int = 1, after: int = 3) -> List[str]:
    """
    Extract coarse snippets of text around lines that contain at least one date.
    Later, each snippet will be split further into one snippet per date.
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


def extract_date_strings(snippet: str) -> List[str]:
    """
    Extract valid date-like strings (day + month) from a snippet
    and ignore things like academic years.
    """
    matches = DATE_REGEX.findall(snippet)
    date_strings: List[str] = []

    for match in matches:
        full_match = match[0].strip()

        # Check if numeric: dd/mm(/yyyy)?
        m = re.match(r"(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?$", full_match)
        if m:
            day, month = int(m.group(1)), int(m.group(2))
            if 1 <= day <= 31 and 1 <= month <= 12:
                date_strings.append(full_match)
            continue

        # Month-name formats (e.g. "Sept 11", "September 11")
        if any(
            mname in full_match.lower()
            for mname in [
                "jan",
                "feb",
                "mar",
                "apr",
                "may",
                "jun",
                "jul",
                "aug",
                "sep",
                "oct",
                "nov",
                "dec",
            ]
        ):
            date_strings.append(full_match)
            continue

    # Deduplicate
    return list(set(date_strings))


def split_snippet_by_dates(snippet: str) -> List[str]:
    """
    Within a large snippet containing many dates, split it into smaller
    chunks, each starting at one date and ending before the next date.
    """
    matches = list(DATE_REGEX.finditer(snippet))
    if not matches:
        return [snippet]

    chunks: List[str] = []

    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(snippet)
        chunk = snippet[start:end].strip()
        if chunk:
            chunks.append(chunk)

    return chunks


def analyze_snippet(snippet: str) -> Optional[List[Dict]]:
    """
    Call the LLM on a mini-snippet (usually corresponding to one date
    + its local context) and get an array of date-level items.
    """
    if not client:
        return None

    date_strings = extract_date_strings(snippet)
    if not date_strings:
        return None

    unique_dates = sorted(set(date_strings))
    date_hint = ", ".join(unique_dates)

    prompt = f"""
You are processing a short excerpt from a university syllabus. The text is
shown below. It contains one or more explicit date strings.

Your job is to identify ALL relevant student tasks/deadlines in this snippet,
GROUPED BY DATE STRING.

The allowed date strings for this snippet are:
{date_hint}

For EACH distinct date string, you may return:
- a "class_session" (class meeting + its prep/mandatory tasks), or
- a "hard_deadline" (exam, assignment, project, registration, confirmation), or
- "ignore" if that date is not relevant for student workload planning.

IMPORTANT:
- Use ONLY the date strings above, do NOT invent or guess new dates.
- Do NOT normalize dates to YYYY-MM-DD. Instead, use the exact substring
  from the text as "date_string".
- For class sessions, treat:
  - 'preparatory', 'read before class', 'pre-class', etc. as MUST-DO tasks
    due by that class date.
  - 'mandatory' readings as SHOULD-DO tasks for that session; target date is
    also that class date.
- For hard deadlines, create tasks under "hard_deadlines".

Return a JSON ARRAY. Each element corresponds to ONE date string and has:

{{
  "kind": "class_session | hard_deadline | ignore",
  "date_string": "<one of: {date_hint}>",
  "session_title": "optional, for class_session",
  "prep_tasks": [{{"title": "...", "type": "reading_preparatory"}}],
  "mandatory_tasks": [{{"title": "...", "type": "reading_mandatory"}}],
  "hard_deadlines": [
    {{"title": "...", "type": "assignment | exam | project | administrative",
      "description": "max 120 chars"}}
  ]
}}

If nothing useful for a given date, you may omit that date entirely or set
"kind": "ignore" and empty lists.

Syllabus snippet:
\"\"\"{snippet}\"\"\""""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
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


def extract_all_tasks_from_syllabus(text: str, show_snippets: bool = False) -> List[Dict]:
    """Main pipeline: extract snippets, analyze each, flatten into tasks."""

    # 1. Extract coarse big snippets that contain dates
    big_snippets = get_date_snippets(text)

    # 2. Split each big snippet into smaller per-date snippets
    snippets: List[str] = []
    for big in big_snippets:
        mini = split_snippet_by_dates(big)
        snippets.extend(mini)

    print(f"📍 Found {len(big_snippets)} big snippets")
    print(f"📍 After splitting: {len(snippets)} mini-snippets\n")

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

    # 3. Analyze each mini-snippet with the LLM
    all_items: List[Dict] = []

    for i, snippet in enumerate(snippets, 1):
        print(f"Analyzing snippet {i}/{len(snippets)}...", end="\r")
        result = analyze_snippet(snippet)
        if result:
            all_items.extend(result)

    print(f"\n✅ Analyzed {len(snippets)} snippets, gathered {len(all_items)} date-items\n")

    # 4. Flatten into individual tasks (keep dates as date_string for now)
    tasks: List[Dict] = []

    for item in all_items:
        if not isinstance(item, dict):
            print(f"⚠️  Skipping malformed item of type {type(item)}")
            continue

        kind = item.get("kind")
        date_string = item.get("date_string")

        if not date_string or kind == "ignore":
            continue

        if kind == "class_session":
            session_title = item.get("session_title", "")

            # Prep tasks (before class)
            for t in item.get("prep_tasks", []):
                tasks.append(
                    {
                        "date": date_string,
                        "title": t["title"],
                        "description": f"Prep for: {session_title}"
                        if session_title
                        else "Preparatory reading",
                        "type": t.get("type", "reading_preparatory"),
                    }
                )

            # Mandatory tasks
            for t in item.get("mandatory_tasks", []):
                tasks.append(
                    {
                        "date": date_string,
                        "title": t["title"],
                        "description": f"For session: {session_title}"
                        if session_title
                        else "Mandatory reading",
                        "type": t.get("type", "reading_mandatory"),
                    }
                )

        elif kind == "hard_deadline":
            for t in item.get("hard_deadlines", []):
                tasks.append(
                    {
                        "date": date_string,
                        "title": t["title"],
                        "description": t.get("description", ""),
                        "type": t.get("type", "deadline"),
                    }
                )

    return tasks


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

    # Extract deadlines
    print("🤖 Step 2: Extracting deadlines using snippet-based approach...")
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
        tasks = extract_all_tasks_from_syllabus(text, show_snippets=show_snippets)

        print("=" * 80)
        print(f"📋 EXTRACTED {len(tasks)} TASKS/DEADLINES")
        print("=" * 80)
        print()

        if not tasks:
            print("⚠️  No tasks found.")
        else:
            for i, task in enumerate(tasks, 1):
                print(f"Task #{i}:")
                print(f"  📌 Title:       {task.get('title', 'N/A')}")
                print(f"  📅 Date:        {task.get('date', 'N/A')}")
                print(f"  📝 Description: {task.get('description', 'N/A')}")
                print(f"  🏷️  Type:        {task.get('type', 'N/A')}")
                print()

        print("=" * 80)
        print(f"✅ Extraction complete! Found {len(tasks)} tasks")
        print("=" * 80)

        # Option to save to JSON
        if tasks:
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
                    json.dump(tasks, f, indent=2)
                print(f"✅ Saved to: {output_file}")

    except Exception as e:
        print(f"❌ Error extracting tasks: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
