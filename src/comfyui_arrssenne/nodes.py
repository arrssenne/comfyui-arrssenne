"""Nodes for comfyui-Arrssenne.

Node origins are documented per-class in their docstring. Adapted nodes keep
a reference to their source pack so updates upstream can be tracked.
"""

import logging

from comfy_execution.graph import ExecutionBlocker

logger = logging.getLogger("ComfyUI-Arrssenne")


class AnyType(str):
    """A type that is always equal in comparisons, used to allow a slot to
    accept/output any ComfyUI type.

    Source: pythongosssss, via ComfyUI-Crystools (crystian) core/types.py.
    """

    def __eq__(self, _) -> bool:
        return True

    def __ne__(self, _) -> bool:
        return False


any_type = AnyType("*")


class SwitchFromAny:
    """Routes a single "any"-typed input to one of two outputs based on a
    boolean: on_true if True, on_false if False.

    The unselected output returns an ExecutionBlocker instead of None, so
    downstream nodes on that branch (especially bare output nodes like
    SaveImage/PreviewImage, which crash on None) are simply not executed
    instead of erroring out the whole queue.

    Adapted from CSwitchFromAny in ComfyUI-Crystools (crystian),
    https://github.com/crystian/comfyui-crystools, nodes/switch.py.
    License: MIT.
    """

    CATEGORY = "Arrssenne/Switch"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "any": (any_type,),
                "boolean": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = (any_type, any_type)
    RETURN_NAMES = ("on_true", "on_false")
    FUNCTION = "execute"

    def execute(self, any, boolean=True):
        logger.debug("Switch from any: %s", boolean)
        blocked = ExecutionBlocker(None)
        if boolean:
            return any, blocked
        return blocked, any


class SwitchFromAny3:
    """Routes a single "any"-typed input to one of three outputs based on an
    integer selector (1, 2 or 3).

    The two unselected outputs return an ExecutionBlocker instead of None,
    so downstream nodes on those branches (especially bare output nodes
    like SaveImage/PreviewImage, which crash on None) are simply not
    executed instead of erroring out the whole queue.

    Outputs are named "1" / "2" / "3" by default. Rename them directly on
    the canvas (clic droit sur la sortie -> Rename) for the workflow at hand
    (ex.: Detailler / Faceswap / Saveas) -- ce renommage est purement visuel
    cote UI ComfyUI, il ne change pas la logique : c'est toujours l'index
    1-3 de "select" qui decide quelle sortie recoit la valeur.

    Adapted from CSwitchFromAny in ComfyUI-Crystools (crystian),
    https://github.com/crystian/comfyui-crystools, nodes/switch.py,
    extended from 2 (true/false) to 3 outputs. License: MIT.
    """

    CATEGORY = "Arrssenne/Switch"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "any": (any_type,),
                "select": ("INT", {"default": 1, "min": 1, "max": 3, "step": 1}),
            }
        }

    RETURN_TYPES = (any_type, any_type, any_type)
    RETURN_NAMES = ("1", "2", "3")
    FUNCTION = "execute"

    def execute(self, any, select=1):
        index = min(max(int(select), 1), 3) - 1
        blocked = ExecutionBlocker(None)
        outputs = [blocked, blocked, blocked]
        outputs[index] = any
        logger.debug("Switch from any (3-way): select=%s", select)
        return tuple(outputs)


NODE_CLASS_MAPPINGS = {
    "ArrssenneSwitchFromAny": SwitchFromAny,
    "ArrssenneSwitchFromAny3": SwitchFromAny3,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ArrssenneSwitchFromAny": "Switch from any (Arrssenne)",
    "ArrssenneSwitchFromAny3": "Switch from any 3-way (Arrssenne)",
}
