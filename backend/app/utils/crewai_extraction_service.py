"""
CrewAI-based extraction service for production use.
Integrates the 4-agent pipeline into the API.

Note: Requires Python 3.10+ and crewai package installed.
"""
import json
import re
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

# Try to import CrewAI (requires Python 3.10+)
try:
    from crewai import Agent, Task, Crew
    CREWAI_AVAILABLE = True
except (ImportError, TypeError):
    CREWAI_AVAILABLE = False
    Agent = Task = Crew = None

# Local imports
from app.config import settings
from app.utils.pdf_parser import parse_pdf, parse_text_document

# Date regex for candidate extraction
DATE_REGEX = re.compile(
    r"\b("
    r"(\d{1,2})[/.](\d{1,2})(?:[/.](\d{2,4}))?"
    r"|"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+\d{1,2}"
    r"|"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}"
    r")\b",
    re.IGNORECASE,
)


def is_valid_date_token(token: str) -> bool:
    """Validate if a date token is reasonable."""
    token = token.strip()
    if "\n" in token:
        return False
    
    # Numeric formats
    m_num = re.match(r"^(\d{1,2})[/.](\d{1,2})(?:[/.](\d{2,4}))?$", token)
    if m_num:
        if re.match(r"^[1-9]/[1-9]$", token):
            return False
        day, month = int(m_num.group(1)), int(m_num.group(2))
        return 1 <= day <= 31 and 1 <= month <= 12
    
    # Month name formats
    if re.match(r"(?i)^(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}$", token):
        return True
    if re.match(r"(?i)^(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}$", token):
        return True
    
    return False


def extract_date_candidates(indexed_lines: List[Dict]) -> List[Dict]:
    """Find all valid date tokens with their line index."""
    candidates: List[Dict] = []
    for line in indexed_lines:
        idx = line["index"]
        txt = line["text"]
        for m in DATE_REGEX.finditer(txt):
            token = m.group(0).strip()
            if is_valid_date_token(token):
                candidates.append({
                    "date_string": token,
                    "line_index": idx,
                    "raw_match": token,
                })
    return candidates


# ============================================================================
# CrewAI Agents (initialized lazily when needed)
# ============================================================================

def create_agents():
    """Create and return all agents. Only called when extraction is performed."""
    if not CREWAI_AVAILABLE:
        raise ImportError("CrewAI is not available")
    
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
        verbose=False,
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
        verbose=False,
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
        verbose=False,
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
        verbose=False,
    )
    
    return segmentation_agent, extraction_agent, qa_agent, workload_estimation_agent


# ============================================================================
# Main Extraction Function
# ============================================================================

