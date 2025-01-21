import os
import sys
from typing import Dict, List, Optional
import json
from piece_parser import PieceParser
from models import Piece, Action, Trigger

def generate_property_docs(prop) -> List[str]:
    """Generate minimal property documentation focused on flow creation."""
    doc = []
    doc.append(f"- **{prop.name}** (`{prop.property_type}`)")
    if prop.description:
        doc.append(f"  {prop.description}")

    # Add validation rules if they exist
    if prop.validation_rules:
        if 'options' in prop.validation_rules:
            doc.append("  **Options:**")
            doc.append("  | Label | Value |")
            doc.append("  |-------|-------|")
            options = prop.validation_rules['options'].strip()
            if options:
                for option in options.split('\n'):
                    if ':' in option:
                        label, value = option.split(':', 1)
                        doc.append(f"  | {label.strip()} | {value.strip()} |")

        if 'minimum' in prop.validation_rules:
            doc.append(f"  **Minimum:** {prop.validation_rules['minimum']}")
        if 'maximum' in prop.validation_rules:
            doc.append(f"  **Maximum:** {prop.validation_rules['maximum']}")

    # Add default value if it exists
    if prop.default_value is not None:
        doc.append(f"  **Default:** `{prop.default_value}`")

    if prop.required:
        doc.append("  **Required:** Yes")

    doc.append("")
    return doc

def generate_component_settings_docs(component) -> List[str]:
    """Generate minimal settings documentation for flow creation."""
    doc = []
    doc.append("```json")
    doc.append("{")
    doc.append('  "settings": {')
    doc.append(f'    "pieceName": "{component.piece_name}",')
    doc.append('    "pieceVersion": "0.0.1",')
    doc.append(f'    "actionName": "{component.name}",')
    doc.append('    "input": {')
    if component.properties:
        props_list = []
        for prop in component.properties:
            # Use default value if available, otherwise use a template value
            value = prop.default_value if prop.default_value is not None else "{{previousStep.output}}"
            # For properties with predefined options, use first option as example
            if prop.validation_rules and 'options' in prop.validation_rules:
                options = prop.validation_rules['options'].strip().split('\n')
                if options:
                    first_option = options[0].split(':', 1)[1].strip()
                    value = first_option
            props_list.append(f'      "{prop.name}": {json.dumps(value)}')
        doc.append(",\n".join(props_list))
    doc.append('    },')
    doc.append('    "inputUiInfo": {},')
    doc.append('    "packageType": "REGISTRY"')
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
    doc.append('    "valid": true,')
    doc.append(f'    "type": "{trigger.trigger_type}",')
    doc.append('    "settings": {')
    if trigger.properties:
        props_list = []
        for prop in trigger.properties:
            value = prop.default_value if prop.default_value is not None else None
            # For properties with predefined options, use first option as example
            if prop.validation_rules and 'options' in prop.validation_rules:
                options = prop.validation_rules['options'].strip().split('\n')
                if options:
                    first_option = options[0].split(':', 1)[1].strip()
                    value = first_option
            props_list.append(f'      "{prop.name}": {json.dumps(value)}')
        doc.append(",\n".join(props_list))
    doc.append('    }')
    doc.append('  }')
    doc.append('}')
    doc.append('```')
    doc.append("")
    doc.append("**Step Outputs:**")
    doc.append("- `{{trigger.body}}` - The complete request body")
    doc.append("- `{{trigger.headers}}` - HTTP request headers")
    doc.append("- `{{trigger.query}}` - URL query parameters")
    doc.append("")
    return doc

def generate_documentation(piece: Piece, flow_examples: Dict) -> str:
    """Generate minimal documentation focused on flow creation."""
    doc = []

    # Piece name and description
    doc.append(f"# {piece.display_name}")
    if piece.description:
        doc.append(f"\n{piece.description}\n")

    # Document actions with minimal info needed for flow creation
    if piece.actions:
        doc.append("## Actions\n")
        for action in piece.actions:
            doc.append(f"### {action.display_name}")
            if action.description:
                doc.append(f"\n{action.description}\n")

            if action.properties:
                doc.append("#### Input Parameters")
                for prop in action.properties:
                    doc.extend(generate_property_docs(prop))

                doc.append("#### Flow Configuration")
                doc.extend(generate_component_settings_docs(action))

            doc.append("---\n")

    # Document triggers with minimal info needed for flow creation
    if piece.triggers:
        doc.append("## Triggers\n")
        for trigger in piece.triggers:
            doc.append(f"### {trigger.display_name}")
            if trigger.description:
                doc.append(f"\n{trigger.description}\n")

            if trigger.properties:
                doc.append("#### Input Parameters")
                for prop in trigger.properties:
                    doc.extend(generate_property_docs(prop))

                doc.append("#### Flow Configuration")
                doc.extend(generate_trigger_config_docs(trigger))

            doc.append("---\n")

    if not piece.actions and not piece.triggers:
        doc.append("\nNo actions or triggers available.\n")

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

            if piece.actions or piece.triggers:
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