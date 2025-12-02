#!/usr/bin/env python3
"""
Enhanced PDF Upload Handler - API-ready file management
"""
import shutil
from pathlib import Path
from typing import Optional, BinaryIO
from datetime import datetime

def save_uploaded_file(
    file_content: bytes,
    filename: str,
    uploads_dir: Optional[Path] = None
) -> dict:
    """
    Save an uploaded file to the uploads directory.
    API-ready version that takes file content and returns status.
    
    Args:
        file_content: Binary content of the file
        filename: Original filename
        uploads_dir: Optional custom uploads directory
        
    Returns:
        dict with status, file_path, and message
    """
    try:
        # Use provided uploads_dir or default
        if uploads_dir is None:
            uploads_dir = Path(__file__).parent.parent.parent / "uploads"
        
        uploads_dir.mkdir(exist_ok=True)
        
        # Create unique filename with timestamp to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_stem = Path(filename).stem
        file_ext = Path(filename).suffix
        unique_filename = f"{file_stem}_{timestamp}{file_ext}"
        
        dest_path = uploads_dir / unique_filename
        
        # Write file content
        with open(dest_path, 'wb') as f:
            f.write(file_content)
        
        return {
            "status": "success",
            "file_path": str(dest_path),
            "filename": unique_filename,
            "original_filename": filename,
            "message": f"Successfully saved {filename}"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error saving file: {str(e)}"
        }


def get_latest_pdf(uploads_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Get the most recently uploaded PDF file.
    
    Args:
        uploads_dir: Optional custom uploads directory
        
    Returns:
        Path to the latest PDF file or None
    """
    if uploads_dir is None:
        uploads_dir = Path(__file__).parent.parent.parent / "uploads"
    
    if not uploads_dir.exists():
        return None
    
    pdf_files = sorted(
        uploads_dir.glob("*.pdf"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    return pdf_files[0] if pdf_files else None


if __name__ == "__main__":
    # Test functionality
    print("Enhanced PDF Upload Handler - API Ready")
    print("This module is now integrated with the backend API.")
    print("Use the save_uploaded_file() function in your API endpoints.")
