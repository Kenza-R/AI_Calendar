"""Test weight enrichment from assessment components."""
import json

# Sample assessment components that would be passed to Agent 2
assessment_components = [
    {
        "name": "Real World Negotiation",
        "weight": "50 pts",
        "description": "Written analysis of real-world negotiation"
    },
    {
        "name": "Deepak-video task",
        "weight": "10 pts",
        "description": "Video response assignment"
    },
    {
        "name": "Sales-video task",
        "weight": "15 pts",
        "description": "Sales negotiation analysis"
    },
    {
        "name": "Final Exam",
        "weight": "30%",
        "description": "Cumulative final examination"
    }
]

# Sample syllabus blocks
sample_blocks = [
    {
        "date": "Oct 22",
        "text": "Deepak-video task (10 pts): Watch video and write 100-200 word response"
    },
    {
        "date": "Oct 29",
        "text": "Sales-video task (15 pts): 3-4 page analysis of sales negotiation tactics"
    },
    {
        "date": "Dec 15",
        "text": "Real World Negotiation Paper due - 3-4 page write-up with planning document"
    },
    {
        "date": "Dec 17",
        "text": "Final Exam - Comprehensive exam covering all course material"
    }
]

print("=" * 80)
print("TEST: Assessment Component Weight Enrichment")
print("=" * 80)

print("\n📋 Assessment Components Available:")
for comp in assessment_components:
    print(f"  - {comp['name']}: {comp['weight']}")

print("\n" + "=" * 80)
print("EXPECTED AGENT 2 EXTRACTION RESULTS:")
print("=" * 80)

for block in sample_blocks:
    print(f"\n📅 {block['date']} - {block['text'][:50]}...")
    
    # Find matching component
    matching_comp = None
    for comp in assessment_components:
        if comp['name'].lower() in block['text'].lower():
            matching_comp = comp
            break
    
    if matching_comp:
        print(f"   ✓ Matches component: {matching_comp['name']} ({matching_comp['weight']})")
        print(f"   ✓ Description should start with: [Weight: {matching_comp['weight']}]")
        
        # Construct expected description
        desc_parts = []
        if "100-200 word" in block['text']:
            desc_parts.append("100-200 word response")
        if "3-4 page" in block['text']:
            desc_parts.append("3-4 page write-up")
        if "analysis" in block['text']:
            desc_parts.append("analysis of sales negotiation tactics")
        if "planning document" in block['text']:
            desc_parts.append("with planning document")
        if "Comprehensive exam" in block['text']:
            desc_parts.append("Comprehensive exam covering all course material")
        
        expected_desc = f"[Weight: {matching_comp['weight']}] " + (", ".join(desc_parts) if desc_parts else block['text'])
        print(f"   📝 Expected description: {expected_desc}")
    else:
        print(f"   ⚠️  No matching assessment component found")

print("\n" + "=" * 80)
print("VALIDATION CRITERIA:")
print("=" * 80)
print("✓ Weight prefixes are properly formatted: [Weight: X pts] or [Weight: X%]")
print("✓ Weights are extracted from assessment_components, not just from text")
print("✓ Weight appears at START of description")
print("✓ assessment_name field is populated for linking")
print("✓ All other details (page counts, word counts) are preserved")

print("\n🔍 To test: Upload the actual syllabus and check backend debug logs")
print("   Agent 2 output should show descriptions starting with [Weight: ...] tags")
