from openai import OpenAI
from typing import List, Dict, Optional
import json
from datetime import datetime
import re
from app.config import settings

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None


def extract_deadlines_from_text(text: str, context: str = "syllabus") -> List[Dict]:
    """
    Use LLM to extract deadlines, assignments, and important dates from text.
    Returns a list of dictionaries with title, date, type, and description.
    """
    if not client:
        # Return sample data if OpenAI is not configured
        return _generate_sample_deadlines(text)
    
    try:
        prompt = f"""You are an expert at extracting deadline and assignment information from academic syllabi and documents.

Analyze the following {context} text and extract EVERY single deadline, assignment, exam, quiz, presentation, paper, project, and important date mentioned.

CRITICAL: First identify the YEAR and SEMESTER from the syllabus:
- Look for "Spring 2024", "Fall 2023", "2023-2024", etc.
- Look at the course start/end dates to determine the year
- If semester is Spring (Jan-May), use that year
- If semester is Fall (Aug-Dec), check if dates are in second half of year
- When you see dates like "January 15" or "March 10" WITHOUT a year, use the identified year from the syllabus

For EACH deadline/assignment found, return valid JSON in exactly this format:
[
  {{
    "title": "Exact assignment/exam name from syllabus",
    "date": "YYYY-MM-DD format using the correct year from syllabus context",
    "type": "assignment|exam|quiz|presentation|paper|deadline|reading|project|interview",
    "description": "What student needs to do",
    "estimated_hours": number between 1 and 20
  }}
]

CRITICAL REQUIREMENTS:
1. Extract EVERY deadline mentioned - do not skip any
2. Convert all dates to YYYY-MM-DD format using the CORRECT YEAR from the syllabus
3. If you see "Due January 20" in a "Fall 2024" syllabus, the date is 2025-01-20 (Spring semester)
4. If you see "Due September 10" in a "Fall 2024" syllabus, the date is 2024-09-10
5. Include the full descriptive title from the syllabus
6. Return ONLY valid JSON array, nothing else
7. Be exhaustive - extract more items rather than fewer

Syllabus text:
{text[:6000]}"""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert at extracting ALL deadline and assignment information with correct years. Return ONLY valid JSON array, no other text."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Lower temperature for consistency
        )
        
        result = response.choices[0].message.content.strip()
        
        # Try to extract JSON from the response
        deadlines = _parse_json_response(result)
        
        # If we got results, validate and return
        if deadlines and len(deadlines) > 0:
            return deadlines
        
        # Fallback: try keyword extraction if JSON parsing fails
        print(f"JSON parsing failed, falling back to keyword extraction")
        return _extract_deadlines_by_keywords(text)
    
    except Exception as e:
        print(f"Error extracting deadlines with OpenAI: {str(e)}")
        return _extract_deadlines_by_keywords(text)


def _parse_json_response(response: str) -> List[Dict]:
    """Safely parse JSON response from LLM, handling various formats."""
    try:
        # Try direct JSON parse first
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from the response text
    try:
        # Look for JSON array pattern
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
    except (json.JSONDecodeError, AttributeError):
        pass
    
    # Try to extract JSON objects
    try:
        json_match = re.findall(r'\{.*?\}', response, re.DOTALL)
        if json_match:
            items = []
            for match in json_match:
                try:
                    items.append(json.loads(match))
                except json.JSONDecodeError:
                    continue
            if items:
                return items
    except Exception:
        pass
    
    return []


def generate_prep_material(task_title: str, task_type: str, description: str = "") -> Dict:
    """
    Generate preparation material for a task (flashcards, quiz questions, company research, etc.)
    """
    if not client:
        return _generate_sample_prep_material(task_title, task_type)
    
    try:
        if task_type == "interview_prep":
            prompt = f"""
            Generate interview preparation material for: {task_title}
            Description: {description}
            
            Provide:
            1. Company research points (if company name is mentioned)
            2. Common interview questions (5-7 questions)
            3. Key topics to review
            4. Tips for success
            
            Format as JSON with keys: company_research, questions, topics, tips
            """
        elif task_type == "exam_prep":
            prompt = f"""
            Generate exam preparation material for: {task_title}
            Description: {description}
            
            Provide:
            1. 10 flashcards (question and answer pairs)
            2. 5 quiz questions with multiple choice answers
            3. Key concepts to review
            4. Study tips
            
            Format as JSON with keys: flashcards, quiz_questions, key_concepts, study_tips
            """
        else:
            prompt = f"""
            Generate study/preparation material for: {task_title}
            Type: {task_type}
            Description: {description}
            
            Provide helpful preparation material including key points, tips, and resources.
            Format as JSON.
            """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert study coach and career advisor."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )
        
        result = response.choices[0].message.content
        try:
            prep_material = json.loads(result)
            return prep_material
        except json.JSONDecodeError:
            return {"content": result}
    
    except Exception as e:
        print(f"Error generating prep material: {str(e)}")
        return _generate_sample_prep_material(task_title, task_type)


def _generate_sample_deadlines(text: str) -> List[Dict]:
    """Generate sample deadlines when OpenAI is not configured."""
    return _extract_deadlines_by_keywords(text)