def extract_with_crew_ai(
    text: str,
    assessment_components: Optional[List[Dict]] = None
) -> Dict:
    """
    Run the full 4-agent CrewAI pipeline on syllabus text.
    
    Args:
        text: Full syllabus text
        assessment_components: Optional list of graded components
    
    Returns:
        Dict with items_with_workload, qa_report, and metadata
    """
    if not CREWAI_AVAILABLE:
        return {
            "success": False,
            "error": "CrewAI not available. Requires Python 3.10+ and crewai package.",
            "items_with_workload": [],
        }
    
    try:
        # Create agents (lazy initialization)
        segmentation_agent, extraction_agent, qa_agent, workload_estimation_agent = create_agents()
        # Step 1: Preprocess text into indexed lines
        lines = text.splitlines()
        indexed_lines = [{"index": i, "text": line} for i, line in enumerate(lines)]
        
        # Extract date candidates
        date_candidates = extract_date_candidates(indexed_lines)
        
        if not date_candidates:
            return {
                "success": False,
                "error": "No date candidates found in syllabus",
                "items_with_workload": [],
            }
        
        # Step 2: Agent 1 - Segmentation
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
                "   - Include ALL lines that belong to that date's session (week label, date, topic, readings, assignments, notes).\n"
                "   - Include forward-looking references like 'by class #3', 'prior to next class', 'due in 2 weeks' - these belong to the session where they appear.\n"
                "   - Ignore purely decorative headers/footers and column labels like 'Day / Instructor / Topic'.\n"
                "   - The extraction agent (Agent 2) will handle resolving forward references to actual dates.\n"
                "4. Create a 'session_dates' array mapping session/class numbers to their calendar dates:\n"
                "   - Extract session numbers from text like 'Class 1', 'Session 2', 'Week 3', etc.\n"
                "   - Map each session number to its corresponding date_string.\n"
                "   - This helps later agents resolve forward references like 'due by class #3'.\n"
                "5. Also group non-schedule content that might be relevant later (e.g., 'Assessment & Grading', "
                "'Exams', 'Policies') into non_schedule_blocks.\n"
                "6. Do NOT interpret the meaning of the content or extract deadlines/readings; your job is only "
                "to segment and group text into blocks.\n"
                "7. Do NOT invent dates. Only use date strings that appear in {date_candidates} or in the text.\n\n"
                "OUTPUT FORMAT:\n"
                "Return a single JSON object with:\n"
                "{\n"
                "  \"schedule_blocks\": [\n"
                "    {\n"
                "      \"date_string\": \"<canonical date string>\",\n"
                "      \"session_number\": <optional int, e.g., 1, 2, 3 if mentioned in text>,\n"
                "      \"line_indices\": [list of ints],\n"
                "      \"raw_block\": \"concatenated raw text for this block\"\n"
                "    },\n"
                "    ...\n"
                "  ],\n"
                "  \"session_dates\": [\n"
                "    {\"session_number\": 1, \"date\": \"Oct 22\"},\n"
                "    {\"session_number\": 2, \"date\": \"Oct 29\"},\n"
                "    {\"session_number\": 3, \"date\": \"Nov 5\"},\n"
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
                "A single JSON object with the keys 'schedule_blocks', 'session_dates', and 'non_schedule_blocks', "
                "as described in the instructions."
            ),
            agent=segmentation_agent,
        )
        
        seg_crew = Crew(
            agents=[segmentation_agent],
            tasks=[segmentation_task],
            verbose=False,
            memory=False,
        )
        
        seg_inputs = {
            "indexed_lines": json.dumps(indexed_lines, indent=2),  # Process all lines
            "date_candidates": json.dumps(date_candidates, indent=2),
            "sections_hint": json.dumps([]),
        }
        
        seg_result_raw = seg_crew.kickoff(inputs=seg_inputs)
        seg_result_str = seg_result_raw.raw if hasattr(seg_result_raw, 'raw') else str(seg_result_raw)
        
        try:
            seg_data = json.loads(seg_result_str.strip())
        except:
            m = re.search(r"\{.*\}", seg_result_str, re.DOTALL)
            if not m:
                return {"success": False, "error": "Segmentation failed", "items_with_workload": []}
            seg_data = json.loads(m.group(0))
        
        schedule_blocks = seg_data.get("schedule_blocks", [])
        session_dates_raw = seg_data.get("session_dates", [])
        
        # ============================================================================
        # PHASE 6 TASK 6.1: BUILD SESSION DATE MAPPING
        # Addresses Issues #1, #4, #12 (Foundation for forward reference resolution)
        # ============================================================================
        
        # Strategy 1: Use Agent 1's explicit session_dates mapping
        session_dates_map = {}
        for session_info in session_dates_raw:
            sess_num = session_info.get("session_number")
            date = session_info.get("date")
            if sess_num and date:
                session_dates_map[sess_num] = date
        
        # Strategy 2: Fallback - infer from schedule_blocks if Agent 1 didn't provide complete mapping
        # This handles cases where Agent 1 misses some session numbers
        for idx, block in enumerate(schedule_blocks):
            session_num = block.get("session_number")
            date_str = block.get("date_string", "")
            
            # Use explicit session_number if provided by Agent 1
            if session_num and date_str:
                if session_num not in session_dates_map:
                    session_dates_map[session_num] = date_str
            # Fallback: assume sequential numbering (session 1, 2, 3, ...)
            elif date_str:
                inferred_session_num = idx + 1
                if inferred_session_num not in session_dates_map:
                    session_dates_map[inferred_session_num] = date_str
        
        # DEBUG: Log session dates mapping with coverage stats
        print(f"\n🔍 DEBUG Agent 1 - Extracted {len(schedule_blocks)} schedule blocks")
        print(f"   Session dates mapping: {len(session_dates_map)} sessions mapped")
        if session_dates_map:
            print(f"   🗓️  Session Date Map:")
            for sess_num in sorted(session_dates_map.keys()):
                print(f"      Session {sess_num} → {session_dates_map[sess_num]}")
        else:
            print(f"   ⚠️  WARNING: No session dates mapped - forward references may fail")
        
        if not schedule_blocks:
            return {"success": False, "error": "No schedule blocks found", "items_with_workload": []}
        
        # Step 3: Agent 2 - Extraction (process each block)
        extraction_task = Task(
            description=(
                "You are the Schedule Interpretation / Task Extraction Agent.\n\n"
                "INPUTS YOU RECEIVE:\n"
                "- One schedule block: {block_text}\n"
                "- Date string for this block: {date_string}\n"
                "- Session dates mapping: {session_dates} (maps session numbers to calendar dates)\n"
                "- Graded assessment components: {assessment_components}\n\n"
                "YOUR GOAL FOR THIS SINGLE BLOCK:\n"
                "1. Read the block and identify:\n"
                "   - Class session information (topic, title, week label, etc.).\n"
                "   - Preparatory readings or 'read before class' items (for THIS session only - do NOT include forward references here).\n"
                "   - Mandatory or optional readings explicitly identified as readings.\n"
                "   - Hard deadlines: anything clearly due, to be submitted, exam dates, quizzes, tests, projects, etc.\n"
                "   \n"
                "   ⚠️ **CRITICAL RULE FOR FORWARD REFERENCES**:\n"
                "   - If text says 'by class #X', 'prior to Xth class', 'for next session', 'by session Y', etc.\n"
                "   - Do NOT put these in prep_tasks, mandatory_tasks, or within the class_session item\n"
                "   - Instead, create a SEPARATE item in your output array with kind='hard_deadline' and the RESOLVED date\n"
                "   - Example: Block for Class 4 (Nov 12) says 'Prior to next (5th) class, watch videos'\n"
                "     → Do NOT add to Class 4's prep_tasks\n"
                "     → Instead, create separate hard_deadline item with date='Nov 19' (Class 5's date)\n"
                "   \n"
                "2. Date extraction rules:\n"
                "   - FIRST PRIORITY: Look for explicit calendar dates (e.g., 'March 15', '3/15/2024', 'Oct 22').\n"
                "   - SECOND PRIORITY: If only relative dates exist (e.g., 'Week 1', 'Session 2'), use the date_string provided for this block.\n"
                "   - THIRD PRIORITY: Use {session_dates} mapping for forward references (see next section).\n"
                "   - PRESERVE exact date format from the syllabus - do NOT convert or reformat dates.\n"
                "   - Do NOT invent dates that don't appear in the text or session_dates.\n"
                "\n"
                "3. FORWARD-LOOKING DATE RESOLUTION:\n"
                "   When text contains forward references to future classes/sessions, resolve them using {session_dates}:\n"
                "   \n"
                "   **Recognition Keywords**: Look for phrases indicating future dates:\n"
                "   - 'by class #X' / 'by session X' / 'by week X'\n"
                "   - 'prior to [Xth] class' / 'before [Xth] session'\n"
                "   - 'next class' / 'next session' / 'following week'\n"
                "   - 'due [date]' / 'submit by [date]'\n"
                "   - 'prepare for class X' / 'read for session X'\n"
                "   \n"
                "   **Resolution Strategy**:\n"
                "   - If text says 'by class #3' or 'by session 3': Look up session_number=3 in {session_dates}, use that date\n"
                "   - If text says 'prior to next class': Find the NEXT session after current block, use that date\n"
                "   - If text says 'before 6th class': Look up session_number=6 in {session_dates}, use that date\n"
                "   - If text says 'get started on X, due [date]': Create ONE deadline with the DUE date ONLY (ignore 'get started')\n"
                "   - If text says 'watch video for next week': Use the NEXT session's date from {session_dates}\n"
                "   \n"
                "   **CRITICAL RULES**:\n"
                "   - Do NOT use the current block's date_string for forward-looking tasks\n"
                "   - Always resolve session numbers using {session_dates} mapping\n"
                "   - If session number not in {session_dates}, skip that task (don't guess)\n"
                "   - Create only ONE task per deadline (don't create duplicates for 'start' and 'due' dates)\n"
                "   \n"
                "   **Examples**:\n"
                "   \n"
                "   Example 1: Forward reference by class number\n"
                "   - Current block: date_string='Oct 22', session_number=1\n"
                "   - Text: 'Read first 3 chapters by class #3'\n"
                "   - session_dates shows: [{\"session_number\": 3, \"date\": \"Nov 5\"}, ...]\n"
                "   - Resolution: Look up session 3 → Nov 5\n"
                "   - Output: Create reading task with date='Nov 5' (NOT 'Oct 22')\n"
                "   \n"
                "   Example 2: Forward reference to next session\n"
                "   - Current block: date_string='Nov 12', session_number=4\n"
                "   - Text: 'Topic: Multi-party negotiations. Prior to next (5th) class, watch strategy videos.'\n"
                "   - session_dates shows: [{\"session_number\": 5, \"date\": \"Nov 19\"}, ...]\n"
                "   - Resolution: 'Prior to next (5th) class' refers to session 5 → Look up session 5 → Nov 19\n"
                "   - Output: Create TWO items in your array:\n"
                "     1. The Class 4 session (Nov 12) with its topics\n"
                "     2. A SEPARATE hard_deadline item with date='Nov 19' for the forward reference\n"
                "   - JSON Output:\n"
                "     [\n"
                "       {\n"
                "         \"kind\": \"class_session\",\n"
                "         \"date_string\": \"Nov 12\",\n"
                "         \"session_title\": \"Multi-party Negotiations\",\n"
                "         \"prep_tasks\": [],\n"
                "         \"mandatory_tasks\": [],\n"
                "         \"hard_deadlines\": []\n"
                "       },\n"
                "       {\n"
                "         \"kind\": \"hard_deadline\",\n"
                "         \"date_string\": \"Nov 19\",\n"
                "         \"hard_deadlines\": [{\n"
                "           \"title\": \"Watch strategy videos\",\n"
                "           \"type\": \"reading\",\n"
                "           \"description\": \"Watch strategy videos prior to Class 5.\"\n"
                "         }]\n"
                "       }\n"
                "     ]\n"
                "   \n"
                "   Example 3: Multiple forward references in one block\n"
                "   - Current block: date_string='Oct 22', session_number=1\n"
                "   - Text: 'Read Chapter 1 for today. Read Chapters 2-3 by class #3. Read Chapter 4 by class #5.'\n"
                "   - Resolution:\n"
                "     * 'Read Chapter 1 for today' → date='Oct 22' (current session) → in class_session's prep_tasks\n"
                "     * 'Read Chapters 2-3 by class #3' → session_dates[3]='Nov 5' → SEPARATE hard_deadline with date='Nov 5'\n"
                "     * 'Read Chapter 4 by class #5' → session_dates[5]='Nov 19' → SEPARATE hard_deadline with date='Nov 19'\n"
                "   - Output: Create 3 items total: 1 class_session + 2 hard_deadline items with resolved dates\n"
                "   \n"
                "   **CRITICAL FORWARD REFERENCE RULE**:\n"
                "   - When you see 'by class #X' or 'prior to Xth class', do NOT put it in prep_tasks/mandatory_tasks\n"
                "   - Instead, create a SEPARATE item with kind='hard_deadline' using the RESOLVED date\n"
                "   - Each forward reference becomes its own hard_deadline item with the correct future date\n"
                "   \n"
                "   Example 4: Assignment with start and due dates\n"
                "   - Current block: date_string='Nov 12', session_number=4\n"
                "   - Text: 'Get started on final paper (due Dec 15)'\n"
                "   - Resolution: Only use the DUE date 'Dec 15', ignore 'get started'\n"
                "   - Output: Create ONE assignment task with date='Dec 15' (NOT two tasks for Nov 12 and Dec 15)\n"
                "\n"
                "4. DUPLICATE PREVENTION RULES:\n"
                "   Assignments and tasks are often mentioned multiple times across blocks (introduction, reminders, due dates).\n"
                "   Extract each task ONLY ONCE using the FINAL DUE DATE to prevent duplicate tasks.\n"
                "   \n"
                "   **Introduction/Reminder Keywords** (NOT deadlines - skip these mentions):\n"
                "   - 'get started on X'\n"
                "   - 'consider X'\n"
                "   - 'begin working on X'\n"
                "   - 'you should have completed X' (past tense - already due)\n"
                "   - 'X was due yesterday'\n"
                "   - 'make progress on X'\n"
                "   - 'start thinking about X'\n"
                "   \n"
                "   **Deadline Keywords** (EXTRACT these - actual due dates):\n"
                "   - 'due [date]'\n"
                "   - 'submit by [date]'\n"
                "   - 'turn in [date]'\n"
                "   - 'deadline [date]'\n"
                "   - 'hand in [date]'\n"
                "   - 'submit on [date]'\n"
                "   \n"
                "   **Extraction Strategy**:\n"
                "   - When processing a block, check if the task title sounds like an assignment you've seen before\n"
                "   - If text only mentions 'get started' or 'begin working', mark it internally but DON'T extract yet\n"
                "   - Only extract when you find the explicit DUE date with deadline keywords\n"
                "   - If multiple blocks mention the same task with different dates, use the EARLIEST explicit due date\n"
                "   - If you see 'should have completed X by yesterday', DO NOT extract (it's already past due from previous block)\n"
                "   \n"
                "   **Example: Sales-video task appears 3 times**\n"
                "   \n"
                "   Block 1 (Oct 29): 'After October 25th... get started on Sales-video task, due Noon, Tuesday, Nov 4th'\n"
                "   → Extract: YES - has explicit due date 'Nov 4'\n"
                "   \n"
                "   Block 2 (Nov 4): [no mention of Sales-video]\n"
                "   → Extract: NO - not mentioned\n"
                "   \n"
                "   Block 3 (Nov 5): 'You should have completed Sales-video task by yesterday noon'\n"
                "   → Extract: NO - past tense reminder, already due in Block 1\n"
                "   \n"
                "   Result: Extract ONCE in Block 1 with date='Nov 4'\n"
                "   {\n"
                "     \"kind\": \"hard_deadline\",\n"
                "     \"date_string\": \"Nov 4\",\n"
                "     \"hard_deadlines\": [{\n"
                "       \"title\": \"Sales-video task\",\n"
                "       \"type\": \"assignment\",\n"
                "       \"description\": \"[Weight: 10 pts] Watch assigned videos and complete survey. Due noon, Tuesday Nov 4th.\"\n"
                "     }]\n"
                "   }\n"
                "   \n"
                "   **Example: Same reading mentioned with different contexts**\n"
                "   \n"
                "   Block 1 (Oct 22): 'Begin reading Chapter 3 for next week'\n"
                "   → Extract: NO - just 'begin reading', no due date\n"
                "   \n"
                "   Block 2 (Oct 29): 'Chapter 3 reading due today. Discuss in class.'\n"
                "   → Extract: YES - explicit due date 'Oct 29'\n"
                "   \n"
                "   Block 3 (Nov 5): 'Refer back to Chapter 3 from last month'\n"
                "   → Extract: NO - reference to past reading, not a new task\n"
                "   \n"
                "   Result: Extract ONCE in Block 2 with date='Oct 29'\n"
                "   \n"
                "   **CRITICAL RULES**:\n"
                "   - Each unique assignment/task should appear ONCE in the final output\n"
                "   - Always use the explicit DUE date, never the 'get started' date\n"
                "   - Skip past-tense reminders ('you should have completed')\n"
                "   - If unsure whether it's a duplicate, extract it (better than missing a task)\n"
                "\n"
                "5. CONDITIONAL TASK DETECTION:\n"
                "   Many syllabi contain optional or conditional tasks that only apply to certain students.\n"
                "   Identify these tasks and mark them appropriately to help students understand requirements.\n"
                "   \n"
                "   **Conditional Keywords** (indicating optional/conditional tasks):\n"
                "   - 'if you are X' / 'if you want to X'\n"
                "   - 'for those who' / 'for students who'\n"
                "   - 'students who already' / 'those who did not'\n"
                "   - 'OR' (indicating an alternative)\n"
                "   - 'optional' / 'optionally'\n"
                "   - 'alternative to X'\n"
                "   - 'only if' / 'unless you'\n"
                "   - 'choose one of' / 'pick either'\n"
                "   \n"
                "   **Detection Strategy**:\n"
                "   - When you see these keywords, set is_optional=true\n"
                "   - Extract the full conditional clause into the 'conditions' field\n"
                "   - Be specific about who the condition applies to\n"
                "   - Capture both positive conditions ('for those who') and negative conditions ('those who did not')\n"
                "   \n"
                "   **Examples**:\n"
                "   \n"
                "   Example 1: Optional survey for certain students\n"
                "   - Text: 'Students who already know Story of the Tree should fill out this survey'\n"
                "   - Detection: 'Students who already' → conditional keyword\n"
                "   - Output:\n"
                "     {\n"
                "       \"title\": \"Story of the Tree Survey\",\n"
                "       \"type\": \"assignment\",\n"
                "       \"is_optional\": true,\n"
                "       \"conditions\": \"Only for students who already took similar course\"\n"
                "     }\n"
                "   \n"
                "   Example 2: Conditional videos based on background\n"
                "   - Text: 'For those who did not learn negotiations from Barry Nalebuff, watch his videos'\n"
                "   - Detection: 'For those who did not' → conditional keyword\n"
                "   - Output:\n"
                "     {\n"
                "       \"title\": \"Barry Nalebuff Negotiation Videos\",\n"
                "       \"type\": \"reading\",\n"
                "       \"is_optional\": true,\n"
                "       \"conditions\": \"Only for students without Core Negotiations background\"\n"
                "     }\n"
                "   \n"
                "   Example 3: Alternative assignment option\n"
                "   - Text: 'If you are unhappy with your Job-Score, write up a 1-page reflection'\n"
                "   - Detection: 'If you are' → conditional keyword\n"
                "   - Output:\n"
                "     {\n"
                "       \"title\": \"Job-Score Reflection\",\n"
                "       \"type\": \"assignment\",\n"
                "       \"description\": \"1-page write-up reflecting on Job-Case performance\",\n"
                "       \"is_optional\": true,\n"
                "       \"conditions\": \"Alternative for students unhappy with Job-Case Score\"\n"
                "     }\n"
                "   \n"
                "   Example 4: Multiple assignment options\n"
                "   - Text: 'Choose either the written analysis OR the video presentation'\n"
                "   - Detection: 'either...OR' → alternative options\n"
                "   - Output: Create TWO tasks, both with is_optional=true\n"
                "     Task 1: {\"title\": \"Written Analysis\", \"is_optional\": true, \"conditions\": \"Choose one: written analysis or video\"}\n"
                "     Task 2: {\"title\": \"Video Presentation\", \"is_optional\": true, \"conditions\": \"Choose one: written analysis or video\"}\n"
                "   \n"
                "   **CRITICAL RULES**:\n"
                "   - Default is_optional to false unless conditional keywords detected\n"
                "   - Be specific in conditions field - explain WHO the task is for or WHEN it applies\n"
                "   - Extract both the requirement AND the condition\n"
                "   - If conditions field is empty, set it to empty string (not null)\n"
                "\n"
                "6. TYPE CLASSIFICATION RULES:\n"
                "   CRITICAL: Correctly classify tasks to distinguish graded work from non-graded readings.\n"
                "   The type field determines how students see and prioritize tasks in the UI.\n"
                "   \n"
                "   **Type Categories**:\n"
                "   - 'assignment': Graded work (papers, projects, surveys, videos, case analyses, write-ups)\n"
                "   - 'exam': Tests, quizzes, midterms, finals\n"
                "   - 'project': Major graded projects (can overlap with assignment)\n"
                "   - 'reading': NON-GRADED reading materials ONLY (textbook chapters, articles, prep materials)\n"
                "   - 'administrative': Non-academic tasks (registration, forms, etc.)\n"
                "   \n"
                "   **Classification Strategy**:\n"
                "   1. **FIRST PRIORITY - Check Assessment Components**:\n"
                "      - If task title/name appears in {assessment_components}, it's GRADED\n"
                "      - Graded items are NEVER type='reading'\n"
                "      - Use type='assignment' for graded work (even if it involves watching videos or reading)\n"
                "   \n"
                "   2. **SECOND PRIORITY - Check for Point Values**:\n"
                "      - If text mentions points, percentage, or weight → type='assignment' or 'exam'\n"
                "      - Examples: '10 pts', '5% of grade', 'worth 50 points'\n"
                "   \n"
                "   3. **THIRD PRIORITY - Check Keywords**:\n"
                "      - Exam keywords: 'exam', 'test', 'quiz', 'midterm', 'final' → type='exam'\n"
                "      - Assignment keywords: 'paper', 'project', 'write-up', 'presentation', 'case analysis', \n"
                "        'submit', 'turn in', 'upload', 'survey', 'video task' → type='assignment'\n"
                "      - Reading keywords (ONLY if not graded): 'read chapter', 'read article', 'textbook', \n"
                "        'preparatory reading' → type='reading'\n"
                "   \n"
                "   4. **DEFAULT BEHAVIOR**:\n"
                "      - If unclear and no points mentioned → default to type='reading' for readings\n"
                "      - If unclear and mentions submission/due date → default to type='assignment'\n"
                "   \n"
                "   **Examples**:\n"
                "   \n"
                "   Example 1: Graded video task (Sales-video)\n"
                "   - assessment_components includes: {\"name\": \"Sales-video task\", \"weight\": \"10 pts\"}\n"
                "   - Text: 'Watch assigned videos and complete survey, due Nov 4th'\n"
                "   - Classification: Appears in assessment_components → GRADED\n"
                "   - Output: type='assignment' (NOT 'reading', even though it involves watching videos)\n"
                "   \n"
                "   Example 2: Non-graded reading\n"
                "   - assessment_components: [does not include this reading]\n"
                "   - Text: 'Read Chapter 3 of textbook before class'\n"
                "   - Classification: Not in assessment_components, no points → NOT GRADED\n"
                "   - Output: type='reading'\n"
                "   \n"
                "   Example 3: Graded paper\n"
                "   - assessment_components includes: {\"name\": \"Final Paper\", \"weight\": \"30%\"}\n"
                "   - Text: 'Final Paper due Dec 15 - 10 pages on negotiation strategies'\n"
                "   - Classification: Appears in assessment_components → GRADED\n"
                "   - Output: type='assignment'\n"
                "   \n"
                "   Example 4: Midterm exam\n"
                "   - assessment_components includes: {\"name\": \"Midterm\", \"weight\": \"25%\"}\n"
                "   - Text: 'Midterm exam covering weeks 1-6, Nov 15th'\n"
                "   - Classification: Appears in assessment_components + 'exam' keyword → GRADED EXAM\n"
                "   - Output: type='exam'\n"
                "   \n"
                "   Example 5: Graded case analysis (even if involves reading)\n"
                "   - assessment_components includes: {\"name\": \"Job-Case\", \"weight\": \"15 pts\"}\n"
                "   - Text: 'Read Job-Case and write 2-page analysis, due Oct 29'\n"
                "   - Classification: Appears in assessment_components + 'write' keyword → GRADED\n"
                "   - Output: type='assignment' (NOT 'reading', even though it involves reading)\n"
                "   \n"
                "   **CRITICAL RULES**:\n"
                "   - ALWAYS check {assessment_components} FIRST before assigning type\n"
                "   - If task matches an assessment component name (even partially), it MUST be type='assignment', 'exam', or 'project'\n"
                "   - Type 'reading' is ONLY for non-graded preparatory materials\n"
                "   - When in doubt between 'reading' and 'assignment', choose 'assignment' if there's ANY indication of grading\n"
                "   - Graded activities involving videos, surveys, or reading are still type='assignment'\n"
                "\n"
                "7. If the block mentions a graded assessment component (by name or close variant), link it "
                "via 'assessment_name' in the corresponding hard_deadline.\n"
                "8. DETAILED DESCRIPTION REQUIREMENTS:\n"
                "   - ALWAYS include page numbers for readings when specified (e.g., 'pp. 15-82', 'pages 83-102', 'Chapter 3 pp. 45-67').\n"
                "   - ALWAYS include point values when mentioned (e.g., 'Worth 10 pts', '15 points', '50 pts').\n"
                "   - ALWAYS include word count requirements when specified (e.g., '100-200 words', '500 word reflection').\n"
                "   - ALWAYS include length requirements (e.g., '3-4 pages', '10 minute presentation').\n"
                "   - ALWAYS capture specific deliverable requirements (e.g., 'video response', 'written analysis', 'group presentation').\n"
                "   - Extract ALL specific details from the text - descriptions can be up to 300 characters.\n"
                "9. ASSESSMENT COMPONENT WEIGHT ENRICHMENT:\n"
                "   - When matching a hard_deadline to an assessment_component, check the component's weight/points.\n"
                "   - If the component has a weight, include it at the START of the description in format: '[Weight: X pts]' or '[Weight: X%]'\n"
                "   - Example: '[Weight: 50 pts] 3-4 page write-up with planning document. Due Dec 15th.'\n"
                "   - This helps students prioritize tasks based on their grade impact.\n\n"
                "OUTPUT FORMAT:\n"
                "Return a JSON ARRAY. Each element has:\n"
                "{\n"
                "  \"kind\": \"class_session\" | \"hard_deadline\" | \"ignore\",\n"
                "  \"date_string\": \"<one of the allowed date strings>\",\n"
                "  \"session_title\": \"optional, for class_session\",\n"
                "  \"prep_tasks\": [ {\"title\": \"...\", \"type\": \"reading_preparatory\" | \"reading_optional\" | \"reading_mandatory\", \"description\": \"optional, include page numbers if specified\"} ],\n"
                "  \"mandatory_tasks\": [ {\"title\": \"...\", \"type\": \"reading_mandatory\" | \"reading_optional\", \"description\": \"optional, include page numbers if specified\"} ],\n"
                "  \"hard_deadlines\": [\n"
                "    {\n"
                "      \"title\": \"...\",\n"
                "      \"type\": \"assignment\" | \"exam\" | \"project\" | \"assessment\" | \"administrative\",\n"
                "      \"description\": \"detailed description (max 300 chars, include page numbers, point values, word counts, all specific requirements)\",\n"
                "      \"assessment_name\": \"optional, name from assessment_components if matched\",\n"
                "      \"is_optional\": true | false,\n"
                "      \"conditions\": \"optional, conditional text if is_optional=true (e.g., 'Only for students who...')\"\n"
                "    }\n"
                "  ]\n"
                "}\n\n"
                "EXAMPLE WITH ASSESSMENT COMPONENT LINKING:\n"
                "If assessment_components includes: {\"name\": \"Real World Negotiation\", \"weight\": \"50 pts\"}\n"
                "And the block mentions: 'Real World Negotiation Paper due Dec 15 - 3-4 page write-up'\n"
                "Then extract:\n"
                "{\n"
                "  \"kind\": \"hard_deadline\",\n"
                "  \"date_string\": \"Dec 15\",\n"
                "  \"hard_deadlines\": [\n"
                "    {\n"
                "      \"title\": \"Real World Negotiation Paper\",\n"
                "      \"type\": \"assignment\",\n"
                "      \"description\": \"[Weight: 50 pts] 3-4 page write-up with planning document\",\n"
                "      \"assessment_name\": \"Real World Negotiation\"\n"
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
        
        extraction_crew = Crew(
            agents=[extraction_agent],
            tasks=[extraction_task],
            verbose=False,
            memory=False,
        )
        
        all_items = []
        # Create list of graded component names for type classification reminder
        graded_names = [comp.get("name", "") for comp in (assessment_components or []) if comp.get("name")]
        graded_reminder = (
            f"\n\nREMINDER: The following components are GRADED and should be type='assignment' or 'exam' (NEVER 'reading'):\n"
            f"{', '.join(graded_names) if graded_names else 'None specified'}"
        )
        
        for idx, block in enumerate(schedule_blocks, 1):  # Process all blocks
            # Convert session_dates_map to array format for Agent 2 compatibility
            # Agent 2 expects: [{"session_number": 1, "date": "Oct 22"}, ...]
            session_dates_array = [
                {"session_number": sess_num, "date": date}
                for sess_num, date in sorted(session_dates_map.items())
            ]
            
            block_inputs = {
                "block_text": block.get("raw_block", "") + graded_reminder,
                "date_string": block.get("date_string", ""),
                "session_dates": json.dumps(session_dates_array, indent=2),
                "assessment_components": json.dumps(assessment_components or [], indent=2),
            }
            
            # DEBUG: Log Agent 2 input for blocks with forward references
            if any(pattern in block.get("raw_block", "") for pattern in ["Class 2", "Class 4", "by class #", "Multi-party"]):
                print(f"\n🔍 DEBUG Agent 2 Input for Block {idx} (date: {block.get('date_string')})")
                print(f"   Full block text: '''{block.get('raw_block', '')}'''")
                print(f"   Session dates available: {len(session_dates_array)} sessions")
                if len(session_dates_array) <= 6:  # Only print for small syllabus
                    print(f"   Session dates passed to Agent 2:")
                    for sd in session_dates_array:
                        print(f"      Session {sd['session_number']} → {sd['date']}")
            
            ext_result = extraction_crew.kickoff(inputs=block_inputs)
            ext_str = ext_result.raw if hasattr(ext_result, 'raw') else str(ext_result)
            
            # DEBUG: Log Agent 2 output for blocks with forward references
            if any(pattern in block.get("raw_block", "") for pattern in ["Class 2", "Class 4", "by class #", "Multi-party"]):
                print(f"\n🔍 DEBUG Agent 2 Output for Block {idx}:")
                print(f"   Raw output (first 800 chars): {ext_str[:800]}...")
            
            try:
                items = json.loads(ext_str.strip())
                if isinstance(items, list):
                    all_items.extend(items)
            except:
                continue
        
        # DEBUG: Log Agent 2 output
        print(f"\n🔍 DEBUG Agent 2 - Extracted {len(all_items)} schedule blocks")
        if all_items:
            print(f"   Sample from Agent 2: {json.dumps(all_items[0], indent=2)}")
            print(f"   Agent 2 keys: {list(all_items[0].keys())}")
        
        if not all_items:
            return {"success": False, "error": "No items extracted", "items_with_workload": []}
        
        # ============================================================================
        # READING OVERLAP CONSOLIDATION (Phase 3 Task 3.4)
        # Addresses Issue #7: HBS reading duplicates (Chapters 1-3 and Chapter 3)
        # ============================================================================
        def consolidate_overlapping_readings(items):
            """
            Consolidate reading assignments where one encompasses another.
            E.g., "Read chapters 1-3" encompasses "Read chapter 3"
            
            Strategy:
            1. Group readings by date
            2. Parse chapter/page ranges from titles
            3. For overlapping ranges on same date, keep the broader one
            4. Preserve all non-reading items unchanged
            """
            reading_items = [item for item in items if item.get("type") == "reading" or 
                           (item.get("kind") == "class_session" and 
                            (item.get("prep_tasks") or item.get("mandatory_tasks")))]
            other_items = [item for item in items if item not in reading_items]
            
            def parse_chapters(title):
                """Extract chapter numbers from reading titles."""
                # Match "chapter 1-3", "chapters 1-3", "chapter 3", "Ch. 1-2"
                match = re.search(r'(?:chapter|ch\.?)[s]?\s+(\d+)(?:\s*[-–—]\s*(\d+))?', 
                                title.lower())
                if match:
                    start = int(match.group(1))
                    end = int(match.group(2)) if match.group(2) else start
                    return set(range(start, end + 1))
                return set()
            
            def parse_pages(title):
                """Extract page numbers from reading titles."""
                # Match "pp. 15-82", "pages 83-102", "p. 45"
                match = re.search(r'(?:pp?\.?|pages?)\s+(\d+)(?:\s*[-–—]\s*(\d+))?', 
                                title.lower())
                if match:
                    start = int(match.group(1))
                    end = int(match.group(2)) if match.group(2) else start
                    return set(range(start, end + 1))
                return set()
            
            def get_reading_range(title):
                """Get combined chapter and page range for comparison."""
                chapters = parse_chapters(title)
                pages = parse_pages(title)
                return (chapters, pages)
            
            # Group readings by date
            readings_by_date = {}
            for item in reading_items:
                date = item.get("date_string") or item.get("date", "")
                if date not in readings_by_date:
                    readings_by_date[date] = []
                readings_by_date[date].append(item)
            
            # Consolidate per date
            consolidated = []
            for date, readings in readings_by_date.items():
                if len(readings) == 1:
                    consolidated.extend(readings)
                    continue
                
                # Find overlapping readings
                kept_readings = []
                for i, reading in enumerate(readings):
                    title = reading.get("title", "")
                    if reading.get("kind") == "class_session":
                        # For class sessions, check prep_tasks and mandatory_tasks
                        kept_readings.append(reading)
                        continue
                    
                    chapters_i, pages_i = get_reading_range(title)
                    
                    # Check if this reading is encompassed by another
                    is_encompassed = False
                    for j, other in enumerate(readings):
                        if i == j:
                            continue
                        other_title = other.get("title", "")
                        chapters_j, pages_j = get_reading_range(other_title)
                        
                        # Check if reading i is fully contained in reading j
                        if chapters_i and chapters_j and chapters_i.issubset(chapters_j) and len(chapters_j) > len(chapters_i):
                            is_encompassed = True
                            break
                        if pages_i and pages_j and pages_i.issubset(pages_j) and len(pages_j) > len(pages_i):
                            is_encompassed = True
                            break
                    
                    if not is_encompassed:
                        kept_readings.append(reading)
                
                consolidated.extend(kept_readings)
            
            # DEBUG: Log consolidation results
            removed_count = len(reading_items) - len(consolidated)
            if removed_count > 0:
                print(f"\n🔍 DEBUG Reading Consolidation - Removed {removed_count} overlapping readings")
            
            return consolidated + other_items
        
        # Apply reading consolidation
        all_items = consolidate_overlapping_readings(all_items)
        
        # Flatten nested structure: extract hard_deadlines AND readings from schedule blocks
        flattened_items = []
        for item in all_items:
            if item.get("kind") == "hard_deadline":
                # Direct hard_deadline with date_string
                for deadline in item.get("hard_deadlines", []):
                    flattened_items.append({
                        "date": item.get("date_string", ""),
                        "title": deadline.get("title", ""),
                        "type": deadline.get("type", "assignment"),
                        "description": deadline.get("description", ""),
                        "assessment_name": deadline.get("assessment_name", ""),
                        "is_optional": deadline.get("is_optional", False),
                        "conditions": deadline.get("conditions", ""),
                    })
            elif item.get("kind") == "class_session":
                # Extract readings and prep tasks as individual items
                date_str = item.get("date_string", "")
                session_title = item.get("session_title", "")
                
                # Extract preparatory readings (readings to do before class)
                for task in item.get("prep_tasks", []) or []:
                    task_title = (task.get("title") or "").strip()
                    if not task_title:
                        continue
                    # Use task description if provided, otherwise create default
                    task_desc = task.get("description", "").strip()
                    if not task_desc:
                        task_desc = f"Preparatory reading for {session_title}" if session_title else "Preparatory reading"
                    flattened_items.append({
                        "date": date_str,
                        "title": task_title,
                        "type": "reading",
                        "description": task_desc,
                        "assessment_name": "",
                        "reading_type": task.get("type", "reading_preparatory"),
                    })
                
                # Extract mandatory/optional readings
                for task in item.get("mandatory_tasks", []) or []:
                    task_title = (task.get("title") or "").strip()
                    if not task_title:
                        continue
                    # Use task description if provided, otherwise create default
                    task_desc = task.get("description", "").strip()
                    if not task_desc:
                        task_desc = f"Mandatory reading for {session_title}" if session_title else "Mandatory reading"
                    flattened_items.append({
                        "date": date_str,
                        "title": task_title,
                        "type": "reading",
                        "description": task_desc,
                        "assessment_name": "",
                        "reading_type": task.get("type", "reading_mandatory"),
                    })
                
                # Add hard deadlines within class session
                for deadline in item.get("hard_deadlines", []):
                    flattened_items.append({
                        "date": date_str,
                        "title": deadline.get("title", ""),
                        "type": deadline.get("type", "assignment"),
                        "description": deadline.get("description", ""),
                        "assessment_name": deadline.get("assessment_name", ""),
                        "is_optional": deadline.get("is_optional", False),
                        "conditions": deadline.get("conditions", ""),
                    })
        
        print(f"\n🔍 DEBUG Flattening - {len(flattened_items)} individual deadlines extracted")
        if flattened_items:
            print(f"   Sample flattened item: {json.dumps(flattened_items[0], indent=2)}")
        
        # Step 2: Deduplicate items by (date, type, title) to prevent duplicate deadlines
        unique_items = []
        seen = set()
        for item in flattened_items:
            key = (item.get("date"), item.get("type"), item.get("title"))
            if key in seen:
                continue
            seen.add(key)
            unique_items.append(item)
        
        print(f"\n🔍 DEBUG Deduplication - {len(unique_items)} unique items (removed {len(flattened_items) - len(unique_items)} duplicates)")
        
        all_items = unique_items
        
        if not all_items:
            return {"success": False, "error": "No deadlines found after flattening", "items_with_workload": []}
        
        # Step 3: Filter generic assessment components to prevent Agent 3 from creating fake deadlines
        filtered_assessment_components = []
        generic_keywords = ["participation", "attendance", "class participation", "engagement", "general"]
        for component in (assessment_components or []):
            component_name = (component.get("name") or "").lower()
            # Skip generic components that don't have specific dated deadlines
            if any(keyword in component_name for keyword in generic_keywords):
                continue
            filtered_assessment_components.append(component)
        
        print(f"\n🔍 DEBUG Component Filtering - {len(filtered_assessment_components)} specific components (filtered {len(assessment_components or []) - len(filtered_assessment_components)} generic ones)")
        
        # Step 4: Agent 3 - QA
        qa_task = Task(
            description=(
                "You are the Global QA & Consistency Agent for a syllabus extraction pipeline.\n\n"
                "INPUTS YOU RECEIVE:\n"
                "- A flat list of all extracted items (class sessions + deadlines): {merged_tasks}\n"
                "- The list of graded assessment components: {assessment_components}\n"
                "- Preliminary mapping between components and tasks: {preliminary_mapping}\n"
                "- Raw text of non-schedule sections: {non_schedule_text}\n\n"
                "YOUR GOAL:\n"
                "1. Check coverage: For each SPECIFIC assessment component (exams, papers, projects with due dates), "
                "verify there is a corresponding 'hard_deadline'. IGNORE general/ongoing components like 'Participation' or 'Attendance'.\n"
                "2. Identify missing assessments: SPECIFIC components that appear in grading but have no dated hard_deadline.\n"
                "3. ADVANCED DUPLICATE DETECTION:\n"
                "   Detect tasks with identical or very similar titles appearing on multiple dates.\n"
                "   This often happens when syllabi mention assignments multiple times:\n"
                "   - First mention: 'Get started on X' or 'Begin working on X' (earlier date)\n"
                "   - Second mention: 'X due today' or 'Submit X' (actual due date)\n"
                "   - Third mention: 'You should have completed X' (past-due reminder)\n"
                "   \n"
                "   **Detection Strategy**:\n"
                "   - Group tasks by title similarity (exact match or very close)\n"
                "   - For each group with multiple dates, identify the ACTUAL due date\n"
                "   - Keep ONLY the task with the latest/actual due date\n"
                "   - Remove earlier 'get started' mentions and later 'past due' reminders\n"
                "   \n"
                "   **Examples**:\n"
                "   \n"
                "   Example 1: Sales-video task appearing 3 times\n"
                "   - Input items:\n"
                "     * 'Sales-video task' on Oct 29 (description: 'get started on Sales-video task, due Nov 4')\n"
                "     * 'Sales-video task' on Nov 4 (description: 'Sales-video task due today at noon')\n"
                "     * 'Sales-video task' on Nov 5 (description: 'should have completed Sales-video by yesterday')\n"
                "   - Analysis:\n"
                "     * Oct 29: Introduction/start date (NOT actual due date)\n"
                "     * Nov 4: Actual due date (KEEP THIS ONE)\n"
                "     * Nov 5: Past-due reminder (NOT actual due date)\n"
                "   - Action: Keep only Nov 4, remove Oct 29 and Nov 5\n"
                "   - Report: Add to inconsistencies: {\"type\": \"duplicate_deadline\", \"details\": \"Removed 2 duplicate mentions of Sales-video task, kept Nov 4 due date\"}\n"
                "   \n"
                "   Example 2: Assignment mentioned twice\n"
                "   - Input items:\n"
                "     * 'Final Paper' on Nov 12 (description: 'start thinking about final paper')\n"
                "     * 'Final Paper' on Dec 15 (description: 'Final Paper due - 10 pages')\n"
                "   - Analysis:\n"
                "     * Nov 12: Reminder to start (NOT due date)\n"
                "     * Dec 15: Actual due date with deliverable details (KEEP THIS ONE)\n"
                "   - Action: Keep only Dec 15, remove Nov 12\n"
                "   - Report: Add to inconsistencies: {\"type\": \"duplicate_deadline\", \"details\": \"Removed 1 early mention of Final Paper, kept Dec 15 due date\"}\n"
                "   \n"
                "   **CRITICAL RULES**:\n"
                "   - For graded items (assignments, exams, projects), each task should appear ONCE with its actual due date\n"
                "   - Always keep the LATEST date when multiple dates exist for same task\n"
                "   - Remove all earlier mentions that say 'get started', 'begin working', 'consider'\n"
                "   - Remove all later mentions that say 'should have completed', 'was due yesterday'\n"
                "   - Report all removed duplicates in inconsistencies array\n"
                "   \n"
                "4. Identify unmatched deadlines: hard_deadlines that do not clearly map to any graded component.\n"
                "5. Perform global sanity checks (e.g., a 40% Final Exam that never appears in the schedule).\n"
                "6. Optionally adjust obvious misclassifications (e.g., 'Final Exam' marked as 'assignment' instead of 'exam').\n\n"
                "CRITICAL CONSTRAINTS:\n"
                "- Do NOT create new deadline items for assessment components that lack specific dates in the schedule.\n"
                "- Do NOT invent dates or create generic deadlines (e.g., 'Class Participation' without a specific date).\n"
                "- Only report missing assessments - do NOT add them to validated_items.\n"
                "- Remove true duplicates from validated_items but preserve all legitimate deadline items.\n"
                "- For duplicate detection, focus on graded items (assignments, exams, projects) - readings can appear multiple times if legitimately scheduled.\n\n"
                "OUTPUT FORMAT:\n"
                "Return a single JSON object:\n"
                "{\n"
                "  \"validated_items\": [ /* final list with duplicates removed */ ],\n"
                "  \"missing_assessments\": [ {\"component_name\": \"...\", \"reason\": \"...\"} ],\n"
                "  \"unmatched_deadlines\": [ {\"title\": \"...\", \"date\": \"...\", \"reason\": \"...\"} ],\n"
                "  \"inconsistencies\": [ \n"
                "    {\"type\": \"duplicate_deadline\", \"details\": \"Removed X duplicate mentions of Y, kept Z date\"},\n"
                "    {\"type\": \"conflicting_type\" | \"grading_mismatch\" | \"other\", \"details\": \"...\"} \n"
                "  ],\n"
                "  \"other_anomalies\": [ {\"type\": \"...\", \"details\": \"...\"} ],\n"
                "  \"summary\": \"Short natural language summary of QA findings including duplicate removal.\"\n"
                "}\n"
            ),
            expected_output=(
                "A single JSON object with 'validated_items', 'missing_assessments', "
                "'unmatched_deadlines', 'inconsistencies', 'other_anomalies', and 'summary'."
            ),
            agent=qa_agent,
        )
        
        qa_crew = Crew(
            agents=[qa_agent],
            tasks=[qa_task],
            verbose=False,
            memory=False,
        )
        
        qa_inputs = {
            "merged_tasks": json.dumps(all_items, indent=2),
            "assessment_components": json.dumps(filtered_assessment_components, indent=2),
            "preliminary_mapping": json.dumps({}, indent=2),
            "non_schedule_text": "",
        }
        
        qa_result = qa_crew.kickoff(inputs=qa_inputs)
        qa_str = qa_result.raw if hasattr(qa_result, 'raw') else str(qa_result)
        
        try:
            qa_data = json.loads(qa_str.strip())
        except:
            qa_data = {"validated_items": all_items}
        
        validated_items = qa_data.get("validated_items", all_items)
        
        # DEBUG: Log Agent 3 output
        print(f"\n🔍 DEBUG Agent 3 - Validated {len(validated_items)} items")
        if validated_items:
            print(f"   Sample from Agent 3: {json.dumps(validated_items[0], indent=2)}")
            print(f"   Agent 3 keys: {list(validated_items[0].keys())}")
        
        # ============================================================================
        # ADVANCED DUPLICATE DETECTION (Phase 4 Task 4.1)
        # Addresses Issues #3, #11: Duplicate tasks across dates
        # ============================================================================
        def parse_date_for_sorting(date_str):
            """
            Parse various date formats for sorting. Return datetime or fallback.
            Supports: 'Oct 22', 'October 22', '10/22/2024', '10/22', '2024-10-22'
            """
            if not date_str:
                return datetime.min
            
            try:
                # Try common formats
                for fmt in ["%b %d", "%B %d", "%m/%d/%Y", "%m/%d", "%Y-%m-%d"]:
                    try:
                        dt = datetime.strptime(date_str.strip(), fmt)
                        # If no year provided (e.g., "Oct 22"), use current year
                        if dt.year == 1900:
                            dt = dt.replace(year=datetime.now().year)
                        return dt
                    except:
                        continue
                # Fallback: try to extract numbers for basic sorting
                import re
                nums = re.findall(r'\d+', date_str)
                if nums:
                    return datetime(2024, int(nums[0]), int(nums[1]) if len(nums) > 1 else 1)
                return datetime.min
            except:
                return datetime.min
        
        def deduplicate_by_title_keep_latest(items):
            """
            For graded items with same title, keep only the one with latest date.
            This removes duplicate mentions like 'get started on X' (early) vs 'X due today' (actual).
            """
            # Group by (type, normalized_title) for graded items only
            groups = {}
            non_graded = []
            
            for item in items:
                item_type = item.get("type", "")
                if item_type in ["assignment", "exam", "project", "assessment"]:
                    # Normalize title for grouping (lowercase, strip whitespace)
                    title = (item.get("title") or "").strip().lower()
                    key = (item_type, title)
                    if key not in groups:
                        groups[key] = []
                    groups[key].append(item)
                else:
                    # Keep non-graded items (readings, etc.) unchanged
                    non_graded.append(item)
            
            # For each group, keep item with latest date
            deduplicated = []
            duplicate_count = 0
            
            for key, group_items in groups.items():
                if len(group_items) > 1:
                    # Parse dates and find latest
                    items_with_dates = []
                    for item in group_items:
                        date_str = item.get("date", "")
                        parsed_date = parse_date_for_sorting(date_str)
                        items_with_dates.append((parsed_date, date_str, item))
                        # DEBUG: Log parsing for "watch strategy videos" duplicates
                        if "strategy video" in (item.get("title") or "").lower() or \
                           ("watch" in (item.get("title") or "").lower() and "video" in (item.get("title") or "").lower()):
                            print(f"   🔍 Parsing duplicate: '{item.get('title')}' date='{date_str}' → parsed={parsed_date}")
                    
                    # Sort by parsed date (latest first)
                    items_with_dates.sort(reverse=True, key=lambda x: x[0])
                    latest_item = items_with_dates[0][2]
                    latest_date = items_with_dates[0][1]
                    
                    deduplicated.append(latest_item)
                    duplicate_count += len(group_items) - 1
                    
                    # Log duplicate removal
                    removed_dates = [x[1] for x in items_with_dates[1:]]
                    print(f"   🔧 Deduplicated '{latest_item.get('title')}': kept {latest_date}, removed {len(removed_dates)} earlier mentions ({', '.join(removed_dates)})")
                else:
                    # Only one item with this title, keep it
                    deduplicated.append(group_items[0])
            
            # Add back non-graded items
            deduplicated.extend(non_graded)
            
            if duplicate_count > 0:
                print(f"\n🔍 DEBUG Advanced Duplicate Detection - Removed {duplicate_count} duplicate tasks across dates")
            
            return deduplicated
        
        # Apply advanced duplicate detection
        validated_items = deduplicate_by_title_keep_latest(validated_items)
        
        # Step 5: Second deduplication pass after Agent 3 (in case QA created duplicates)
        deduplicated_items = []
        seen_after_qa = set()
        for item in validated_items:
            key = (item.get("date"), item.get("type"), item.get("title"))
            if key in seen_after_qa:
                continue
            seen_after_qa.add(key)
            deduplicated_items.append(item)
        
        print(f"\n🔍 DEBUG Post-QA Deduplication - {len(deduplicated_items)} unique items (removed {len(validated_items) - len(deduplicated_items)} duplicates)")
        validated_items = deduplicated_items
        
        # Step 6: Agent 4 - Workload Estimation
        workload_task = Task(
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
        
        workload_crew = Crew(
            agents=[workload_estimation_agent],
            tasks=[workload_task],
            verbose=False,
            memory=False,
        )
        
        workload_inputs = {
            "validated_items": json.dumps(validated_items, indent=2),
            "assessment_components": json.dumps(assessment_components or [], indent=2),
            "full_text": text[:3000],
        }
        
        # DEBUG: Log Agent 4 input
        print(f"\n🔍 DEBUG Agent 4 Input - {len(validated_items)} items to estimate")
        if validated_items:
            print(f"   Input keys: {list(validated_items[0].keys())}")
        
        workload_result = workload_crew.kickoff(inputs=workload_inputs)
        workload_str = workload_result.raw if hasattr(workload_result, 'raw') else str(workload_result)
        
        # DEBUG: Log Agent 4 raw output
        print(f"\n🔍 DEBUG Agent 4 Raw Output (first 500 chars): {workload_str[:500]}")
        
        try:
            # PHASE 5 TASK 5.2: Strip markdown code fences if present
            # Agent 4 sometimes wraps JSON in ```json ... ``` which breaks parsing
            clean_str = workload_str.strip()
            
            # Remove opening code fence (```json or ```)
            if clean_str.startswith('```'):
                # Find end of first line (the opening fence)
                first_newline = clean_str.find('\n')
                if first_newline != -1:
                    clean_str = clean_str[first_newline + 1:]
            
            # Remove closing code fence (```)
            if clean_str.endswith('```'):
                clean_str = clean_str[:-3].rstrip()
            
            items_with_workload = json.loads(clean_str)
            if not isinstance(items_with_workload, list):
                print(f"   ⚠️ WARNING: Agent 4 returned non-list type: {type(items_with_workload)}")
                items_with_workload = validated_items
        except Exception as e:
            print(f"   ⚠️ WARNING: Agent 4 JSON parsing failed: {str(e)}")
            print(f"   Attempted to parse: {workload_str[:200]}...")
            items_with_workload = validated_items
        
        # DEBUG: Log Agent 4 output and validate workload fields were added
        print(f"\n🔍 DEBUG Agent 4 Output - {len(items_with_workload)} items")
        if items_with_workload:
            print(f"   Sample from Agent 4: {json.dumps(items_with_workload[0], indent=2)}")
            print(f"   Agent 4 keys: {list(items_with_workload[0].keys())}")
            
            # Validate that workload fields were actually added
            sample_item = items_with_workload[0]
            has_estimated_hours = "estimated_hours" in sample_item
            has_workload_breakdown = "workload_breakdown" in sample_item
            has_confidence = "confidence" in sample_item
            has_notes = "notes" in sample_item
            
            print(f"   ✓ Workload fields present: estimated_hours={has_estimated_hours}, "
                  f"workload_breakdown={has_workload_breakdown}, confidence={has_confidence}, notes={has_notes}")
            
            if not (has_estimated_hours or has_workload_breakdown):
                print(f"   ⚠️ CRITICAL: Agent 4 did NOT add workload fields! Falling back to defaults.")
        
        # Ensure all items have valid estimated_hours (handle None values)
        for item in items_with_workload:
            hours = item.get("estimated_hours")
            if hours is None or not isinstance(hours, (int, float)):
                item["estimated_hours"] = 5  # Default to 5 hours
            elif isinstance(hours, float):
                item["estimated_hours"] = int(hours)  # Convert float to int
        
        # Calculate total hours
        total_hours = sum(item.get("estimated_hours") or 0 for item in items_with_workload)
        
        return {
            "success": True,
            "items_with_workload": items_with_workload,
            "qa_report": qa_data,
            "total_estimated_hours": total_hours,
            "items_count": len(items_with_workload),
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "items_with_workload": [],
        }


def extract_deadlines_and_tasks(file_content: bytes, filename: str) -> Dict:
    """
    Main entry point for the API to extract deadlines with workload estimates.
    
    Args:
        file_content: Raw file bytes
        filename: Original filename
    
    Returns:
        Dict with extracted items and metadata
    """
    try:
        # Parse document
        file_extension = "." + filename.split(".")[-1].lower()
        
        if file_extension == ".pdf":
            text = parse_pdf(file_content)
        else:
            text = parse_text_document(file_content, file_extension)
        
        if not text or len(text) < 100:
            return {
                "success": False,
                "error": "Document appears to be empty or too short",
                "items_with_workload": [],
            }
        
        # Try to extract assessment components first (optional)
        try:
            from app.utils.test_assessment_parser import extract_assessment_components
            assessment_components = extract_assessment_components(text)
        except:
            assessment_components = None
        
        # Run CrewAI extraction
        result = extract_with_crew_ai(text, assessment_components)
        
        return result
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Extraction failed: {str(e)}",
            "items_with_workload": [],
        }
