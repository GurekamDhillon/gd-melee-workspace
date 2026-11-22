# Rivals of Aether II Mod Kit as a Geno authoring front-end: feasibility (2026-10-09)

Supersedes nothing. Research only; no installs, no accounts, no terms accepted. Sources fetched 2026-10-09.

## Verdict (short)

**NO-GO on the Mod Kit editor as an authoring tool for Geno. GO-WITH-FALLBACK: Blender-only (what `tools/geno/artist` already is).**
The kit's own terms forbid using the Editor with any project other than the Rivals II Modkit. That is the gate and it fails.

## 1. License

Source: Aether Studios / Epic "Unreal Editor Terms, Disclaimers, and Warranties", Epic EULA-tracking PDF dated 2025-12-18, linked from the Epic store page for the kit
(https://cdn1.epicgames.com/eulatracking-download/aether/en/v1/r1/0da742fb2bc1ec148a9e20f1e3e11ab3.pdf; store: https://store.epicgames.com/p/rivals-of-aether-ii-mod-kit).
I extracted the PDF text locally and read it. Quoted clauses:

- "Use of the Editor ... is subject to the Unreal Engine End User License Agreement ("UE EULA"), which may be found at www.unrealengine.com/eula. By downloading or using the Editor, you also agree to the UE EULA."
- **"Notwithstanding the terms of the UE EULA, you may not use the Editor or any Epic Content (a) with or in connection to any games, projects, products, or services other than the Rivals of Aether II Modkit, or (b) to create or develop any separate or standalone games, projects, products, or services."**
- "Your breach of the foregoing will constitute a material breach of both the UE EULA and this User Agreement ... upon termination ... your license under the UE EULA to use the Editor and any Epic Content will immediately terminate" (other UE versions' licenses are not terminated).
- "Epic Content" = art/content assets Epic makes available through the kit or Marketplace for use with the kit.

Answers:
- (a) Authoring our own original character in their editor, then exporting to Geno: **forbidden by clause (a)** ("in connection to any ... projects ... other than the Modkit"). Exporting/converting for Melee is use "in connection to" another project. Not a gray area worth risking. (Clause is about the Editor, not about the art you made in Blender; art made in Blender never needs the kit, see c.)
- (b) Built-in / sample / Rivals assets: not ours to port. Clause (a)/(b) plus normal copyright; I did not find a separate Aether Studios content license (see gaps). Treat as not allowed. The docs do say any content file can be exported (Asset Actions/Export; https://rivals2.com/workshop/knowledge-base/miscellaneous/export-content-from-workshop/) but that page says nothing on permitted use; do not rely on it.
- (c) Plain Unreal Engine (not the kit): governed by the public UE EULA (unrealengine.com/eula), which I did not re-read in full this pass; the kit text itself says the kit's restriction is "Notwithstanding" the UE EULA, i.e. the plain-engine terms are looser and the kit adds the lock. Plain UE is permitted as a tool for non-UE games in general (EULA royalties apply only to UE-based products), but this must be confirmed against the current EULA text by the owner before relying on it. Practical point: UE gives us nothing Blender does not (see 3).

Gaps: I did not find a Workshop-specific content/modding policy page from Aether Studios, nor Valve's Workshop terms text (WebFetch of the docs site returned navigation only). Owner should check the Steam Workshop Guide PDF (https://rivals2.com/img/Rivals%20of%20Aether%202%20Steam%20Workshop%20Guide%20v1.03.pdf returned only nav/intro text to my fetcher) and the Steam Subscriber Agreement. Nothing I read addresses reverse engineering or redistribution of exported data beyond the above; absence of a clause is not permission.

## 2. Format (official docs, https://rivals2.com/workshop/ , beta)

- Install: Epic launcher, kit includes UE 5.8 and "most of the game's project files"; Steam must be running/logged in to create or publish mods. (https://rivals2.com/workshop/?p=7)
- Character mod = template assets under Content/Mod Content/<ModNumber>/Unreal Assets (https://rivals2.com/workshop/knowledge-base/character-creation/create-your-character-mod/): Skeletal Mesh, Skeleton (no bone requirements listed in that article), Physics Asset HB_<Mod> (hurtboxes and ECB), PH_<Mod>_Shadow, Animation Sequences (one per character state), RivalsLuaCharacterData (hurtbox + animation states), RivalsLuaCharacterDefinition, per-attack RivalsCharacterAttackData (ATT_), skins, palettes, VFX/SFX assets.
- Attacks (https://rivals2.com/workshop/knowledge-base/character-creation/setting-up-an-attack/): Attack Data assets, edited in editor, not scripts. Hitbox Attributes (Name, Bone Name, offset, radius, On Hit Properties Name); On Hit Properties shared by name (knockback); Attack Windows (Startup/Active/Recovery, with cancels and movement); Hitbox Windows (hitbox name, start frame relative to window, length in frames, 0 = whole window). Frame-based.
- Scripting: Lua ("Lua Scripting API Documentation" is in-editor; the web article only points there). Blueprints exist in the stack (CD blueprint, RivalsCharacterRenderer blueprint). I found no statement on editor Python or C++ plugin permission; unverified. Given the engine is a shipped modkit, assume content/Blueprint/Lua only unless the owner finds otherwise.
- Pipeline: Blender -> FBX -> Unreal import; mesh/animation conventions authored in Maya, converted to UE coords. Packaged and published to Steam Workshop via the kit's tool; exact container (pak/IoStore, cooked) not stated in pages I read (cooked pak is the UE norm; unverified).
- Also exists: 2D characters and Rivals 1 character import (not relevant).

## 3. Mapping to our pipeline

Our side (docs/superpowers/plans/2026-10-08-geno-artist-pipeline.md, tools/geno/artist/spec.py): Blender -> glTF with armature extras, bone roles, hurtbox capsules (max 15), clips tiered against 351 motion rows, markers, then geno.json / retarget.json generated.

| item | transfers? |
|---|---|
| mesh, skeleton, skin weights, animation clips | Yes, but only because they are plain Blender/FBX data. The kit adds nothing; we already import glTF from Blender. |
| hurtbox capsules | Rivals uses a UE Physics Asset; ours are capsules by bone. Conceptually close, trivially expressible from Blender empties. No kit needed. |
| hitbox timing/placement | Rivals: bone + offset + radius, start frame/length per window. Ours: retarget.json hitbox joint/offset/size/delays. Direct field mapping (bone->joint, radius->size, start frame->delay). Clean. |
| knockback, hitstun, DI, states | Needs Melee translation (Rivals On Hit Properties are Rivals physics; Melee uses base/growth/angle, hitlag, shieldstun, the 351-row action-state model). Same problem as ports/goku-xv2: translate intent, never copy numbers. |
| Lua move logic | Rivals-specific API; would need a manual translation layer. |

Conclusion: every transferable piece is already authored in Blender in our pipeline; the Rivals-specific pieces (data assets, Lua) do not map without redesign.

## 4. Effort, risks, next step

- Minimal exporter proof via the kit: M-L, and moot because of the license. Do not build it.
- Fallback A (recommended): Blender-only, current `tools/geno/artist`. If we want a Rivals-style ATT-like authoring layer, add a Blender panel that writes hitbox windows (name, bone, offset, radius, start frame, length) into the action markers/extras; the existing validator/generator then emits retarget.json. Effort S-M.
- Fallback B: plain UE + custom plugin: M-L, gains nothing over Blender, adds a heavy dependency; also confirm plain UE EULA first.
- Risks: terms could be updated; unverified items (Python/C++ policy, packaging format, Workshop policy page) are irrelevant once no-go holds.
- Exact next step: none required for the kit. If interested in the Rivals-style hitbox-window UI, spec the Blender-side marker schema in tools/geno/artist.

## Owner actions

- None required. Installing the kit through the Epic launcher and accepting its terms is the owner's job and I recommend NOT doing so for Geno authoring (it would bind the owner to the clause above on that install). If the owner wants certainty, ask Aether Studios (support / Discord) in writing whether an exporter to a non-Rivals game is permitted; expect no.
- Optional: owner reads the current Unreal Engine EULA and the Workshop Guide PDF to close the gaps listed in section 1.
