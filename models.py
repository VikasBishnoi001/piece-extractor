from dataclasses import dataclass
from typing import List, Dict, Optional, Any

@dataclass
class Property:
    name: str
    display_name: str
    description: str
    required: bool
    property_type: str

@dataclass
class Action:
    name: str
    display_name: str
    description: str
    properties: List[Property]

@dataclass
class Trigger:
    name: str
    display_name: str
    description: str
    properties: List[Property]

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