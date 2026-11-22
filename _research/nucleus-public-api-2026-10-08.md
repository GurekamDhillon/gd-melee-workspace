# SSBM Nucleus public mods API v1 (2026-10-08)

Source: https://ssbmnucleus.net/developers (pasted by the owner 2026-10-08; summarised, not copied). Supersedes the
"API pending" note in `nucleus-modloader-2026-10-08.md`. Permission from sc00p stands (link back).

- Base `https://ssbmnucleus.net/api/public/v1`, JSON, no key, no account, CORS `*`. GET only.
- `GET /mods` list/search/sync. Params: `limit` 1-100 (50), `cursor` (opaque, same params only), `type`
  (costume, stage_skin, effects, custom_stage, gameplay_mod, patch, other), `character` (name or slug), `stage`,
  `updated_since` (inclusive), `q` (<=200), `tags`/`exclude_tags` (<=20, comma), `author`, `sort`
  (updated default | newest | downloads | likes | title), `order`. Unknown or repeated params -> 400 (no cache-busters).
  Response `{data:[mod], next_cursor|null, total}`.
- `GET /mods/{id}` -> `{data: mod + archive_files:[{filename,size|null}]}`; 404 if not public.
- `GET /mods/removed?since=&cursor=&limit<=1000` -> `{data:[{id,removed_at}], next_cursor}`.
- `GET /mods/{id}/download[?file={fileId}]` counts a download, 302 to the zip/file. Use the `download_url` fields
  (counted); `zip_url`/`file_url` are uncounted (re-reads only). HEAD does not count.
- Mod: id, title, description (Markdown), author, type, stage, tags, created_at, updated_at, download_count,
  like_count, page_url, thumbnail_url, screenshots[], download_url, zip_url, files[].
  File: id, filename (e.g. `PlFxRe.dat`), file_type (e.g. `character_dat`), character, color (slot, e.g. Red),
  slippi_safe, csp_url, stock_url, preview_url, download_url, file_url. Some hidden files are only in the zip.
- Sync: first run note T0 and page everything; then poll `/mods?updated_since=W-15min` (apply), then
  `/mods/removed?since=W-15min` (delete). Default sort cursors are keyset and stable.
- Cache: 10 min edge cache; 404 cached 1 min. Errors `{error:{code,message}}`; 400 fix-don't-retry; 429/5xx back off.
- Etiquette (binding for us): User-Agent naming the tool + contact; poll at most every 10 min; download via
  `download_url` and cache downloads (never refetch per launch); credit the author and link `page_url` (or the site).
- Versioned path; additive changes within v1 (ignore unknown fields).
