from dataclasses import dataclass
from typing import List, Dict, Optional, Any

@dataclass
class Property:
    name: str
    display_name: str
    description: str
    required: bool
    property_type: str
    input_ui_info: Optional[Dict] = None  # Store UI-specific information
    default_value: Optional[Any] = None   # Store default values if specified
    validation_rules: Optional[Dict] = None  # Store any validation rules

@dataclass
class Action:
    name: str
    display_name: str
    description: str
    properties: List[Property]
    piece_name: Optional[str] = None  # The name of the piece this action belongs to
    piece_version: Optional[str] = None  # Version information
    settings_template: Optional[Dict] = None  # Example settings from flows

@dataclass
class Trigger:
    name: str
    display_name: str
    description: str
    properties: List[Property]
    piece_name: Optional[str] = None
    piece_version: Optional[str] = None
    settings_template: Optional[Dict] = None

@dataclass
class Piece:
    name: str
    display_name: str
    description: str
    minimum_supported_release: str
    logo_url: str
    actions: List[Action]
    triggers: List[Trigger]
    authors: List[str]
    categories: List[str] = None
    auth_type: Optional[str] = None  # Store authentication type information