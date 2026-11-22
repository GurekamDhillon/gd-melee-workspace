# Xenoverse 2 (`xv2.pc`) IR conventions

`xv2.pc` describes the hashed PC source files in the accepted Goku v0.1 package.
The destination is GD's Melee. A source record does not establish equivalent
Melee behavior. XV2 did not run successfully; there is no `observed` provenance.

## Index spaces

| Space | Numbering and required scope | Stability |
|---|---|---|
| `xv2.cms_id` | CMS character ID; `GOK` is 0 in the captured CMS. | stable for the captured retail character table |
| `xv2.bcs.partset` | Partset ID in one BCS resource. It is not a model or mesh ID. | stable within the hashed BCS |
| `xv2.esk.joint` | Joint ordinal in one ESK or EAN reference skeleton. The 122-joint render rig and 130-joint body-animation rig differ. | stable within the hashed skeleton |
| `xv2.ean.clip` | Clip ID in one EAN resource. Body, face, camera, common and each skill are distinct scopes. | stable within the hashed EAN |
| `xv2.bac.entry` | Entry ID in one character/common/skill BAC resource. | stable within the hashed BAC |
| `xv2.bcm.node` | Decoder source ID in one BCM. Tree-path entity IDs distinguish expanded occurrences of the same source node. | stable within the hashed BCM and pinned decoder |
| `xv2.bdm.entry` | Reaction/damage entry ID in the BDM selected by the command's scope. | stable within the hashed BDM |
| `xv2.eepk.effect` | Effect ID in the EEPK selected by the command's effect/skill scope. | stable within the hashed EEPK |
| `xv2.emb.index` | Embedded image ordinal in one EMB; diffuse and DYT banks are separate. | stable within the hashed EMB |
| `xv2.cus.skill_id` | CUS skill numbering, qualified by category and ID1/ID2 interpretation. Custom allocations can change between installs. | install-relative; retail IDs are retained as source facts |
| `xv2.emd.mesh` | Document-global traversal ordinal of the selected eight parts' submeshes. `source_submesh` and resource path preserve the EMD-local identity. | stable for this package and traversal |
| `xv2.bsa.entry` | Projectile entry ID in one BSA. | stable within the hashed BSA |

An `IndexSpace` is always an object containing `space` and `value`. The existing
schema also deliberately uses integers for structural fields such as
`Joint.index`, `Joint.parent`, `BoneRole.joint`, `Mesh.index`, and part visibility
mesh lists. These retain their schema types and enclosing skeleton/model scope;
the extension carries the corresponding named source space. Raw parser data is
not reclassified as schema indices. Never compare a naked raw field across files.

`identity.index_mappings` records partial resolution rules: CMS to BCS partset;
BCM to BAC; BAC animation to EAN; BAC reaction to BDM; BAC effect to EEPK;
material sampler to EMB; and CUS skill category/directory to BAC. In particular,
`clipId` alone is insufficient: combine it with `sourceScope` and the selected
character/common/skill resource. Unresolved references stay unresolved.

## Script language `xv2.bac`

The decoder is Xv2CoreLib at commit `59242676`. Commands have a type ID, source
start frame and duration. These are static decoded values, not measurements of
the runtime clock, branch selection, contact, or simultaneous command order.

| Source type | Canonical EventOp | Interpretation limit |
|---|---|---|
| Hitbox | `hitbox.create` | Source shape and reaction are retained; no Melee knockback conversion is implied. |
| Invulnerability | `body.state` | Preserve the source state; target state selection is an adaptation. |
| Projectile | `article.spawn` | BSA entry/scope still need resolution and host implementation. |
| Effect | `gfx.spawn` | EEPK scope and effect ID remain source-specific. |
| Sound | `sfx.play` | ACB/cue resolution is absent in v0.1. |
| Time Scale | `timer.set_anim_rate` | Preserve the decoded value and duration. |
| Movement | `move.velocity` | Source coordinate space, flags and integration remain in raw form. |
| Throw Handler | `throw.set` | Member of the schema's `throw.*` family; no claim that it is a Melee throw record. |
| Animation and all other types | `engine.<normalized_type_name>` | Includes Tracking, Homing, Targeting Assistance, Camera, BCM Callback, Function and Aura. |

Every BAC entry, including empty entries, is a Subaction with a main Script.
The Subaction's `clip` is the first resolved animation event for navigation;
`animation_bindings` preserves all animation selections. It must not be treated
as a faithful single-clip execution model. BCM nodes become Actions whose child
and loop links are inferred transition candidates. Runtime condition evaluation
and air/charge/connect branches remain unexecuted.

## Extension blocks (`engine["xv2.pc"]`)

- **Resource:** CPK origin, raw BlobRef and decoded BlobRef. Decoded fields are
  addressed using JSON Pointers; checksums cover the complete sidecar.
- **Skeleton:** purpose (`render` or `animation_reference`), source file,
  named joint space, typed joint indices and the original quaternion/TRS BlobRef.
  Hair attaches at Head; belt attaches at Pelvis. SCD simulation is unconverted.
- **Model/Mesh/Material:** selected part metadata, stable mesh numbering,
  geometry BlobRefs, EMM BlobRefs and texture/DYT sampler references. A material
  record does not claim the source shader has been reproduced.
- **Costume/CostumeSet:** typed BCS partset ID, source partset BlobRef and grouping
  by geometry selectors. Only the selected base partset's geometry is decoded.
- **Animation:** typed clip ID, EAN scope, source pointer and camera flag.
  `fps:null` means unmeasured. The 60-fps LibXenoverse export convention is not
  an XV2 runtime measurement. Keys remain in external BlobRefs.
- **Subaction/Action:** source namespace, animation bindings, source flags,
  input mask, decoded pointer and unexecuted condition status.
- **Event:** the schema has no Event-level `engine` property. Therefore the
  extension is at `args.engine["xv2.pc"]`; it contains the source resource,
  decoded event pointer, duration and Encoding description. `raw.opcode` and
  `raw.engine_name` retain the pinned parser's label. Raw bytes stay external.
- **Hitbox:** source shape, min/max, source bone, typed joint/reaction index and
  reaction scope. `size` retains the source Size scalar, with sphere equivalence
  explicitly unverified. Unknown angle, growth and base knockback are omitted;
  target values must be labelled design values outside the source document.
- **EffectBank/Article:** bank-scoped typed effect/projectile indices and source
  BlobRefs. SoundBank references can remain unresolved; no samples are invented.
- **Integration:** source package, part manifest and skill-binding BlobRefs,
  role-map path and the requirement to select entities through root `parity`.

## Evidence and parity

Every captured raw file has a `file_bytes` evidence record with its SHA-256.
Parser output, v0.1 structural validation, parser enum knowledge and adaptation
decisions have separate evidence. A checked hash proves identity; structural
checks prove only their documented invariants. They do not verify gameplay.

The schema's BoneRole and Attribute records have no entity IDs. Role parity
therefore references the actual Joint entity and states the exact role in
`differences`; attribute parity references an explicit missing-source Issue and
the host fighter-data resource, stating the exact attribute key. This avoids
inventing unresolved role/attribute Ref namespaces. See
[Goku's role map](../../../goku-xv2/ROLE-MAP.md) and
[parity decisions](../../../goku-xv2/PARITY.md).

Coverage is bounded by the shallow dump. Stats and decoded audio are absent.
Each v0.1 gap remains an Issue. All move labels are inferred at best; parity
relations are adaptation proposals and do not imply review or runtime approval.
