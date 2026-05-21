#!/usr/bin/env python3
import sys
from docx import Document


def extract_text_from_docx(file_path):
    try:
        doc = Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                full_text.append(text)
        return "\n".join(full_text)
    except Exception as exc:
        print(f"Error reading Word document: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 extract_docx_text.py <path-to-docx-file>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    print(extract_text_from_docx(path))
