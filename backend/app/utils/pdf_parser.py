import PyPDF2
import docx
from typing import Optional
import io


def parse_pdf(file_content: bytes) -> str:
    """Parse PDF file and extract text content."""
    try:
        pdf_file = io.BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        return text.strip()
    except Exception as e:
        raise ValueError(f"Error parsing PDF: {str(e)}")


def parse_text_document(file_content: bytes, file_extension: str) -> str:
    """Parse text documents (txt, docx) and extract content."""
    try:
        if file_extension == ".txt":
            return file_content.decode("utf-8")
        
        elif file_extension == ".docx":
            doc_file = io.BytesIO(file_content)
            doc = docx.Document(doc_file)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text.strip()
        
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    
    except Exception as e:
        raise ValueError(f"Error parsing document: {str(e)}")
