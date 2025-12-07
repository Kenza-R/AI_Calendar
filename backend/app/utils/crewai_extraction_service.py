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
        
        if not schedule_blocks:
            return {"success": False, "error": "No schedule blocks found", "items_with_workload": []}
        
        # Step 3: Agent 2 - Extraction (process each block)
        extraction_task = Task(
            description=(
                "You are the Schedule Interpretation / Task Extraction Agent.\n\n"
                "INPUTS YOU RECEIVE:\n"
                "- One schedule block: {block_text}\n"
                "- Date string for this block: {date_string}\n"
                "- Graded assessment components: {assessment_components}\n\n"
                "YOUR GOAL FOR THIS SINGLE BLOCK:\n"
                "1. Read the block and identify:\n"
                "   - Class session information (topic, title, week label, etc.).\n"
                "   - Preparatory readings or 'read before class' items.\n"
                "   - Mandatory or optional readings explicitly identified as readings.\n"
                "   - Hard deadlines: anything clearly due, to be submitted, exam dates, quizzes, tests, projects, etc.\n"
                "2. Date extraction rules:\n"
                "   - FIRST PRIORITY: Look for explicit calendar dates (e.g., 'March 15', '3/15/2024', 'Oct 22').\n"
                "   - SECOND PRIORITY: If only relative dates exist (e.g., 'Week 1', 'Session 2'), use the date_string provided for this block.\n"
                "   - PRESERVE exact date format from the syllabus - do NOT convert or reformat dates.\n"
                "   - Do NOT invent dates that don't appear in the text.\n"
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
        
        extraction_crew = Crew(
            agents=[extraction_agent],
            tasks=[extraction_task],
            verbose=False,
            memory=False,
        )
        
        all_items = []
        for block in schedule_blocks:  # Process all blocks
            block_inputs = {
                "block_text": block.get("raw_block", ""),
                "date_string": block.get("date_string", ""),
                "assessment_components": json.dumps(assessment_components or [], indent=2),
            }
            
            ext_result = extraction_crew.kickoff(inputs=block_inputs)
            ext_str = ext_result.raw if hasattr(ext_result, 'raw') else str(ext_result)
            
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
        
        # Flatten nested structure: extract hard_deadlines from schedule blocks
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
                    })
            elif item.get("kind") == "class_session":
                # Extract readings and prep tasks as individual items
                date_str = item.get("date_string", "")
                session_title = item.get("session_title", "")
                
                # Add hard deadlines within class session
                for deadline in item.get("hard_deadlines", []):
                    flattened_items.append({
                        "date": date_str,
                        "title": deadline.get("title", ""),
                        "type": deadline.get("type", "assignment"),
                        "description": deadline.get("description", ""),
                        "assessment_name": deadline.get("assessment_name", ""),
                    })
        
        print(f"\n🔍 DEBUG Flattening - {len(flattened_items)} individual deadlines extracted")
        if flattened_items:
            print(f"   Sample flattened item: {json.dumps(flattened_items[0], indent=2)}")
        
        all_items = flattened_items
        
        if not all_items:
            return {"success": False, "error": "No deadlines found after flattening", "items_with_workload": []}
        
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
        
        qa_crew = Crew(
            agents=[qa_agent],
            tasks=[qa_task],
            verbose=False,
            memory=False,
        )
        
        qa_inputs = {
            "merged_tasks": json.dumps(all_items, indent=2),
            "assessment_components": json.dumps(assessment_components or [], indent=2),
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
        
        # Step 5: Agent 4 - Workload Estimation
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
        
        workload_result = workload_crew.kickoff(inputs=workload_inputs)
        workload_str = workload_result.raw if hasattr(workload_result, 'raw') else str(workload_result)
        
        try:
            items_with_workload = json.loads(workload_str.strip())
            if not isinstance(items_with_workload, list):
                items_with_workload = validated_items
        except:
            items_with_workload = validated_items
        
        # DEBUG: Log Agent 4 output
        print(f"\n🔍 DEBUG Agent 4 - Items with workload: {len(items_with_workload)}")
        if items_with_workload:
            print(f"   Sample from Agent 4: {json.dumps(items_with_workload[0], indent=2)}")
            print(f"   Agent 4 keys: {list(items_with_workload[0].keys())}")
        
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
