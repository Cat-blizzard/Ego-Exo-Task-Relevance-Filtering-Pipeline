# Annotation Protocol

Annotators should judge whether a take is useful for coarse loco-manipulation FACT token learning, not whether the video is aesthetically good.

Use the contact sheet first. Optional clips can be used when the sheet is ambiguous.

## Fields

`take_relevance`:

- `A_interaction_rich`
- `B_loco_body`
- `C_active_view_only`
- `D_scene_only`
- `E_fine_dexterous`
- `F_bad_or_unclear`

`ego_hand_visibility`:

- `0`: no hand/wrist/forearm visible
- `1`: partial or intermittent visibility
- `2`: clear and frequent visibility

`exo_body_visibility`:

- `0`: person/body not usable
- `1`: partial body visibility
- `2`: full body or enough torso/limb context

`object_interaction`:

- `0`: no target object or body-object relation
- `1`: weak or ambiguous relation
- `2`: clear reach/contact/carry/place/tool/ball/table object interaction

`phase_diversity`:

- `0`: frames are mostly one state
- `1`: weak state changes
- `2`: clear approach/reach/contact/carry/place/release or body-motion phase changes

`usable_for`:

- `tokenizer_main`
- `loco_aux`
- `discard`
- `diagnostic_candidate`

## Rules of Thumb

Prefer `A_interaction_rich` when ego provides usable interaction cues and exo provides body/global context.

Prefer `B_loco_body` for sports, dance, climbing, walking, turning, and approach/reposition phases where body motion is meaningful but hand-object manipulation is weak.

Use `D_scene_only` when the sheet is mostly walls, fields, floors, static rooms, or scenery with no visible interaction phase.

Use `E_fine_dexterous` for very small hand/tool motions that may be useful later but are not reliable for the first coarse tokenizer.
