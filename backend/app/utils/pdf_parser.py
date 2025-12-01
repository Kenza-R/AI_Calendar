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


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
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
                print("Usage: python pdf_parser.py <path_to_pdf>")
                sys.exit(1)
        else:
            print("❌ Uploads folder not found")
            print("Usage: python pdf_parser.py <path_to_pdf>")
            sys.exit(1)
    else:
        file_path = Path(sys.argv[1])
    
    # Check if file exists
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    # Parse the PDF
    print("=" * 80)
    print(f"📄 PARSING: {file_path.name}")
    print("=" * 80)
    print()
    
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        
        if file_path.suffix.lower() == ".pdf":
            text = parse_pdf(content)
        else:
            text = parse_text_document(content, file_path.suffix.lower())
        
        print(text)
        print()
        print("=" * 80)
        print(f"✅ Successfully parsed {len(text)} characters")
        print("=" * 80)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
