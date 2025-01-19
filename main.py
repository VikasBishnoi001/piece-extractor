import os
import sys
from typing import Dict, List
from piece_parser import PieceParser
from models import Piece, Action, Trigger
from utils import find_files_by_extension

def generate_documentation(piece: Piece) -> str:
    """Generate documentation for a piece and its actions."""
    doc = []

    # Piece header
    doc.append(f"# {piece.display_name}")
    doc.append(f"\n{piece.description}")
    doc.append(f"\nMinimum Supported Release: {piece.minimum_supported_release}")
    if piece.authors:
        doc.append(f"Authors: {', '.join(piece.authors)}")

    # Actions documentation
    if piece.actions:
        doc.append("\n## Available Actions\n")

        for action in piece.actions:
            doc.append(f"### {action.display_name}")
            doc.append(f"{action.description}\n")
            doc.append("#### Parameters:")

            if not action.properties:
                doc.append("No parameters required.")
            else:
                for prop in action.properties:
                    required = "(Required)" if prop.required else "(Optional)"
                    doc.append(f"- **{prop.display_name}** {required}")
                    doc.append(f"  - Type: {prop.property_type}")
                    doc.append(f"  - Description: {prop.description}\n")

    # Triggers documentation
    if piece.triggers:
        doc.append("\n## Available Triggers\n")

        for trigger in piece.triggers:
            doc.append(f"### {trigger.display_name}")
            doc.append(f"{trigger.description}\n")
            doc.append("#### Parameters:")

            if not trigger.properties:
                doc.append("No parameters required.")
            else:
                for prop in trigger.properties:
                    required = "(Required)" if prop.required else "(Optional)"
                    doc.append(f"- **{prop.display_name}** {required}")
                    doc.append(f"  - Type: {prop.property_type}")
                    doc.append(f"  - Description: {prop.description}\n")

    if not piece.actions and not piece.triggers:
        doc.append("\nNo actions or triggers available for this piece.")

    return "\n".join(doc)

def process_piece_directory(directory: str) -> List[str]:
    """Process a piece directory and generate documentation."""
    parser = PieceParser()
    docs = []

    # Find index.ts files
    index_files = find_files_by_extension(directory, "index.ts")

    for index_file in index_files:
        if "src" not in index_file:
            continue

        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse piece
            piece = parser.parse_piece(content)
            if not piece:
                print(f"Warning: Could not parse piece from {index_file}")
                continue

            base_dir = os.path.dirname(index_file)

            # Find and parse actions
            action_dir = os.path.join(base_dir, "lib", "actions")
            if os.path.exists(action_dir):
                action_files = find_files_by_extension(action_dir, ".ts")

                for action_file in action_files:
                    try:
                        with open(action_file, 'r', encoding='utf-8') as f:
                            action_content = f.read()
                        action = parser.parse_action(action_content)
                        if action:
                            piece.actions.append(action)
                    except Exception as e:
                        print(f"Warning: Error parsing action file {action_file}: {str(e)}")

            # Find and parse triggers
            trigger_dir = os.path.join(base_dir, "lib", "triggers")
            if os.path.exists(trigger_dir):
                trigger_files = find_files_by_extension(trigger_dir, ".ts")

                for trigger_file in trigger_files:
                    try:
                        with open(trigger_file, 'r', encoding='utf-8') as f:
                            trigger_content = f.read()
                        trigger = parser.parse_trigger(trigger_content)
                        if trigger:
                            piece.triggers.append(trigger)
                    except Exception as e:
                        print(f"Warning: Error parsing trigger file {trigger_file}: {str(e)}")

            # Generate documentation
            docs.append(generate_documentation(piece))

        except Exception as e:
            print(f"Error processing {index_file}: {str(e)}")

    return docs

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <pieces_directory>")
        sys.exit(1)

    pieces_dir = sys.argv[1]
    if not os.path.exists(pieces_dir):
        print(f"Directory not found: {pieces_dir}")
        sys.exit(1)

    # Process all pieces and generate documentation
    all_docs = process_piece_directory(pieces_dir)

    if not all_docs:
        print("No pieces were found or could be processed.")
        sys.exit(1)

    # Write documentation to file
    output_file = "pieces_documentation.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n\n".join(all_docs))

    print(f"Documentation generated successfully: {output_file}")

if __name__ == "__main__":
    main()