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
# CrewAI Agents (only created if CrewAI is available)
# ============================================================================

if CREWAI_AVAILABLE:
    segmentation_agent = Agent(
        llm="gpt-4o-mini",
        role="Syllabus Segmentation Agent",
        goal="Segment a syllabus into clean, date-based schedule blocks and non-schedule blocks.",
        backstory=(
            "You specialize in understanding complex university syllabi and reconstructing "
            "schedule information into coherent blocks, never inventing dates."
        ),
        allow_delegation=False,
        verbose=False,
    )
else:
    segmentation_agent = None

if CREWAI_AVAILABLE:
    extraction_agent = Agent(
        llm="gpt-4o-mini",
        role="Syllabus Task Extraction Agent",
        goal="Extract structured class sessions, readings, and hard deadlines from schedule blocks.",
        backstory=(
            "You are an expert at reading university syllabi and turning unstructured schedule "
            "entries into structured tasks, using assessment context to improve accuracy."
        ),
        allow_delegation=False,
        verbose=False,
    )

    qa_agent = Agent(
        llm="gpt-4o-mini",
        role="Syllabus QA & Consistency Agent",
        goal="Audit extracted items to ensure completeness and consistency with grading components.",
        backstory=(
            "You act as a rigorous auditor, verifying coverage of graded components and detecting "
            "inconsistencies or duplicates without inventing new assessments or dates."
        ),
        allow_delegation=False,
        verbose=False,
    )

    workload_estimation_agent = Agent(
        llm="gpt-4o-mini",
        role="Academic Workload Estimation Agent",
        goal="Estimate realistic time requirements for all tasks and deadlines.",
        backstory=(
            "You are an experienced academic advisor who understands student workloads. You provide "
            "conservative, realistic estimates considering assignment type, complexity, and academic standards."
        ),
        allow_delegation=False,
        verbose=False,
    )
else:
    extraction_agent = qa_agent = workload_estimation_agent = None


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
                "Segment the syllabus into schedule blocks by date. "
                "Inputs: {indexed_lines}, {date_candidates}. "
                "Output: JSON with schedule_blocks and non_schedule_blocks arrays."
            ),
            expected_output="JSON object with schedule_blocks and non_schedule_blocks",
            agent=segmentation_agent,
        )
        
        seg_crew = Crew(
            agents=[segmentation_agent],
            tasks=[segmentation_task],
            verbose=False,
            memory=False,
        )
        
        seg_inputs = {
            "indexed_lines": json.dumps(indexed_lines[:20], indent=2),  # Limit for API
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
                "Extract tasks from a schedule block. "
                "Inputs: {block_text}, {date_string}, {assessment_components}. "
                "Output: JSON array of extracted items."
            ),
            expected_output="JSON array of tasks with dates, types, and descriptions",
            agent=extraction_agent,
        )
        
        extraction_crew = Crew(
            agents=[extraction_agent],
            tasks=[extraction_task],
            verbose=False,
            memory=False,
        )
        
        all_items = []
        for block in schedule_blocks[:10]:  # Limit to first 10 blocks
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
        
        if not all_items:
            return {"success": False, "error": "No items extracted", "items_with_workload": []}
        
        # Step 4: Agent 3 - QA
        qa_task = Task(
            description=(
                "Validate extracted items for completeness and consistency. "
                "Inputs: {merged_tasks}, {assessment_components}. "
                "Output: JSON with validated_items and QA report."
            ),
            expected_output="JSON with validated_items array",
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
        
        # Step 5: Agent 4 - Workload Estimation
        workload_task = Task(
            description=(
                "Estimate realistic time requirements for each task. "
                "Inputs: {validated_items}, {assessment_components}. "
                "Output: JSON array with workload estimates."
            ),
            expected_output="JSON array with estimated_hours for each item",
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
        
        # Calculate total hours
        total_hours = sum(item.get("estimated_hours", 0) for item in items_with_workload)
        
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
