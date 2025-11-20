#!/usr/bin/env python3
"""
Test script for syllabus analysis using improved LLM service
"""
import sys
sys.path.insert(0, '/Users/kmr/Documents/GitHub/AI_Calendar/backend')

from app.utils.llm_service import extract_deadlines_from_text
import json

# Sample syllabus text (similar to what would be extracted from a PDF)
sample_syllabus = """
COMPUTER SCIENCE 101: INTRODUCTION TO PROGRAMMING
Spring 2024 Syllabus

Course Description:
This course introduces programming concepts and practices using Python. Students will learn fundamental programming
principles including variables, control structures, functions, and data structures.

Course Schedule and Assignments:

Week 1-2: Introduction to Python
- Assignment 1: Hello World and Variables - Due January 20, 2024

Week 3-4: Control Structures
- Assignment 2: If-Else Statements - Due February 3, 2024
- Quiz 1: Basic Syntax - February 5, 2024

Week 5-6: Functions and Loops
- Assignment 3: Functions and Loops - Due February 17, 2024
- Midterm Exam - February 24, 2024

Week 7-8: Data Structures
- Assignment 4: Lists and Dictionaries - Due March 9, 2024
- Quiz 2: Data Structures - March 11, 2024

Week 9-10: File I/O and Exception Handling
- Assignment 5: File Processing - Due March 23, 2024
- Assignment 6: Exception Handling - Due April 6, 2024

Week 11-12: Final Project
- Project Proposal - Due April 13, 2024
- Final Project Submission - Due April 27, 2024
- Final Exam - May 4, 2024

Grading:
- Assignments (6): 40%
- Quizzes (2): 20%
- Midterm Exam: 15%
- Final Project: 15%
- Final Exam: 10%

Late Work Policy:
All assignments must be submitted by 11:59 PM on the due date. Late submissions will receive a 10% penalty per day late.

Office Hours:
Monday and Wednesday: 2:00 PM - 4:00 PM
Thursday: 10:00 AM - 12:00 PM
"""

print("Testing syllabus analysis with improved extraction...\n")
print("=" * 60)

# Extract deadlines
deadlines = extract_deadlines_from_text(sample_syllabus, context="syllabus")

print(f"\nFound {len(deadlines)} deadlines:\n")
print(json.dumps(deadlines, indent=2))

# Verify we found the expected deadlines
expected_assignments = [
    "Assignment 1",
    "Assignment 2",
    "Quiz 1",
    "Assignment 3",
    "Midterm",
    "Assignment 4",
    "Quiz 2",
    "Assignment 5",
    "Assignment 6",
    "Final Project",
    "Final Exam"
]

found_items = []
for deadline in deadlines:
    title_lower = deadline.get('title', '').lower()
    for expected in expected_assignments:
        if expected.lower() in title_lower:
            found_items.append(expected)
            break

print("\n" + "=" * 60)
print(f"\nExpected items: {len(expected_assignments)}")
print(f"Found items: {len(found_items)}")
print(f"Match rate: {len(found_items) / len(expected_assignments) * 100:.1f}%")

if len(found_items) > 0:
    print(f"\n✅ Successfully extracted: {', '.join(set(found_items))}")
else:
    print("\n⚠️  No assignments found - falling back to keyword extraction")
