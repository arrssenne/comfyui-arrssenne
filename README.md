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
        └── nodes.py                  # Définitions des nœuds
```

## Nœuds

| Nœud | Catégorie | Description | Source |
|------|-----------|--------------|--------|
| **Switch from any** | `Arrssenne/Switch` | Route une entrée `any` vers `on_true` ou `on_false` selon un booléen | Adapté de `CSwitchFromAny` — [comfyui-crystools](https://github.com/crystian/comfyui-crystools) (MIT) |
| **Switch from any 3-way** | `Arrssenne/Switch` | Route une entrée `any` vers 1 des 3 sorties (`1`/`2`/`3`) selon un entier `select` (1-3) | Extension de `CSwitchFromAny` (idem, MIT) — sorties renommables sur le canvas (clic droit → Rename), ex. Detailler/Faceswap/Saveas |

### À savoir : sorties non sélectionnées
Les sorties non choisies renvoient un `ExecutionBlocker` (pas `None`) : les nœuds branchés sur ces sorties ne s'exécutent simplement pas, au lieu de planter. C'est nécessaire parce que tout `SaveImage`/`PreviewImage` du graphe s'exécute à ch