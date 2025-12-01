#!/usr/bin/env python3
"""
Simple PDF File Picker - Select and save PDFs
"""
import subprocess
import shutil
from pathlib import Path

def select_and_save_pdf():
    """Open native file picker and save selected PDF."""
    # Use osascript (AppleScript) to open file picker on macOS
    script = """
    set theFile to (choose file of type {"com.adobe.pdf"})
    return POSIX path of theFile
    """
    
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            file_path = result.stdout.strip()
            if file_path:
                # Save to uploads folder (relative to backend directory)
                uploads_dir = Path(__file__).parent.parent.parent / "uploads"
                uploads_dir.mkdir(exist_ok=True)
                
                # Copy file
                filename = Path(file_path).name
                dest_path = uploads_dir / filename
                shutil.copy(file_path, dest_path)
                
                print(f"✓ Saved: {dest_path}")
        else:
            print("Cancelled")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    select_and_save_pdf()
