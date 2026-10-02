# Resume the roguelite on the next machine

Captured 2026-10-01. These branches back up local work, including unreviewed agent
changes. They are not merges into the release or claims that every branch builds.
Existing worktrees, their indexes, and active branches were left unchanged.

## Start here

- Workspace/tools: `handoff/2026-10-01/roguelite-100-integration` in `gd-melee-workspace`.
- Game/Lua/native code: `handoff/2026-10-01/roguelite-100-game` in `melee`.
- Root's additional source/docs/assets: `handoff/2026-10-01/linux-qt-launcher`
  and `handoff/2026-10-01/linux`. Review differences before importing them.
- New model concepts: game branch `handoff/2026-10-01/vk-concepts-kit-20261001`.
  The VK kit is authored Blender source, greymasks and concept renders; it is not
  yet exported to the engine. BF sources are under `pc/assets_src/bf_interior`
  and `pc/assets_src/bf_platform`; runtime exports are in the workspace's
  `menu/out_roguelite/room-kit`.

For a FRESH checkout (do not overwrite an existing Windows workspace):

```sh
git clone -b handoff/2026-10-01/roguelite-100-integration https://github.com/GurekamDhillon/gd-melee-workspace.git gdm
git clone -b handoff/2026-10-01/roguelite-100-game https://github.com/GurekamDhillon/melee.git gdm/melee
git -C gdm/melee worktree add -b resume/roguelite worktrees/linux HEAD
```

The nested `worktrees/linux` path is needed because the current pure-test and
roguelite bundle tools still use it as their source path. On Windows/Git Bash,
set `GW_MELEE` to that same checkout for native builds, rather than building
the separate parent checkout accidentally:

```sh
cd gdm
export GW_MELEE="$(pwd -W)/melee/worktrees/linux"
```

Read `SETUP.md` for the Windows LLVM/MSVC toolchain and disc extraction steps.
Toolchains, native objects, map files, extracted disc headers/assets, private
`.env` settings, saves and disc images must be provisioned locally. Regenerate
the bridge from that machine's own link map; never copy the Linux bridge into a
Windows build. No binaries or cores are part of these source snapshots.

Original procedural/vector sources and original runtime art/meshes have been
preserved, including ignored original PNGs. The art generators and dependency
recipe are in `menu/pipeline` and `tools/roguelite/art_venv.sh`. Raw agent session
JSONL, local caches, game captures, generated bridges, extracted Nintendo data
and compressed duplicate art bundles were omitted. Useful reports, prompts,
small certification summaries and source patches are below `reports/`.

## Current acceptance and first tasks

The reviewed integration ran 251 pure/stub tests, with one skipped. Earlier
native integration evidence was 214/214 under Linux. Those checks are historical
evidence for their recorded source; run the relevant checks on the new machine.
Windows native compilation/playtesting of this latest integration remains to be
done. Snapshotting did not run or certify every agent's WIP independently.

Read `docs/ROGUELITE-100-100-LEDGER.md`,
`docs/FULL-100-100-MODEL-ASSIGNMENT.md`, and
`reports/coordination/100-100/ROOT-REVIEW-NEW-WORK-2026-10-01.md` first.
The ledger's latest commit explicitly records these four findings as OPEN:

1. An actually earned/exported gene cannot be discarded durably: the finish
   ledger still requires the exported gene to exist during save validation.
2. Legacy Restore consumes an item when native healing returns false.
3. V2 Restore saves contradictory inventory and campaign supply counts.
4. Run history is appended after the durable finish save and can vanish on reload.

Pending-export pagination/confirmation and stronger real-menu regressions are
also in that review. Do not trust the old "R2 closed" headline over the newer
findings. Enemy/boss native controls, region/effects integration, audio and camera,
full room certification and the rest of the 100/100 program remain open.

Linux port work is paused by the user. The published `v0.1.8-linux` prerelease
and source branch `release/linux-0.1.8` are a separate validated port baseline;
these unfinished roguelite snapshots are not included in that release.
Do not replace the release with a snapshot or publish another release implicitly.

