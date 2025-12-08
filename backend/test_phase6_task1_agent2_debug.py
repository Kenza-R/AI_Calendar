"""
PHASE 6 TASK 6.1 DEBUGGING: Agent 2 Forward Reference Resolution
=================================================================

Test Agent 2's ability to resolve "Prior to next (Xth) class" pattern.
"""

import os
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils.crewai_extraction_service import extract_with_crew_ai


def test_agent2_forward_reference():
    """Test Agent 2 on Class 4 block with 'Prior to next (5th) class' pattern."""
    
    print("="*70)
    print("DEBUGGING: Agent 2 Forward Reference Resolution")
    print("="*70)
    print()
    
    # Minimal test case focusing on Class 4 block
    test_syllabus = """
    Course Schedule - Negotiation Strategies
    
    Class 1 (Oct 22) - Introduction
    Topic: Overview

    Class 2 (Oct 29) - Distributive Bargaining
    Topic: Win-lose

    Class 3 (Nov 5) - Integrative Negotiation
    Topic: Win-win

    Class 4 (Nov 12) - Multi-party Negotiations
    Topic: Complex stakeholder management
    Prior to next (5th) class, watch strategy videos
    
    Class 5 (Nov 19) - Real-World Applications
    Topic: Case studies
    Strategy videos discussion
    
    Class 6 (Dec 15) - Final Project Presentations
    Submit final project
    """
    
    print("📋 Test Case:")
    print("   Block: Class 4 (Nov 12)")
    print("   Text: 'Prior to next (5th) class, watch strategy videos'")
    print("   Expected: Task with date='Nov 19' (Class 5's date)")
    print()
    print("   Agent 2 should:")
    print("   1. Recognize 'Prior to next (5th) class' as forward reference")
    print("   2. Extract session number 5 from '(5th) class'")
    print("   3. Look up session 5 in session_dates → Nov 19")
    print("   4. Create task with date='Nov 19' (NOT Nov 12)")
    print()
    
    print("🔍 Running extraction...")
    print("-" * 70)
    
    result = extract_with_crew_ai(
        text=test_syllabus,
        assessment_components=[]
    )
    
    if not result.get("success"):
        print(f"❌ Extraction failed: {result.get('error')}")
        return
    
    items = result.get("items_with_workload", [])
    
    print()
    print("="*70)
    print("📊 RESULTS")
    print("="*70)
    print()
    print(f"Total items extracted: {len(items)}")
    print()
    
    # Find the "watch strategy videos" task
    video_task = None
    for item in items:
        if "strategy video" in item.get("title", "").lower() or \
           "watch" in item.get("title", "").lower() and "video" in item.get("title", "").lower():
            video_task = item
            break
    
    if video_task:
        print("✅ Found 'watch strategy videos' task:")
        print(f"   Title: {video_task.get('title')}")
        print(f"   Date: {video_task.get('date')}")
        print(f"   Type: {video_task.get('type')}")
        print(f"   Description: {video_task.get('description', '')[:100]}")
        print()
        
        if video_task.get('date') == 'Nov 19':
            print("✅ SUCCESS: Task correctly assigned to Nov 19 (Class 5)")
            print("   Agent 2 successfully resolved 'Prior to next (5th) class'")
        elif video_task.get('date') == 'Nov 12':
            print("❌ FAILURE: Task incorrectly assigned to Nov 12 (Class 4)")
            print("   Agent 2 used current block's date instead of resolving forward reference")
            print()
            print("🔍 DIAGNOSIS:")
            print("   Agent 2 is NOT correctly parsing 'Prior to next (5th) class' pattern")
            print("   Possible causes:")
            print("   1. LLM not recognizing '(5th) class' as session number 5")
            print("   2. Agent 2 instructions may need stronger emphasis on this pattern")
            print("   3. session_dates mapping not being used correctly")
        else:
            print(f"⚠️  UNEXPECTED: Task assigned to {video_task.get('date')}")
    else:
        print("❌ ERROR: 'watch strategy videos' task not found in extraction")
        print()
        print("All extracted items:")
        for i, item in enumerate(items, 1):
            print(f"   {i}. {item.get('title')} (Date: {item.get('date')}, Type: {item.get('type')})")
    
    print()
    print("="*70)


if __name__ == "__main__":
    load_dotenv()
    test_agent2_forward_reference()
