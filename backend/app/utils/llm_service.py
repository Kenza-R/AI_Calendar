from openai import OpenAI
from typing import List, Dict, Optional
import json
from datetime import datetime
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
        prompt = f"""
        Analyze the following {context} and extract all deadlines, assignments, exams, 
        interviews, and important dates. For each item, provide:
        - title: The name/title of the item
        - date: The date (in ISO format YYYY-MM-DD if possible, or the date as stated)
        - type: The type (exam, assignment, interview, deadline, reading, etc.)
        - description: A brief description
        - estimated_hours: Estimated hours needed for preparation (integer)
        
        Return the results as a JSON array.
        
        Text:
        {text[:3000]}  # Limit to first 3000 chars to avoid token limits
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert at extracting deadline information from academic and professional documents."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        
        result = response.choices[0].message.content
        # Try to parse as JSON
        try:
            deadlines = json.loads(result)
            return deadlines if isinstance(deadlines, list) else []
        except json.JSONDecodeError:
            return []
    
    except Exception as e:
        print(f"Error extracting deadlines: {str(e)}")
        return _generate_sample_deadlines(text)


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
    # Simple keyword-based extraction as fallback
    keywords = ["exam", "assignment", "due", "deadline", "interview", "quiz", "test"]
    lines = text.lower().split('\n')
    
    deadlines = []
    for line in lines[:10]:  # Check first 10 lines
        if any(keyword in line for keyword in keywords):
            deadlines.append({
                "title": line[:50],
                "date": datetime.now().isoformat(),
                "type": "deadline",
                "description": line[:100],
                "estimated_hours": 5
            })
    
    return deadlines if deadlines else [{
        "title": "Sample Deadline",
        "date": datetime.now().isoformat(),
        "type": "assignment",
        "description": "Please configure OpenAI API key for accurate extraction",
        "estimated_hours": 3
    }]


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
