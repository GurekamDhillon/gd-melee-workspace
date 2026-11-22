# Third-party sources (local clones, not vendored)

Cloned for reading or building only, into the git-ignored `_build/third_party/`. Nothing from them is copied into this
folder. Licences and obligations are in `LICENSING.md`.

| Repo | Commit | Licence | Use |
|---|---|---|---|
| github.com/Ploaj/HSDLib (workspace copy `experiment/tooling/HSDLib`) | 6d45b7f4dbb0f1596deab1eb5760f78f2f715eb5 | MIT | linked by `costumebuild` |
| github.com/soopercool101/BrawlCrate (BrawlLib) | a4c1ee3385010d5c64a88df9c56267c61f213321 | LGPL-3.0 | linked by `model_export` / `brawl_matdump` (prebuilt DLL of unrecorded version; see LICENSING.md) |
| github.com/akaneia/m-ex | c9f25da0e59e8c387895371934e98eb5046796b3 | none (all rights reserved) | read only; must not be used |
| github.com/akaneia/mexTool | 30ec86530ec9cecd72ad8ea58016559a188269e2 | none | read only; must not be used |
| github.com/Ploaj/MexManager (mexLib) | aecc921dbd1e13c2c9381f8fae18400cba32a8e0 | none | read only (the reader of the m-ex costume spec); must not be used |
