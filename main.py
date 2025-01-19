import os
import sys
from typing import Dict, List, Optional
import json
from piece_parser import PieceParser
from models import Piece, Action, Trigger

def generate_property_docs(prop) -> List[str]:
    """Generate minimal property documentation focused on flow creation."""
    doc = []
    doc.append(f"- **{prop.name}**: `{prop.property_type}`")
    if prop.description:
        doc.append(f"  {prop.description}")
    doc.append("")
    return doc

def generate_component_settings_docs(component) -> List[str]:
    """Generate minimal settings documentation for flow creation."""
    doc = []
    doc.append("```json")
    doc.append("{")
    doc.append('  "type": "PIECE",')
    doc.append('  "settings": {')
    doc.append(f'    "pieceName": "{component.piece_name}",')
    doc.append(f'    "actionName": "{component.name}",')
    doc.append('    "input": {')
    if component.properties:
        for prop in component.properties:
            doc.append(f'      "{prop.name}": "{{previousStep.output_field}}"')
    doc.append('    }')
    doc.append('  },')
    doc.append('  "nextAction": {')
    doc.append('    "type": "PIECE",')
    doc.append('    "settings": {')
    doc.append('      "pieceName": "piece_name",')
    doc.append('      "actionName": "action_name",')
    doc.append('      "input": {')
    doc.append('        "param": "{{currentStep.output}}"')
    doc.append('      }')
    doc.append('    }')
    doc.append('  }')
    doc.append('}')
    doc.append('```')
    doc.append("")
    return doc

def generate_trigger_config_docs(trigger) -> List[str]:
    """Generate minimal trigger documentation for flow creation."""
    doc = []
    doc.append("```json")
    doc.append("{")
    doc.append('  "trigger": {')
    doc.append(f'    "type": "{trigger.trigger_type}",')
    doc.append('    "settings": {')
    if trigger.properties:
        for prop in trigger.properties:
            doc.append(f'      "{prop.name}": null')
    doc.append('    },')
    doc.append('    "nextAction": {')
    doc.append('      "type": "PIECE",')
    doc.append('      "settings": {')
    doc.append('        "pieceName": "piece_name",')
    doc.append('        "actionName": "action_name",')
    doc.append('        "input": {')
    doc.append('          "param": "{{trigger.body}}"')
    doc.append('        }')
    doc.append('      }')
    doc.append('    }')
    doc.append('  }')
    doc.append('}')
    doc.append('```')
    doc.append("")
    doc.append("Trigger outputs available in next steps:")
    doc.append("- `{{trigger.body}}` - Request body")
    doc.append("- `{{trigger.headers}}` - Request headers") 
    doc.append("- `{{trigger.query}}` - Query parameters")
    doc.append("")
    return doc

def generate_documentation(piece: Piece, flow_examples: Dict) -> str:
    """Generate minimal documentation focused on flow creation."""
    doc = []

    # Piece name and description only
    doc.append(f"# {piece.display_name}")
    if piece.description:
        doc.append(f"\n{piece.description}\n")

    # Actions with minimal info needed for flow creation
    if piece.actions:
        doc.append("## Actions")
        for action in piece.actions:
            doc.append(f"\n### {action.display_name}")
            if action.description:
                doc.append(f"\n{action.description}\n")

            if action.properties:
                doc.append("#### Input Parameters")
                for prop in action.properties:
                    doc.extend(generate_property_docs(prop))

            doc.extend(generate_component_settings_docs(action))
            doc.append("---\n")

    # Triggers with minimal info needed for flow creation  
    if piece.triggers:
        doc.append("## Triggers")
        for trigger in piece.triggers:
            doc.append(f"\n### {trigger.display_name}")
            if trigger.description:
                doc.append(f"\n{trigger.description}\n")

            if trigger.properties:
                doc.append("#### Input Parameters")
                for prop in trigger.properties:
                    doc.extend(generate_property_docs(prop))

            doc.extend(generate_trigger_config_docs(trigger))
            doc.append("---\n")

    if not piece.actions and not piece.triggers:
        doc.append("\nThis piece has no actions or triggers available.\n")

    doc.append("\n")
    return "\n".join(doc)

def process_piece_directory(directory: str, flow_examples: Optional[Dict] = None) -> List[str]:
    """Process a piece directory and generate documentation."""
    parser = PieceParser()
    docs = []
    flow_examples = flow_examples or {}

    # Find index.ts files
    index_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file == "index.ts":
                index_files.append(os.path.join(root, file))

    for index_file in index_files:
        if "src" not in index_file:
            continue

        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()

            piece = parser.parse_piece(content)
            if not piece:
                continue

            base_dir = os.path.dirname(index_file)

            # Parse actions
            action_dir = os.path.join(base_dir, "lib", "actions")
            if os.path.exists(action_dir):
                for root, _, files in os.walk(action_dir):
                    for file in files:
                        if file.endswith(".ts"):
                            try:
                                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                                    action_content = f.read()
                                action = parser.parse_action(action_content)
                                if action:
                                    action.piece_name = piece.name
                                    piece.actions.append(action)
                            except Exception as e:
                                print(f"Warning: Error parsing action file {file}: {str(e)}")

            # Parse triggers
            for trigger_dirname in ["triggers", "trigger"]:
                trigger_dir = os.path.join(base_dir, "lib", trigger_dirname)
                if os.path.exists(trigger_dir):
                    for root, _, files in os.walk(trigger_dir):
                        for file in files:
                            if file.endswith(".ts"):
                                try:
                                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                                        trigger_content = f.read()
                                    trigger = parser.parse_trigger(trigger_content)
                                    if trigger:
                                        trigger.piece_name = piece.name
                                        piece.triggers.append(trigger)
                                except Exception as e:
                                    print(f"Warning: Error parsing trigger file {file}: {str(e)}")

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

    # Generate documentation
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