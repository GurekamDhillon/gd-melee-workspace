# SSBM Nucleus: in-game mod browser permission (2026-10-08)

**Status: permission GRANTED by the Nucleus creator, with one condition (link back). API access: not yet; the creator
is checking whether it can work as an API.**

## Who

- **Sc00p** (Discord `sc00p57`), creator of **SSBM Nucleus** (`SSBMNucleus.net`; also `vAMPplayer.com`). 1 mutual
  friend, 3 mutual servers with the owner.
- Asked by the owner (Discord "Peace"), 2026-10-08 12:15 PM (Pacific).

## What was said (from the screenshot)

> **Peace:** @Sc00p Yo is it cool if I try to build an in-game modbrowser for my build using the mods on nucleus?
> **Sc00p:** Sure! That sounds sick, just link back to nucleus somewhere and I'm chill with it
> **Peace:** Of course! Also do [...] Nucleus client has? I would [...] with cra[...]  *(partly hidden by a profile card)*
> **Sc00p:** Yeah the[...] see if it would work as like an api
> **Peace:** Yippie!

Evidence: `_research/nucleus/2026-10-08-sc00p-permission.png` (local only; `_research/nucleus/` is git-ignored; a
private conversation with a third party, so it is never committed or published).

## Terms to honour

1. **Link back to Nucleus** visibly wherever its mods appear: the in-game mod browser and the launcher's Mods tab
   (e.g. "Mods from SSBM Nucleus" with a link to https://ssbmnucleus.net), plus CREDITS.md and the release notes
   that ship the feature.
2. Until sc00p confirms an API (or other access method), **do not scrape the site or call its backend** from the
   game, the launcher or any tool. Build against our own index format first (`tools/mods_browser/`,
   `gdmelee-mods.schema.json`, `docs/mods-browser.md`) so a Nucleus source plugs in once the access method is agreed.
3. Ask before redistributing any Nucleus-hosted file ourselves; the browser should fetch from Nucleus at the player's
   request, not mirror it.

## Next (when the owner wants it)

- Design note: in-game mod browser + launcher Mods tab sourcing from Nucleus (what metadata is needed: title, author,
  version, game/disc compatibility (m-ex, ACE, Akaneia), file type and how a mod installs into `mods/`, checksums,
  netplay identity effects).
- Questions for sc00p once the API is on the table: endpoints/format, rate limits, auth, whether mods carry
  compatibility metadata, attribution wording he prefers.
