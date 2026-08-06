# ComfyUI-Arrssenne

Pack de custom nodes personnel pour ComfyUI. Structure conforme au
walkthrough officiel : https://docs.comfy.org/custom-nodes/walkthrough

## Installation

Cloner/copier ce dossier dans `ComfyUI/custom_nodes/`, puis redémarrer ComfyUI.

```
ComfyUI/custom_nodes/comfyui-Arrssenne/
```

## Structure

```
comfyui-Arrssenne/
├── __init__.py                      # Expose NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS, WEB_DIRECTORY
├── pyproject.toml                   # Métadonnées du pack (registry comfy)
├── requirements.txt                 # Dépendances Python (aucune pour l'instant)
├── LICENSE                          # MIT (ce pack)
├── THIRD_PARTY_NOTICES.md           # Licences des nœuds adaptés de packs tiers
└── src/
    └── comfyui_arrssenne/
        ├── __init__.py
        ├── nodes.py                  # Définitions des nœuds
        └── wildcards/                 # Listes pour Card overlay (nom, tags)
            ├── card_surname.txt
            ├── card_tag.txt
            └── card_tag_special.txt
```

## Nœuds

| Nœud | Catégorie | Description | Source |
|------|-----------|--------------|--------|
| **Switch from any** | `Arrssenne/Switch` | Route une entrée `any` vers `on_true` ou `on_false` selon un booléen | Adapté de `CSwitchFromAny` — [comfyui-crystools](https://github.com/crystian/comfyui-crystools) (MIT) |
| **Switch from any 3-way** | `Arrssenne/Switch` | Route une entrée `any` vers 1 des 3 sorties (`1`/`2`/`3`) selon un entier `select` (1-3) | Extension de `CSwitchFromAny` (idem, MIT) — sorties renommables sur le canvas (clic droit → Rename), ex. Detailler/Faceswap/Saveas |
| **Filename ckpt+seed** | `Arrssenne/Text` | Construit un nom de fichier `nomcheckpoint_seed` : retire dossier, extension et suffixe `_NNNNN_` du nom de checkpoint, puis joint le seed avec `_` | Original (remplace la chaîne RegexReplace + SomethingToString + JoinStrings) |
| **Loader ckpt+clip+vae+lora** | `Arrssenne/Loaders` | Loader tout-en-un : checkpoint (MODEL seulement, CLIP/VAE embarqués jamais chargés), CLIP externe (text encoder + type), VAE externe, et application des balises `<lora:nom:force>` trouvées dans le prompt (style Forge). Sorties : MODEL, CLIP, VAE, texte sans balises, checkpoint_name | Original — concept balise-dans-le-prompt inspiré de [comfyui_lora_tag_loader](https://github.com/badjeff/comfyui_lora_tag_loader), implémentation from scratch sur les APIs ComfyUI (folder_paths, comfy.sd, nodes.LoraLoader) |
| **Loader ckpt+lora** | `Arrssenne/Loaders` | Variante du loader tout-en-un pour les checkpoints **auto-suffisants** (CLIP+VAE embarqués, ex. SDXL/Illustrious/Pony) : pas de menus clip/vae — le CLIP et le VAE sortent directement du checkpoint (`output_vae/output_clip=True`). Balises `<lora:nom:force>` du prompt appliquées et retirées, comme l'autre loader. Mêmes 5 sorties (MODEL, CLIP, VAE, texte sans balises, checkpoint_name) → interchangeable avec Loader ckpt+clip+vae+lora dans un workflow. Erreur claire si le checkpoint n'a pas de CLIP utilisable | Original (même base que Loader ckpt+clip+vae+lora) |
| **Load image FACE + path** | `Arrssenne/Image` | LoadImage + sortie `path` = `base_path\nom-sans-extension` (ex. base `E:\Ai image save\Confyui` + `Lyne.jpg` → `E:\Ai image save\Confyui\Lyne`), à brancher sur le `path` d'un Image Saver Simple pour que le répertoire de sauvegarde suive la face choisie. Sorties : IMAGE, MASK, path, name | Original — le chargement d'image est délégué au `LoadImage` builtin |
| **Card overlay** | `Arrssenne/Image` | Compose une carte « collection » par-dessus l'image générée : étoiles (haut-droite), tags (bas-droite, `tag_count` tirés de `tag_wildcard_path` + `tag_special_count` tirés de `tag_special_wildcard_path`), bandeau nom+prix. Nom = `first_name` (ex. sortie `name` de Load image FACE) + nom de famille tiré au sort dans `surname_wildcard_path`. Prix aléatoire `price_min`-`price_max` (arrondi à `price_step`), avec chance `rare_chance` de tomber à 100 000 et `ultra_rare_chance` à 1 000 000 — ces deux paliers rares ajoutent un effet holographique (dégradé arc-en-ciel screen-blend). Étoiles aléatoires `star_min`-`star_max`. Chemins wildcard/police relatifs résolus contre le sous-dossier `wildcards/` du pack. Sorties : IMAGE, full_name, price_str, stars | Original |

### À savoir : sorties non sélectionnées
Les sorties non choisies renvoient un `ExecutionBlocker` (pas `None`) : les nœuds branchés sur ces sorties ne s'exécutent simplement pas, au lieu de planter. C'est nécessaire parce que tout `SaveImage`/`PreviewImage` du graphe s'exécute à chaque run dans ComfyUI, peu importe le switch.

## Ajouter un nœud adapté d'un autre pack

1. Ajouter la classe dans `src/comfyui_arrssenne/nodes.py`.
2. L'enregistrer dans `NODE_CLASS_MAPPINGS` / `NODE_DISPLAY_NAME_MAPPINGS` (même fichier).
3. Documenter la source + licence dans le tableau ci-dessus et dans `THIRD_PARTY_NOTICES.md`.