## Snapshot inventory

Many agent worktrees contain copied baselines, so rows overlap. Treat each as
an isolated recovery/reference branch, not a queue to merge wholesale. `commit`
in SNAPSHOTS.json identifies the source snapshot; the primary workspace branch
also has a following documentation-only commit containing this handoff.

| Repository | Original lane / GitHub snapshot | Changed files in snapshot | Source snapshot |
| --- | --- | ---: | --- |
| workspace | [agent/linux-qt-launcher](https://github.com/GurekamDhillon/gd-melee-workspace/tree/handoff/2026-10-01/linux-qt-launcher) | 437 | `c2f5332478` |
| workspace | [agent/deepseek-certification-20260930](https://github.com/GurekamDhillon/gd-melee-workspace/tree/handoff/2026-10-01/deepseek-certification-20260930) | 172 | `687c1ab27d` |
| workspace | [agent/deepseek-encounters-20260930](https://github.com/GurekamDhillon/gd-melee-workspace/tree/handoff/2026-10-01/deepseek-encounters-20260930) | 171 | `010fa72325` |
| workspace | [agent/deepseek-enemy-behaviors-20260930](https://github.com/GurekamDhillon/gd-melee-workspace/tree/handoff/2026-10-01/deepseek-enemy-behaviors-20260930) | 19 | `b1fcc81a1d` |
| workspace | [agent/deepseek-gene-actions-20260930](https://github.com/GurekamDhillon/gd-melee-workspace/tree/handoff/2026-10-01/deepseek-gene-actions-20260930) | 19 | `4951586693` |
| workspace | [agent/deepseek-gene-world-20260930](https://github.com/GurekamDhillon/gd-melee-workspace/tree/handoff/2026-10-01/deepseek-gene-world-20260930) | 7 | `3af9830971` |
| workspace | [agent/deepseek-integration-20260930](https://github.com/GurekamDhillon/gd-melee-workspace/tree/handoff/2026-10-01/deepseek-integration-20260930) | 19 | `48f3e9e775` |
| workspace | [agent/deepseek-inventory-20260930](https://github.com/GurekamDhillon/gd-melee-workspace/tree/handoff/2026-10-01/deepseek-inventory-20260930) | 19 | `d96bf59d35` |
| workspace | [agent/deepseek-layouts-20260930](https://github.com/GurekamDhillon/gd-melee-workspace/tree/handoff/2026-10-01/deepseek-layouts-20260930) | 71 | `11e8d1ff07` |
| workspace | [agent/deepseek-menu-polish-20260930](https://github.com/GurekamDhillon/gd-melee-workspace/tree/handoff/2026-10-01/deepseek-menu-polish-20260930) | 19 | `27a94a8167` |
| workspace | [agent/deepseek-physical-20260930](https://github.com/GurekamDhillon/gd-melee-workspace/tree/handoff/2026-10-01/deepseek-physical-20260930) | 171 | `bd08aa122b` |
| workspace | [agent/deepseek-rewards-20260930](https://github.com/GurekamDhillon/gd-melee-workspace/tree/handoff/2026-10-01/deepseek-rewards-20260930) | 16 | `ad6f19dd4c` |
| workspace | [agent/deepseek-stage-seams-20260930](https://github.com/GurekamDhillon/gd-melee-workspace/tree/handoff/2026-10-01/deepseek-stage-seams-20260930) | 1 | `7460dc57a1` |
| workspace | [agent/roguelite-100-integration](https://github.com/GurekamDhillon/gd-melee-workspace/tree/handoff/2026-10-01/roguelite-100-integration) | 408 | `f478fe89da` |
| workspace | [agent/model-test-campaign-20260930](https://github.com/GurekamDhillon/gd-melee-workspace/tree/handoff/2026-10-01/model-test-campaign-20260930) | 430 | `6d465c1f48` |
| workspace | [agent/gene-world-capacity-20260930](https://github.com/GurekamDhillon/gd-melee-workspace/tree/handoff/2026-10-01/gene-world-capacity-20260930) | 198 | `089fa746ab` |
| game | [agent/deepseek-certification-20260930](https://github.com/GurekamDhillon/melee/tree/handoff/2026-10-01/deepseek-certification-20260930) | 7 | `bc5f89e52a` |
| game | [agent/deepseek-encounters-20260930](https://github.com/GurekamDhillon/melee/tree/handoff/2026-10-01/deepseek-encounters-20260930) | 6 | `38a665bda1` |
| game | [agent/deepseek-enemy-behaviors-20260930](https://github.com/GurekamDhillon/melee/tree/handoff/2026-10-01/deepseek-enemy-behaviors-20260930) | 6 | `f9da7a6183` |
| game | [agent/deepseek-gene-actions-20260930](https://github.com/GurekamDhillon/melee/tree/handoff/2026-10-01/deepseek-gene-actions-20260930) | 7 | `4b078215a9` |
| game | [agent/deepseek-gene-world-20260930](https://github.com/GurekamDhillon/melee/tree/handoff/2026-10-01/deepseek-gene-world-20260930) | 4 | `4a19293ff6` |
| game | [agent/deepseek-integration-20260930](https://github.com/GurekamDhillon/melee/tree/handoff/2026-10-01/deepseek-integration-20260930) | 5 | `7dc662c2f5` |
| game | [agent/deepseek-inventory-20260930](https://github.com/GurekamDhillon/melee/tree/handoff/2026-10-01/deepseek-inventory-20260930) | 7 | `2e57e08056` |
| game | [agent/deepseek-layouts-20260930](https://github.com/GurekamDhillon/melee/tree/handoff/2026-10-01/deepseek-layouts-20260930) | 8 | `ddd45e16ea` |
| game | [agent/deepseek-menu-polish-20260930](https://github.com/GurekamDhillon/melee/tree/handoff/2026-10-01/deepseek-menu-polish-20260930) | 9 | `0883fe8a29` |
| game | [agent/deepseek-physical-20260930](https://github.com/GurekamDhillon/melee/tree/handoff/2026-10-01/deepseek-physical-20260930) | 6 | `7b908dad51` |
| game | [agent/deepseek-rewards-20260930](https://github.com/GurekamDhillon/melee/tree/handoff/2026-10-01/deepseek-rewards-20260930) | 6 | `0e4055245f` |
| game | [agent/deepseek-stage-seams-20260930](https://github.com/GurekamDhillon/melee/tree/handoff/2026-10-01/deepseek-stage-seams-20260930) | 0 | `7ebd732ee0` |
| game | [agent/roguelite-100-game](https://github.com/GurekamDhillon/melee/tree/handoff/2026-10-01/roguelite-100-game) | 0 | `3062566f59` |
| game | [agent/model-test-campaign-20260930](https://github.com/GurekamDhillon/melee/tree/handoff/2026-10-01/model-test-campaign-20260930) | 8 | `08a292bd5b` |
| game | [agent/gene-world-capacity-20260930](https://github.com/GurekamDhillon/melee/tree/handoff/2026-10-01/gene-world-capacity-20260930) | 2 | `42d92ea6b8` |
| game | [agent/sol-native-owner-cleanup-20260930](https://github.com/GurekamDhillon/melee/tree/handoff/2026-10-01/sol-native-owner-cleanup-20260930) | 28 | `0b227162a4` |
| game | [agent/vk-concepts-kit-20261001](https://github.com/GurekamDhillon/melee/tree/handoff/2026-10-01/vk-concepts-kit-20261001) | 30 | `55b110dd30` |
| game | [agent/linux](https://github.com/GurekamDhillon/melee/tree/handoff/2026-10-01/linux) | 53 | `15c459c507` |
| game | [wip/linux-compat-2026-09-22](https://github.com/GurekamDhillon/melee/tree/handoff/2026-10-01/archived-linux-compat-20260922) | 0 | `0ab62f440c` |
