import os
from main import process_piece_directory

def test_single_piece():
    """Test documentation generation for a single piece"""
    test_dir = "comm/contentful"  # Using contentful as it has a complex action
    docs = process_piece_directory(test_dir)
    
    # Write test output to a file
    with open("test_documentation.md", "w", encoding="utf-8") as f:
        f.write("\n\n".join(docs))

if __name__ == "__main__":
    test_single_piece()