def _extract_deadlines_by_keywords(text: str) -> List[Dict]:
    """Extract deadlines using keyword matching as fallback."""
    deadlines = []
    lines = text.split('\n')
    
    # Keywords to look for
    deadline_keywords = {
        'assignment': r'(assignment|homework|work|project|task)',
        'exam': r'(exam|examination|test|midterm|final)',
        'quiz': r'(quiz|quizzes)',
        'presentation': r'(presentation|present)',
        'paper': r'(paper|essay|writing)',
        'reading': r'(reading|read|chapter)',
        'deadline': r'(due|deadline|submit|submission)',
        'interview': r'(interview|phone screen)',
        'project': r'(project|proposal)'
    }
    
    # Date patterns
    date_patterns = [
        r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY
        r'(\d{1,2}-\d{1,2}-\d{4})',  # MM-DD-YYYY
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})',  # Month DD
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})',  # Mon DD
        r'Week\s+(\d{1,2})',  # Week number
    ]
    
    # Extract deadlines from text
    for i, line in enumerate(lines[:50]):  # Check first 50 lines
        line_lower = line.lower()
        
        # Skip empty lines and very short lines
        if len(line.strip()) < 5:
            continue
        
        # Check for deadline keywords
        for task_type, pattern in deadline_keywords.items():
            if re.search(pattern, line_lower):
                # Look for dates in this line or nearby lines
                date_found = None
                description = line.strip()
                
                # Check current line and next 3 lines for dates
                for j in range(i, min(i + 4, len(lines))):
                    for date_pattern in date_patterns:
                        date_match = re.search(date_pattern, lines[j])
                        if date_match:
                            date_found = date_match.group(0)
                            break
                    if date_found:
                        break
                
                if date_found or task_type:
                    deadlines.append({
                        "title": line.strip()[:100],
                        "date": date_found or datetime.now().isoformat(),
                        "type": task_type,
                        "description": description[:200],
                        "estimated_hours": 5
                    })
                    break  # Found a match for this line
    
    # If no deadlines found, return a message
    if not deadlines:
        deadlines = [{
            "title": "Syllabus analyzed",
            "date": datetime.now().isoformat(),
            "type": "deadline",
            "description": "No specific deadlines found. Please add them manually.",
            "estimated_hours": 0
        }]
    
    return deadlines


def _generate_sample_prep_material(task_title: str, task_type: str) -> Dict:
    """Generate sample prep material when OpenAI is not configured."""
    if task_type == "interview_prep":
        return {
            "company_research": ["Research company mission and values", "Review recent news"],
            "questions": [
                "Tell me about yourself",
                "Why do you want to work here?",
                "What are your strengths?",
                "Describe a challenging project",
                "Where do you see yourself in 5 years?"
            ],
            "topics": ["Technical skills", "Soft skills", "Company culture fit"],
            "tips": ["Practice STAR method", "Prepare questions for interviewer", "Dress professionally"]
        }
    else:
        return {
            "flashcards": [
                {"question": "Sample Question 1", "answer": "Sample Answer 1"},
                {"question": "Sample Question 2", "answer": "Sample Answer 2"}
            ],
            "quiz_questions": [
                {
                    "question": "Sample Quiz Question?",
                    "options": ["A", "B", "C", "D"],
                    "correct": "A"
                }
            ],
            "key_concepts": ["Concept 1", "Concept 2", "Concept 3"],
            "study_tips": ["Review notes regularly", "Practice problems", "Form study group"]
        }


if __name__ == "__main__":
    import sys
    import os
    from pathlib import Path
    
    # Add backend directory to path for imports
    backend_dir = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(backend_dir))
    
    from pdf_parser import parse_pdf, parse_text_document
    
    print("=" * 80)
    print("📅 DEADLINE EXTRACTION TEST")
    print("=" * 80)
    print()
    
    # Check if file path is provided
    if len(sys.argv) < 2:
        # If no argument, look for the most recent file in uploads folder
        uploads_dir = Path(__file__).parent.parent.parent / "uploads"
        if uploads_dir.exists():
            pdf_files = sorted(uploads_dir.glob("*.pdf"), key=lambda x: x.stat().st_mtime, reverse=True)
            if pdf_files:
                file_path = pdf_files[0]
                print(f"📄 Using most recent PDF: {file_path.name}\n")
            else:
                print("❌ No PDF files found in uploads folder")
                print("Usage: python llm_service.py <path_to_pdf>")
                sys.exit(1)
        else:
            print("❌ Uploads folder not found")
            print("Usage: python llm_service.py <path_to_pdf>")
            sys.exit(1)
    else:
        file_path = Path(sys.argv[1])
    
    # Check if file exists
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    # Parse the file
    print(f"🔍 Step 1: Parsing PDF...")
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
    print(f"🤖 Step 2: Extracting deadlines using LLM...")
    print(f"OpenAI API Key configured: {'Yes ✅' if client else 'No ❌ (will use keyword extraction)'}\n")
    
    try:
        deadlines = extract_deadlines_from_text(text, context="syllabus")
        
        print("=" * 80)
        print(f"📋 FOUND {len(deadlines)} DEADLINES")
        print("=" * 80)
        print()
        
        for i, deadline in enumerate(deadlines, 1):
            print(f"Deadline #{i}:")
            print(f"  📌 Title: {deadline.get('title', 'N/A')}")
            print(f"  📅 Date: {deadline.get('date', 'N/A')}")
            print(f"  🏷️  Type: {deadline.get('type', 'N/A')}")
            print(f"  📝 Description: {deadline.get('description', 'N/A')[:100]}{'...' if len(deadline.get('description', '')) > 100 else ''}")
            print(f"  ⏱️  Estimated Hours: {deadline.get('estimated_hours', 'N/A')}")
            print()
        
        print("=" * 80)
        print("✅ Deadline extraction complete!")
        print("=" * 80)
        
        # Option to save to JSON
        save_option = input("\n💾 Save results to JSON file? (y/n): ").lower().strip()
        if save_option == 'y':
            output_file = Path(__file__).parent.parent.parent / "uploads" / f"{file_path.stem}_deadlines.json"
            with open(output_file, 'w') as f:
                json.dump(deadlines, f, indent=2)
            print(f"✅ Saved to: {output_file}")
    
    except Exception as e:
        print(f"❌ Error extracting deadlines: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
