"""
Phase 5 Task 5.1: Diagnose Agent 4 Workload Field Loss
Addresses Issues #5, #13 (Workload estimates show correctly initially, then become 5h)

This diagnostic script tests the full data pipeline to identify where workload fields get lost:
1. Agent 4 output (CrewAI extraction service)
2. Database insertion (documents.py)
3. Database retrieval (tasks.py)
4. API response schema (TaskResponse)

Run this to determine whether the issue is:
- Agent 4 not producing workload fields (LLM instruction issue)
- Data pipeline losing fields during insertion/retrieval
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from app.utils.crewai_extraction_service import extract_with_crew_ai
from app.models.task import Task
from app.schemas.task import TaskResponse
import json

def test_agent4_workload_output():
    """Test if Agent 4 produces workload fields in its output."""
    
    print("="*70)
    print("PHASE 5 TASK 5.1: AGENT 4 WORKLOAD FIELD DIAGNOSIS")
    print("="*70)
    print()
    
    print("📋 Test Scenario: Simple syllabus with 2 tasks")
    print()
    
    # Sample syllabus with clear workload requirements
    test_syllabus = """
    Course Schedule
    
    Oct 22 - Class 1: Introduction
    Read Chapter 1 (20 pages) before class
    
    Nov 4 - Sales-video task due
    Watch 3 videos (total 45 minutes) and complete survey (15 minutes)
    Worth 10 points
    
    Dec 15 - Final Paper due
    Research and write 10-page paper on negotiation strategies
    Worth 50 points
    """
    
    # Assessment components for context
    assessment_components = [
        {"name": "Sales-video task", "weight": "10 pts"},
        {"name": "Final Paper", "weight": "50 pts"}
    ]
    
    print("🔍 STEP 1: Running CrewAI extraction (4-agent pipeline)")
    print("-" * 70)
    
    result = extract_with_crew_ai(
        text=test_syllabus,
        assessment_components=assessment_components
    )
    
    if not result.get("success"):
        print(f"❌ Extraction failed: {result.get('error')}")
        return
    
    items = result.get("items_with_workload", [])
    
    print(f"\n✅ Extraction completed: {len(items)} items extracted")
    print()
    
    print("🔍 STEP 2: Checking Agent 4 Output for Workload Fields")
    print("-" * 70)
    print()
    
    # Check each item for workload fields
    workload_field_stats = {
        "items_with_estimated_hours": 0,
        "items_with_workload_breakdown": 0,
        "items_with_confidence": 0,
        "items_with_notes": 0,
        "items_without_any_workload_fields": 0
    }
    
    for i, item in enumerate(items, 1):
        print(f"\n📦 Item {i}: {item.get('title', 'Unknown')}")
        print(f"   Date: {item.get('date', 'N/A')}")
        print(f"   Type: {item.get('type', 'N/A')}")
        
        has_estimated_hours = "estimated_hours" in item and item["estimated_hours"] is not None
        has_workload_breakdown = "workload_breakdown" in item and item["workload_breakdown"]
        has_confidence = "confidence" in item and item["confidence"]
        has_notes = "notes" in item and item["notes"]
        
        print(f"\n   Workload Fields Present:")
        print(f"   ✓ estimated_hours: {item.get('estimated_hours', 'MISSING')}")
        print(f"   ✓ workload_breakdown: {'Present' if has_workload_breakdown else 'MISSING'}")
        print(f"   ✓ confidence: {'Present' if has_confidence else 'MISSING'}")
        print(f"   ✓ notes: {'Present' if has_notes else 'MISSING'}")
        
        if has_estimated_hours:
            workload_field_stats["items_with_estimated_hours"] += 1
        if has_workload_breakdown:
            workload_field_stats["items_with_workload_breakdown"] += 1
            print(f"      → {item['workload_breakdown']}")
        if has_confidence:
            workload_field_stats["items_with_confidence"] += 1
        if has_notes:
            workload_field_stats["items_with_notes"] += 1
        
        if not any([has_estimated_hours, has_workload_breakdown, has_confidence, has_notes]):
            workload_field_stats["items_without_any_workload_fields"] += 1
    
    print()
    print("="*70)
    print("📊 DIAGNOSIS RESULTS")
    print("="*70)
    print()
    
    total_items = len(items)
    
    print(f"Total items extracted: {total_items}")
    print()
    print(f"Workload Field Coverage:")
    print(f"  • estimated_hours:      {workload_field_stats['items_with_estimated_hours']}/{total_items} items")
    print(f"  • workload_breakdown:   {workload_field_stats['items_with_workload_breakdown']}/{total_items} items")
    print(f"  • confidence:           {workload_field_stats['items_with_confidence']}/{total_items} items")
    print(f"  • notes:                {workload_field_stats['items_with_notes']}/{total_items} items")
    print()
    
    # Determine diagnosis
    if workload_field_stats["items_without_any_workload_fields"] == total_items:
        print("🚨 ISSUE IDENTIFIED: Agent 4 Output Problem")
        print("   Agent 4 is NOT producing any workload fields in its output.")
        print("   This is an LLM instruction issue - Agent 4 not following instructions.")
        print()
        print("   ➡️  NEXT STEP: Proceed to Task 5.3 (Strengthen Agent 4 Instructions)")
        print()
        return "agent4_output_problem"
    
    elif workload_field_stats["items_with_estimated_hours"] >= total_items * 0.8:
        print("✅ ISSUE IDENTIFIED: Data Pipeline Problem")
        print("   Agent 4 IS producing workload fields (≥80% coverage).")
        print("   Fields are being lost somewhere in the data pipeline:")
        print("   - Database insertion in documents.py")
        print("   - Database retrieval in tasks.py")
        print("   - API schema in TaskResponse")
        print()
        print("   ➡️  NEXT STEP: Proceed to Task 5.2 (Fix Data Pipeline)")
        print()
        return "data_pipeline_problem"
    
    else:
        print("⚠️  ISSUE IDENTIFIED: Partial Agent 4 Output")
        print(f"   Agent 4 producing workload fields for {workload_field_stats['items_with_estimated_hours']}/{total_items} items.")
        print("   This is inconsistent behavior - Agent 4 sometimes following instructions.")
        print()
        print("   ➡️  NEXT STEP: Proceed to Task 5.3 (Strengthen Agent 4 Instructions)")
        print()
        return "partial_agent4_problem"
    
    print()
    print("="*70)
    print()
    
    # Additional debugging info
    print("🔍 ADDITIONAL DEBUGGING INFO")
    print("-" * 70)
    print()
    print("Agent 4 Output Sample (first item):")
    if items:
        print(json.dumps(items[0], indent=2))
    print()
    
    print("Database Schema Check:")
    print("  Task model includes: estimated_hours (Integer)")
    print("  TaskResponse schema includes: estimated_hours (Optional[int])")
    print("  ⚠️  Note: workload_breakdown, confidence, notes NOT in database schema")
    print("     These fields exist only in Agent 4 output, not persisted to database!")
    print()


if __name__ == "__main__":
    test_agent4_workload_output()
