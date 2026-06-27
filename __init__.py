"""Top-level package for comfyui-Arrssenne."""

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
]

__author__ = "arrssenne"
__email__ = "duneimf@gmail.com"
__version__ = "0.0.1"

from .src.comfyui_arrssenne.nodes import NODE_CLASS_MAPPINGS
from .src.comfyui_arrssenne.nodes import NODE_DISPLAY_NAME_MAPPINGS

# Pas de JS custom pour l'instant -> pas de WEB_DIRECTORY.
# Si on ajoute un jour du JS (web/js/...), le redeclarer ici.
