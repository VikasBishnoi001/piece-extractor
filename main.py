import os
import sys
from typing import Dict, List
import json
from piece_parser import PieceParser
from models import Piece, Action, Trigger
from utils import find_files_by_extension

def extract_flow_examples(flow_json_path: str) -> Dict:
    """Extract examples of piece usage from a flow JSON file."""
    try:
        with open(flow_json_path, 'r', encoding='utf-8') as f:
            flow_data = json.load(f)

        examples = {}
        if 'template' in flow_data and 'trigger' in flow_data['template']:
            current = flow_data['template']['trigger']
            while current and 'nextAction' in current:
                current = current['nextAction']
                if current.get('type') == 'PIECE':
                    piece_name = current['settings']['pieceName']
                    action_name = current['settings']['actionName']
                    key = f"{piece_name}:{action_name}"
                    examples[key] = {
                        'input': current['settings'].get('input', {}),
                        'pieceVersion': current['settings'].get('pieceVersion'),
                        'settings': current['settings']
                    }

        return examples
    except Exception as e:
        print(f"Warning: Could not parse flow example file: {str(e)}")
        return {}

def generate_property_docs(prop) -> List[str]:
    """Generate documentation for a property with enhanced details."""
    doc = []
    requirement = "**Required**" if prop.required else "Optional"
    doc.append(f"- **{prop.display_name}** ({requirement})")
    doc.append(f"  - Type: `{prop.property_type}`")
    if prop.description:
        doc.append(f"  - Description: {prop.description}")
    if prop.default_value is not None:
        doc.append(f"  - Default Value: `{prop.default_value}`")
    if prop.validation_rules:
        doc.append("  - Validation Rules:")
        for rule, value in prop.validation_rules.items():
            doc.append(f"    - {rule}: {value}")
    doc.append("")
    return doc

def generate_usage_example(component, flow_examples: Dict) -> List[str]:
    """Generate usage example documentation for an action or trigger."""
    doc = []

    # Check if we have a matching example from the flow
    if component.piece_name and component.name:
        example_key = f"{component.piece_name}:{component.name}"
        if example_key in flow_examples:
            example = flow_examples[example_key]
            doc.append("#### Usage Example")
            doc.append("```json")
            doc.append("settings: {")

            # Show input parameters
            if example['input']:
                doc.append("  input: {")
                for key, value in example['input'].items():
                    doc.append(f"    {key}: {value},")
                doc.append("  },")

            # Show other relevant settings
            if example['pieceVersion']:
                doc.append(f"  pieceVersion: \"{example['pieceVersion']}\",")

            doc.append("}")
            doc.append("```")
            doc.append("")

    return doc

def generate_documentation(piece: Piece, flow_examples: Dict) -> str:
    """Generate documentation for a piece and its actions."""
    doc = []

    # Piece header with divider
    doc.append(f"# {piece.display_name}")
    if piece.description:
        doc.append(f"\n{piece.description}")
    doc.append(f"\nMinimum Supported Release: {piece.minimum_supported_release}")
    if piece.authors:
        doc.append(f"Authors: {', '.join(piece.authors)}")
    if piece.categories:
        doc.append(f"Categories: {', '.join(piece.categories)}")
    if piece.auth_type:
        doc.append(f"\nAuthentication: {piece.auth_type}")
    doc.append("\n---\n")

    # Actions documentation
    if piece.actions:
        doc.append("## Actions\n")
        for action in piece.actions:
            doc.append(f"### {action.display_name}")
            if action.description:
                doc.append(f"\n{action.description}\n")

            if action.piece_version:
                doc.append(f"Version: {action.piece_version}\n")

            if action.properties:
                doc.append("#### Parameters\n")
                for prop in action.properties:
                    doc.extend(generate_property_docs(prop))
            else:
                doc.append("This action has no configurable parameters.\n")

            # Add usage example from flow if available
            doc.extend(generate_usage_example(action, flow_examples))
            doc.append("---\n")

    # Triggers documentation
    if piece.triggers:
        doc.append("## Triggers\n")
        for trigger in piece.triggers:
            doc.append(f"### {trigger.display_name}")
            if trigger.description:
                doc.append(f"\n{trigger.description}\n")

            if trigger.piece_version:
                doc.append(f"Version: {trigger.piece_version}\n")

            if trigger.properties:
                doc.append("#### Parameters\n")
                for prop in trigger.properties:
                    doc.extend(generate_property_docs(prop))
            else:
                doc.append("This trigger has no configurable parameters.\n")

            # Add usage example from flow if available
            doc.extend(generate_usage_example(trigger, flow_examples))
            doc.append("---\n")

    if not piece.actions and not piece.triggers:
        doc.append("\nThis piece has no actions or triggers available.")

    # Add final newline
    doc.append("\n")
    return "\n".join(doc)

def process_piece_directory(directory: str, flow_example_path: str = None) -> List[str]:
    """Process a piece directory and generate documentation."""
    parser = PieceParser()
    docs = []

    # Load flow examples if provided
    flow_examples = {}
    if flow_example_path and os.path.exists(flow_example_path):
        flow_examples = extract_flow_examples(flow_example_path)

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
                            # Set piece-specific information
                            action.piece_name = piece.name
                            piece.actions.append(action)
                    except Exception as e:
                        print(f"Warning: Error parsing action file {action_file}: {str(e)}")

            # Find and parse triggers (check both triggers and trigger directories)
            for trigger_dirname in ["triggers", "trigger"]:
                trigger_dir = os.path.join(base_dir, "lib", trigger_dirname)
                if os.path.exists(trigger_dir):
                    trigger_files = find_files_by_extension(trigger_dir, ".ts")

                    for trigger_file in trigger_files:
                        try:
                            with open(trigger_file, 'r', encoding='utf-8') as f:
                                trigger_content = f.read()
                            trigger = parser.parse_trigger(trigger_content)
                            if trigger:
                                # Set piece-specific information
                                trigger.piece_name = piece.name
                                piece.triggers.append(trigger)
                        except Exception as e:
                            print(f"Warning: Error parsing trigger file {trigger_file}: {str(e)}")

            # Generate documentation with flow examples
            docs.append(generate_documentation(piece, flow_examples))

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

    # Use the provided example flow JSON if it exists
    example_flow_path = "attached_assets/Pasted--created-1728657602018-updated-1728657602018-name-Interview-Question-Generato-1737319364276.txt"

    # Process all pieces and generate documentation
    all_docs = process_piece_directory(pieces_dir, example_flow_path)

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