"""Nodes for comfyui-Arrssenne.

Node origins are documented per-class in their docstring. Adapted nodes keep
a reference to their source pack so updates upstream can be tracked.
"""

import colorsys
import logging
import math
import os
import random
import re

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


class CkptSeedFilename:
    """Builds a clean filename string from a checkpoint name and a seed.

    Replaces a 3-node chain (RegexReplace + SomethingToString + JoinStrings)
    used to produce SaveImage filename prefixes like "arrssenne_126090403892970".

    Cleanup applied to checkpoint_name, in order:
    1. strip any folder prefix (both "/" and "\\" separators),
    2. strip the file extension (".safetensors", ".ckpt", ...),
    3. strip an optional trailing "_NNNNN_" counter suffix.

    Then joins the cleaned name and the seed with "_".

    Original node, no third-party source.
    """

    CATEGORY = "Arrssenne/Text"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "checkpoint_name": ("STRING", {"forceInput": True}),
                "seed": ("INT", {"forceInput": True, "default": 0, "min": 0,
                                 "max": 0xFFFFFFFFFFFFFFFF}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filename",)
    FUNCTION = "execute"

    def execute(self, checkpoint_name, seed):
        name = checkpoint_name.replace("\\", "/").split("/")[-1]
        name = re.sub(r"\.[^.]+$", "", name)   # extension
        name = re.sub(r"_\d+_$", "", name)     # suffixe compteur _NNNNN_
        filename = f"{name}_{seed}"
        logger.debug("CkptSeedFilename: %s", filename)
        return (filename,)


LORA_TAG_RE = re.compile(r"<lora:([^:>]+)(?::([^:>]*))?(?::([^:>]*))?>")


def parse_lora_tags(text):
    """Extract <lora:name[:strength_model[:strength_clip]]> tags from text.

    Returns (tags, cleaned_text) where tags is a list of
    (name, strength_model, strength_clip) and cleaned_text is the text with
    all tags removed. Missing strengths default to 1.0 / strength_model.
    Pure function, testable outside ComfyUI.
    """
    tags = []

    def _repl(m):
        name = m.group(1).strip()
        try:
            sm = float(m.group(2)) if m.group(2) else 1.0
        except ValueError:
            sm = 1.0
        try:
            sc = float(m.group(3)) if m.group(3) else sm
        except ValueError:
            sc = sm
        tags.append((name, sm, sc))
        return ""

    cleaned = LORA_TAG_RE.sub(_repl, text)
    return tags, cleaned


def resolve_lora_file(name, lora_files):
    """Match a tag name against the list of installed LoRA files.

    Priority: exact path > path without extension > basename (stem) match.
    Separators \\ and / are treated as equivalent. Returns the matching
    entry from lora_files, or None. Pure function, testable outside ComfyUI.
    """
    norm = name.replace("\\", "/").strip()
    norm_stem = norm.split("/")[-1]
    if "." in norm_stem:
        norm_stem = norm_stem.rsplit(".", 1)[0]

    basename_match = None
    for f in lora_files:
        fn = f.replace("\\", "/")
        if fn == norm:
            return f
        if fn.rsplit(".", 1)[0] == norm:
            return f
        stem = fn.split("/")[-1].rsplit(".", 1)[0]
        if basename_match is None and stem == norm_stem:
            basename_match = f
    return basename_match


class Loader:
    """All-in-one loader: checkpoint (MODEL only) + external CLIP + external
    VAE + LoRA tags parsed from the prompt text (Forge-style), in one node.

    Replaces the 4-node chain CheckpointLoaderWithString + CLIPLoader +
    VAELoader + LoraTagLoader. The checkpoint's embedded CLIP/VAE are never
    loaded (output_vae/output_clip=False), so a Krea2-style checkpoint with
    no usable text encoder cannot cause a "clip input is invalid" error —
    the external CLIP is always the one used.

    Every <lora:name[:strength[:strength_clip]]> tag found in `text` is
    applied to MODEL+CLIP (via the builtin LoraLoader, so caching works) and
    removed from the `text` output. Unresolvable tags are logged and
    skipped, never fatal.

    Outputs: MODEL, CLIP, VAE, text (tags stripped), checkpoint_name (raw,
    for Filename ckpt+seed and Image Saver Metadata).

    Original node. LoRA-tag-in-prompt concept inspired by
    badjeff/comfyui_lora_tag_loader; implementation written from scratch on
    ComfyUI builtin APIs (folder_paths, comfy.sd, nodes.LoraLoader).
    """

    CATEGORY = "Arrssenne/Loaders"

    @classmethod
    def INPUT_TYPES(cls):
        import folder_paths
        from nodes import CLIPLoader as _CLIPLoader, VAELoader as _VAELoader

        try:
            clip_types = list(_CLIPLoader.INPUT_TYPES()["required"]["type"][0])
        except Exception:  # structure changed upstream: degrade gracefully
            clip_types = ["stable_diffusion"]
        try:
            vae_names = list(_VAELoader.INPUT_TYPES()["required"]["vae_name"][0])
        except Exception:
            vae_names = folder_paths.get_filename_list("vae")

        return {
            "required": {
                "ckpt_name": (folder_paths.get_filename_list("checkpoints"),),
                "clip_name": (folder_paths.get_filename_list("text_encoders"),),
                "clip_type": (clip_types,),
                "vae_name": (vae_names,),
                "text": ("STRING", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("MODEL", "CLIP", "VAE", "STRING", "STRING")
    RETURN_NAMES = ("MODEL", "CLIP", "VAE", "text", "checkpoint_name")
    FUNCTION = "execute"

    def execute(self, ckpt_name, clip_name, clip_type, vae_name, text):
        import comfy.sd
        import folder_paths
        from nodes import CLIPLoader, VAELoader, LoraLoader

        ckpt_path = folder_paths.get_full_path_or_raise("checkpoints", ckpt_name)
        model = comfy.sd.load_checkpoint_guess_config(
            ckpt_path,
            output_vae=False,
            output_clip=False,
            embedding_directory=folder_paths.get_folder_paths("embeddings"),
        )[0]

        clip = CLIPLoader().load_clip(clip_name, type=clip_type)[0]
        vae = VAELoader().load_vae(vae_name)[0]

        tags, cleaned = parse_lora_tags(text)
        if tags:
            lora_files = folder_paths.get_filename_list("loras")
            lora_loader = LoraLoader()
            for name, sm, sc in tags:
                lora_file = resolve_lora_file(name, lora_files)
                if lora_file is None:
                    logger.warning("Arrssenne Loader: LoRA introuvable, tag ignore: <lora:%s>", name)
                    continue
                model, clip = lora_loader.load_lora(model, clip, lora_file, sm, sc)
                logger.info("Arrssenne Loader: LoRA applique: %s (model=%s, clip=%s)", lora_file, sm, sc)

        return model, clip, vae, cleaned, ckpt_name


class LoaderCkpt:
    """All-in-one loader for checkpoints that embed their own CLIP and VAE:
    checkpoint + LoRA tags parsed from the prompt text (Forge-style), in
    one node — no clip_name/clip_type/vae_name selection widgets.

    Companion to ArrssenneLoader (which loads an external CLIP/VAE for
    checkpoints like Krea2 that lack a usable embedded text encoder). Use
    this one when the checkpoint is self-contained (SDXL/Illustrious/Pony
    style): the CLIP and VAE outputs come straight from inside the
    checkpoint file (output_vae/output_clip=True).

    Every <lora:name[:strength[:strength_clip]]> tag found in `text` is
    applied to MODEL+CLIP (via the builtin LoraLoader, so caching works)
    and removed from the `text` output. Unresolvable tags are logged and
    skipped, never fatal.

    Outputs: MODEL, CLIP, VAE, text (tags stripped), checkpoint_name (raw,
    for Filename ckpt+seed and Image Saver Metadata) — same signature as
    ArrssenneLoader, so the two are drop-in swappable in a workflow.

    Original node. LoRA-tag-in-prompt concept inspired by
    badjeff/comfyui_lora_tag_loader; implementation written from scratch on
    ComfyUI builtin APIs (folder_paths, comfy.sd, nodes.LoraLoader).
    """

    CATEGORY = "Arrssenne/Loaders"

    @classmethod
    def INPUT_TYPES(cls):
        import folder_paths

        return {
            "required": {
                "ckpt_name": (folder_paths.get_filename_list("checkpoints"),),
                "text": ("STRING", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("MODEL", "CLIP", "VAE", "STRING", "STRING")
    RETURN_NAMES = ("MODEL", "CLIP", "VAE", "text", "checkpoint_name")
    FUNCTION = "execute"

    def execute(self, ckpt_name, text):
        import comfy.sd
        import folder_paths
        from nodes import LoraLoader

        ckpt_path = folder_paths.get_full_path_or_raise("checkpoints", ckpt_name)
        model, clip, vae = comfy.sd.load_checkpoint_guess_config(
            ckpt_path,
            output_vae=True,
            output_clip=True,
            embedding_directory=folder_paths.get_folder_paths("embeddings"),
        )[:3]
        if clip is None:
            raise RuntimeError(
                f"Arrssenne Loader ckpt: le checkpoint '{ckpt_name}' ne contient pas de "
                "CLIP utilisable — utiliser 'Loader ckpt+clip+vae+lora (Arrssenne)' "
                "avec un CLIP externe."
            )

        tags, cleaned = parse_lora_tags(text)
        if tags:
            lora_files = folder_paths.get_filename_list("loras")
            lora_loader = LoraLoader()
            for name, sm, sc in tags:
                lora_file = resolve_lora_file(name, lora_files)
                if lora_file is None:
                    logger.warning("Arrssenne Loader ckpt: LoRA introuvable, tag ignore: <lora:%s>", name)
                    continue
                model, clip = lora_loader.load_lora(model, clip, lora_file, sm, sc)
                logger.info("Arrssenne Loader ckpt: LoRA applique: %s (model=%s, clip=%s)", lora_file, sm, sc)

        return model, clip, vae, cleaned, ckpt_name


def face_image_stem(image):
    """Extract the bare name (no folder, no extension, no ComfyUI
    " [input]"/" [output]"/" [temp]" annotation) from a LoadImage widget
    value. Pure function, testable outside ComfyUI.
    """
    name = image.strip()
    if name.endswith("]") and " [" in name:
        name = name[: name.rindex(" [")]
    name = name.replace("\\", "/").split("/")[-1]
    if "." in name:
        name = name.rsplit(".", 1)[0]
    return name


def build_face_path(base_path, stem):
    """Join base_path and stem with a Windows backslash, tolerating a
    trailing separator on base_path. Empty base_path returns stem alone.
    Pure function, testable outside ComfyUI.
    """
    base = base_path.strip().rstrip("\\/")
    return f"{base}\\{stem}" if base else stem


class LoadImageFace:
    """LoadImage variant for the face-swap source image: loads the image
    like the builtin LoadImage, and additionally outputs a save path built
    from the chosen file's name — base_path + "\\" + name without
    extension (e.g. base "E:\\Ai image save\\Confyui" + "Lyne.jpg" ->
    "E:\\Ai image save\\Confyui\\Lyne").

    Meant to feed the `path` input of Image Saver Simple so the save
    directory follows the selected face automatically. Also outputs the
    bare name if needed elsewhere.

    Original node; delegates the actual image loading to the builtin
    nodes.LoadImage (no reimplementation).
    """

    CATEGORY = "Arrssenne/Image"

    @classmethod
    def INPUT_TYPES(cls):
        from nodes import LoadImage as _LoadImage

        t = _LoadImage.INPUT_TYPES()
        required = {"base_path": ("STRING", {"default": "E:\\Ai image save\\Confyui"})}
        required.update(t["required"])  # base_path first, then image (+upload)
        t["required"] = required
        return t

    RETURN_TYPES = ("IMAGE", "MASK", "STRING", "STRING")
    RETURN_NAMES = ("IMAGE", "MASK", "path", "name")
    FUNCTION = "execute"

    def execute(self, base_path, image, **kwargs):
        from nodes import LoadImage as _LoadImage

        img, mask = _LoadImage().load_image(image)
        stem = face_image_stem(image)
        return img, mask, build_face_path(base_path, stem), stem

    @classmethod
    def IS_CHANGED(cls, base_path, image, **kwargs):
        from nodes import LoadImage as _LoadImage

        return _LoadImage.IS_CHANGED(image)

    @classmethod
    def VALIDATE_INPUTS(cls, image, **kwargs):
        from nodes import LoadImage as _LoadImage

        return _LoadImage.VALIDATE_INPUTS(image)


def read_wildcard_lines(path):
    """Read a wildcard .txt file, one entry per line, skipping blank lines.
    Missing file returns an empty list instead of raising. Pure function,
    testable outside ComfyUI.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except OSError:
        logger.warning("ArrssenneCardOverlay: wildcard introuvable: %s", path)
        return []


def resolve_wildcard_path(path, package_dir):
    """Resolve a wildcard path: absolute paths are used as-is, relative
    paths are resolved against package_dir (this node's own package folder),
    so the bundled wildcards/ subfolder works out of the box once the pack
    is deployed. Pure function, testable outside ComfyUI.
    """
    if os.path.isabs(path):
        return path
    return os.path.join(package_dir, path)


def pick_lines(rng, lines, count):
    """Pick up to `count` distinct random lines (no repeats within one
    draw). Clamps count to len(lines). Pure function, testable outside
    ComfyUI.
    """
    if not lines:
        return []
    k = min(max(int(count), 0), len(lines))
    return rng.sample(lines, k)


def roll_price(rng, price_min, price_max, price_step, rare_chance, ultra_rare_chance):
    """Roll a card price. Returns (price: int, holo: bool).

    - probability `ultra_rare_chance`: fixed 1 000 000, holo=True.
    - next slice of probability `rare_chance`: fixed 100 000, holo=True.
    - otherwise: random integer in [price_min, price_max], rounded to the
      nearest price_step, holo=False.
    Pure function, testable outside ComfyUI.
    """
    r = rng.random()
    if r < ultra_rare_chance:
        return 1_000_000, True
    if r < ultra_rare_chance + rare_chance:
        return 100_000, True
    step = max(int(price_step), 1)
    lo, hi = int(price_min), int(price_max)
    if lo > hi:
        lo, hi = hi, lo
    raw = rng.randint(lo, hi)
    return round(raw / step) * step, False


def roll_stars(rng, star_min, star_max):
    """Roll an integer star count in [star_min, star_max]. Pure function,
    testable outside ComfyUI.
    """
    lo, hi = int(star_min), int(star_max)
    if lo > hi:
        lo, hi = hi, lo
    return rng.randint(lo, hi)


def format_price(price):
    """Format an integer price as \"$X,XXX\". Pure function."""
    return f"${price:,}"


def star_polygon(cx, cy, r_outer):
    """Return the 10 (x, y) points of a 5-point star centered at (cx, cy),
    point facing up. Pure function, testable outside ComfyUI.
    """
    r_inner = r_outer * 0.42
    points = []
    for i in range(10):
        angle = math.pi / 2 + i * math.pi / 5
        radius = r_outer if i % 2 == 0 else r_inner
        points.append((cx + radius * math.cos(angle), cy - radius * math.sin(angle)))
    return points


def holo_gradient(size, rng):
    """Build a diagonal rainbow-hue gradient image at `size`, used as a
    screen-blended sheen for the rare/ultra-rare holographic price tiers.
    Deterministic given rng. Requires Pillow.
    """
    from PIL import Image

    w, h = size
    small = 24
    grad = Image.new("RGB", (small, small))
    px = grad.load()
    offset = rng.random()
    for i in range(small):
        for j in range(small):
            hue = ((i + j) / (small * 2) + offset) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 0.55, 1.0)
            px[i, j] = (int(r * 255), int(g * 255), int(b * 255))
    return grad.resize((w, h), Image.BICUBIC)


def load_font(font_path, size):
    """Load a TTF font, falling back to Pillow's built-in bitmap font (with
    a logged warning) if font_path can't be found. Requires Pillow.
    """
    from PIL import ImageFont

    try:
        return ImageFont.truetype(font_path, size)
    except Exception:
        logger.warning("ArrssenneCardOverlay: police introuvable (%s), repli sur la police par defaut", font_path)
        return ImageFont.load_default()


GOLD = (212, 175, 55)
WHITE = (240, 240, 240)


def build_card_image(image, name, tags, price_str, stars, holo, font_path, rng):
    """Compose the card overlay (star rating top-right, tags bottom-right,
    name + price banner at the bottom, optional holographic sheen) onto a
    copy of `image` (a Pillow RGB image). Returns a new Pillow RGB image.
    Requires Pillow.
    """
    from PIL import Image, ImageChops, ImageDraw

    card = image.convert("RGB").copy()
    w, h = card.size
    draw = ImageDraw.Draw(card, "RGBA")

    star_r = w * 0.032
    star_x = w * 0.93
    star_y = h * 0.06
    for i in range(stars):
        draw.polygon(star_polygon(star_x, star_y + i * star_r * 2.3, star_r), fill=GOLD)

    tag_size = max(int(h * 0.026), 10)
    tag_font = load_font(font_path, tag_size)
    tag_y = h * 0.70
    for tag in tags:
        label = tag.title()
        bbox = draw.textbbox((0, 0), label, font=tag_font)
        draw.text((w * 0.95 - (bbox[2] - bbox[0]), tag_y), label, font=tag_font, fill=WHITE)
        tag_y += tag_size * 1.3

    banner_top = h * 0.89
    draw.rectangle([0, banner_top, w, h], fill=(0, 0, 0, 190))
    name_size = max(int(h * 0.05), 14)
    name_font = load_font(font_path, name_size)
    text_y = banner_top + (h - banner_top - name_size) / 2
    draw.text((w * 0.05, text_y), name, font=name_font, fill=GOLD)
    price_bbox = draw.textbbox((0, 0), price_str, font=name_font)
    draw.text((w * 0.95 - (price_bbox[2] - price_bbox[0]), text_y), price_str, font=name_font, fill=GOLD)

    if holo:
        sheen = ImageChops.screen(card, holo_gradient((w, h), rng))
        card = Image.blend(card, sheen, 0.35)

    return card


class CardOverlay:
    """Composes a "collector card" overlay (star rating, tags, name + price
    banner, optional holographic sheen for rare price tiers) on top of a
    generated character card image.

    `full_name` = `first_name` input (e.g. from Load image FACE + path) + a
    random surname drawn from `surname_wildcard_path`. Tags = `tag_count`
    random entries from `tag_wildcard_path` plus `tag_special_count` random
    entries from a second, separately curated `tag_special_wildcard_path`.

    Price: normally a random value in [price_min, price_max] (rounded to
    price_step); with probability `rare_chance` it is fixed at 100 000, and
    with probability `ultra_rare_chance` fixed at 1 000 000 -- both rare
    tiers add a holographic sheen. Star count is random in
    [star_min, star_max].

    Wildcard/font paths: relative paths resolve against this node's own
    package folder (bundled wildcards/ subfolder), so it works out of the
    box once the pack is deployed; absolute paths override that.

    Original node, no third-party source.
    """

    CATEGORY = "Arrssenne/Image"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "first_name": ("STRING", {"forceInput": True}),
                "surname_wildcard_path": ("STRING", {"default": "wildcards/card_surname.txt"}),
                "tag_wildcard_path": ("STRING", {"default": "wildcards/card_tag.txt"}),
                "tag_special_wildcard_path": ("STRING", {"default": "wildcards/card_tag_special.txt"}),
                "tag_count": ("INT", {"default": 3, "min": 0, "max": 10}),
                "tag_special_count": ("INT", {"default": 1, "min": 0, "max": 5}),
                "price_min": ("INT", {"default": 1000, "min": 0, "max": 10_000_000}),
                "price_max": ("INT", {"default": 10000, "min": 0, "max": 10_000_000}),
                "price_step": ("INT", {"default": 100, "min": 1, "max": 10000}),
                "rare_chance": ("FLOAT", {"default": 0.03, "min": 0.0, "max": 1.0, "step": 0.001}),
                "ultra_rare_chance": ("FLOAT", {"default": 0.005, "min": 0.0, "max": 1.0, "step": 0.001}),
                "star_min": ("INT", {"default": 1, "min": 1, "max": 5}),
                "star_max": ("INT", {"default": 5, "min": 1, "max": 5}),
                "font_path": ("STRING", {"default": "georgia.ttf"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "INT")
    RETURN_NAMES = ("IMAGE", "full_name", "price_str", "stars")
    FUNCTION = "execute"

    def execute(self, image, first_name, surname_wildcard_path, tag_wildcard_path,
                tag_special_wildcard_path, tag_count, tag_special_count,
                price_min, price_max, price_step, rare_chance, ultra_rare_chance,
                star_min, star_max, font_path, seed):
        import numpy as np
        import torch
        from PIL import Image

        package_dir = os.path.dirname(os.path.abspath(__file__))
        rng = random.Random(seed)

        surnames = read_wildcard_lines(resolve_wildcard_path(surname_wildcard_path, package_dir))
        tags1 = read_wildcard_lines(resolve_wildcard_path(tag_wildcard_path, package_dir))
        tags2 = read_wildcard_lines(resolve_wildcard_path(tag_special_wildcard_path, package_dir))

        surname = rng.choice(surnames) if surnames else ""
        full_name = f"{first_name} {surname}".strip()
        tags = pick_lines(rng, tags1, tag_count) + pick_lines(rng, tags2, tag_special_count)
        price, holo = roll_price(rng, price_min, price_max, price_step, rare_chance, ultra_rare_chance)
        price_str = format_price(price)
        stars = roll_stars(rng, star_min, star_max)

        arr = (image[0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
        pil_img = Image.fromarray(arr).convert("RGB")
        card = build_card_image(pil_img, full_name, tags, price_str, stars, holo, font_path, rng)
        out = torch.from_numpy(np.array(card).astype(np.float32) / 255.0)[None,]

        logger.info("ArrssenneCardOverlay: %s - %s - %s etoiles - holo=%s", full_name, price_str, stars, holo)
        return out, full_name, price_str, stars


LATENT_PRESET_CUSTOM = "Personnalisé"
LATENT_PRESETS = [
    "896x1152 — Portrait 3:4",
    "1216x832 — Paysage 3:2",
    "1024x1024 — Carré 1:1",
    LATENT_PRESET_CUSTOM,
]
LATENT_PRESET_RE = re.compile(r"^\s*(\d+)\s*x\s*(\d+)")


def parse_preset_dimensions(preset):
    """Extract (width, height) from a preset label starting with "WxH".
    Returns None if the label has no leading WxH (e.g. "Personnalisé").
    Pure function, testable outside ComfyUI.
    """
    m = LATENT_PRESET_RE.match(preset)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


class EmptyLatentPreset:
    """EmptyLatentImage variant with a preset dropdown: three common
    resolutions (labelled with orientation and aspect ratio) plus a
    "Personnalisé" entry that uses the custom_width/custom_height widgets
    instead. batch_size always applies.

    The dimensions of a preset are parsed straight from its label
    ("896x1152 — Portrait 3:4" -> 896x1152), so the label list is the
    single source of truth. custom_width/custom_height are ignored unless
    the preset is "Personnalisé" (100% Python: they stay visible either
    way).

    Original node; delegates latent creation to the builtin
    nodes.EmptyLatentImage (no reimplementation).
    """

    CATEGORY = "Arrssenne/Latent"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "preset": (LATENT_PRESETS, {"default": LATENT_PRESETS[0]}),
                "custom_width": ("INT", {"default": 896, "min": 16, "max": 16384, "step": 8}),
                "custom_height": ("INT", {"default": 1152, "min": 16, "max": 16384, "step": 8}),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 4096}),
            }
        }

    RETURN_TYPES = ("LATENT",)
    FUNCTION = "execute"

    def execute(self, preset, custom_width, custom_height, batch_size):
        from nodes import EmptyLatentImage as _EmptyLatentImage

        dims = parse_preset_dimensions(preset)
        width, height = dims if dims else (custom_width, custom_height)
        logger.debug("EmptyLatentPreset: %s -> %sx%s (batch %s)", preset, width, height, batch_size)
        return _EmptyLatentImage().generate(width, height, batch_size)


NODE_CLASS_MAPPINGS = {
    "ArrssenneSwitchFromAny": SwitchFromAny,
    "ArrssenneSwitchFromAny3": SwitchFromAny3,
    "ArrssenneCkptSeedFilename": CkptSeedFilename,
    "ArrssenneLoader": Loader,
    "ArrssenneLoaderCkpt": LoaderCkpt,
    "ArrssenneLoadImageFace": LoadImageFace,
    "ArrssenneCardOverlay": CardOverlay,
    "ArrssenneEmptyLatentPreset": EmptyLatentPreset,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ArrssenneSwitchFromAny": "Switch from any (Arrssenne)",
    "ArrssenneSwitchFromAny3": "Switch from any 3-way (Arrssenne)",
    "ArrssenneCkptSeedFilename": "Filename ckpt+seed (Arrssenne)",
    "ArrssenneLoader": "Loader ckpt+clip+vae+lora (Arrssenne)",
    "ArrssenneLoaderCkpt": "Loader ckpt+lora (Arrssenne)",
    "ArrssenneLoadImageFace": "Load image FACE + path (Arrssenne)",
    "ArrssenneCardOverlay": "Card overlay (Arrssenne)",
    "ArrssenneEmptyLatentPreset": "Empty Latent presets (Arrssenne)",
}
