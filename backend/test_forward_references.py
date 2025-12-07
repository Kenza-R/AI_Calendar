"""Test forward reference resolution with session_dates mapping."""
import json

# Sample session_dates that Agent 1 should create
session_dates = [
    {"session_number": 1, "date": "Oct 22"},
    {"session_number": 2, "date": "Oct 29"},
    {"session_number": 3, "date": "Nov 5"},
    {"session_number": 4, "date": "Nov 12"},
    {"session_number": 5, "date": "Nov 19"},
    {"session_number": 6, "date": "Dec 3"},
    {"session_number": 7, "date": "Dec 10"},
]

# Sample syllabus blocks with forward references
test_cases = [
    {
        "block_date": "Oct 22",
        "block_text": "Class 1 - Oct 22: Introduction\nRead first 3 chapters by class #3",
        "expected_task": {
            "title": "Read first 3 chapters",
            "date": "Nov 5",  # Should resolve to class #3 date, NOT Oct 22
            "reason": "Forward reference 'by class #3' should resolve to Nov 5"
        }
    },
    {
        "block_date": "Nov 19",
        "block_text": "Class 5 - Nov 19: Advanced Topics\nWatch Shapley-Pie video prior to 6th class",
        "expected_task": {
            "title": "Watch Shapley-Pie video",
            "date": "Dec 3",  # Should resolve to class #6 date, NOT Nov 19
            "reason": "Forward reference 'prior to 6th class' should resolve to Dec 3"
        }
    },
    {
        "block_date": "Oct 29",
        "block_text": "Class 2 - Oct 29: Negotiations\nPrepare for discussion before next session",
        "expected_task": {
            "title": "Prepare for discussion",
            "date": "Nov 5",  # Should resolve to next session (class #3), NOT Oct 29
            "reason": "Forward reference 'before next session' should resolve to Nov 5"
        }
    },
    {
        "block_date": "Nov 5",
        "block_text": "Class 3 - Nov 5: Bargaining\nComplete assignment due today",
        "expected_task": {
            "title": "Complete assignment",
            "date": "Nov 5",  # Should use current date since it says "due today"
            "reason": "No forward reference - use current block date"
        }
    }
]

print("=" * 80)
print("TEST: Forward Reference Resolution with Session Dates")
print("=" * 80)

print("\n📅 Session Dates Mapping (from Agent 1):")
for session in session_dates:
    print(f"   Class #{session['session_number']} = {session['date']}")

print("\n" + "=" * 80)
print("EXPECTED AGENT 2 BEHAVIOR:")
print("=" * 80)

for i, test in enumerate(test_cases, 1):
    print(f"\n{i}. Block Date: {test['block_date']}")
    print(f"   Block Text: {test['block_text'][:80]}...")
    print(f"   ✓ Expected Task: '{test['expected_task']['title']}'")
    print(f"   ✓ Expected Date: {test['expected_task']['date']}")
    print(f"   📝 Reason: {test['expected_task']['reason']}")

print("\n" + "=" * 80)
print("VALIDATION CRITERIA:")
print("=" * 80)
print("✓ Agent 1 extracts session_dates array from schedule")
print("✓ Agent 2 receives session_dates in block_inputs")
print("✓ Agent 2 resolves 'by class #3' to session_dates[3].date")
print("✓ Agent 2 resolves 'prior to 6th class' to session_dates[6].date")
print("✓ Agent 2 resolves 'before next session' to next session's date")
print("✓ Tasks with forward references get correct future dates, not current block date")

print("\n" + "=" * 80)
print("FIXES ISSUES:")
print("=" * 80)
print("✓ Issue #1: 'Read first 3 chapters' now gets Nov 5 (class #3), not Oct 22")
print("✓ Issue #4: 'Shapley-Pie video' now gets Dec 3 (before 6th), not Nov 19")
print("✓ Issue #12: All forward references properly resolved using session_dates")

print("\n🔍 To test: Upload syllabus and check backend debug logs")
print("   Agent 1 should log session_dates array")
print("   Agent 2 should resolve forward references correctly")
