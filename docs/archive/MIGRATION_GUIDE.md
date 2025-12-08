# Quick Reference: Old vs New Extraction Services

## Function Migration Map

### For Document/Syllabus Extraction

**OLD WAY:**
```python
from app.utils.llm_service import extract_deadlines_from_text
from app.utils.test_assessment_parser_copy import extract_assessment_components_api
from app.utils.test_deadline_extraction_copy import extract_deadlines_and_sessions_api

# Old simple extraction
deadlines = extract_deadlines_from_text(text_content, context="syllabus")

# Old assessment extraction
result = extract_assessment_components_api(text_content)

# Old deadline extraction with sessions
result = extract_deadlines_and_sessions_api(text_content, assessments)
```

**NEW WAY:**
```python
from app.utils.crewai_extraction_service import extract_deadlines_and_tasks

# New CrewAI extraction (handles everything)
result = extract_deadlines_and_tasks(file_content, filename)

# Returns comprehensive result:
{
    "success": True,
    "items_with_workload": [
        {
            "title": "Assignment 1",
            "date": "2024-01-20",
            "type": "assignment",
            "description": "Complete homework",
            "estimated_hours": 5,
            "workload_breakdown": "2h reading, 3h coding"
        }
    ],
    "total_estimated_hours": 50,
    "qa_report": {...}
}
```

## Key Differences

### Input Format
- **OLD:** Required text string (`str`)
- **NEW:** Requires bytes (`bytes`) - use `text.encode('utf-8')` or pass file content directly

### Output Format
- **OLD:** Simple list of dictionaries
  ```python
  [{"title": "...", "date": "...", "type": "..."}]
  ```
- **NEW:** Rich dictionary with workload estimates
  ```python
  {"success": bool, "items_with_workload": [...], "total_estimated_hours": int, ...}
  ```

### Features
| Feature | Old Services | CrewAI Service |
|---------|--------------|----------------|
| Date extraction | ✅ Basic | ✅ Advanced |
| Task extraction | ✅ Basic | ✅ Advanced |
| Assessment parsing | ✅ Separate function | ✅ Integrated |
| Workload estimation | ❌ No | ✅ Yes |
| QA validation | ❌ No | ✅ Yes |
| Multi-agent pipeline | ❌ No | ✅ 4 agents |
| Structured breakdown | ❌ No | ✅ Yes |

## Code Examples

### Example 1: Upload Endpoint
```python
# OLD
text_content = parse_pdf(file_content)
deadlines = extract_deadlines_from_text(text_content)

# NEW
result = extract_deadlines_and_tasks(file_content, filename)
if result.get("success"):
    items = result.get("items_with_workload", [])
```

### Example 2: Email Processing
```python
# OLD
email_text = f"Subject: {subject}\n\n{body}"
extracted = extract_deadlines_from_text(email_text, context="email")

# NEW
email_text = f"Subject: {subject}\n\n{body}"
result = extract_deadlines_and_tasks(email_text.encode('utf-8'), f"email_{message_id}.txt")
if result.get("success"):
    items = result.get("items_with_workload", [])
```

### Example 3: Accessing Results
```python
result = extract_deadlines_and_tasks(file_content, filename)

# Check success
if not result.get("success"):
    error = result.get("error", "Unknown error")
    # Handle error
    
# Get all items (excluding class sessions if needed)
items = result.get("items_with_workload", [])
for item in items:
    if item.get("type") != "class_session":
        title = item.get("title")
        date = item.get("date")
        hours = item.get("estimated_hours")
        breakdown = item.get("workload_breakdown")
        
# Get total workload estimate
total_hours = result.get("total_estimated_hours", 0)

# Get QA report
qa_report = result.get("qa_report", {})
summary = qa_report.get("summary", "")
```

## Migration Checklist

- [x] Replace `extract_deadlines_from_text` imports with `extract_deadlines_and_tasks`
- [x] Update function calls to use new format
- [x] Handle bytes input (use `.encode('utf-8')` for strings)
- [x] Update response handling to check `success` field
- [x] Extract items from `items_with_workload` key
- [x] Filter out `class_session` type if needed
- [x] Use `estimated_hours` and `workload_breakdown` fields
- [ ] Update frontend to display workload information
- [ ] Test all endpoints thoroughly
- [ ] Update API documentation

## Notes

1. The CrewAI service is more robust but requires:
   - Python 3.10+
   - `crewai` package installed
   - OpenAI API key set in environment

2. If CrewAI is not available, it gracefully falls back to keyword-based extraction

3. The old services are still in the codebase but no longer used

4. `generate_prep_material()` from `llm_service.py` is still used for flashcards/quizzes
