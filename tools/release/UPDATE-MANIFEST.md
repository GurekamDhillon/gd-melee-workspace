# Stable update manifest, schema 1

This is the phase 0/1 contract implementing the accepted
[`launcher-updates-2026-10-10.md`](../../_research/launcher-updates-2026-10-10.md).
It supersedes that note's unimplemented phase-1 details. Downloads, staging,
installation, rollback and cryptographic verification remain phases 2/3.

`update.json` is a GitHub Release asset at
`https://github.com/GurekamDhillon/gd-melee-workspace/releases/latest/download/update.json`.
Only stable numeric releases publish it. The document is a UTF-8 JSON object,
at most 65,536 bytes.

| Field | Contract |
|---|---|
| `schema` | Integer `1` |
| `channel` | Literal `stable` |
| `version` | Numeric `x.y.z[.w]`, no leading zeros or suffix; each component <= 2,147,483,647 |
| `released` | Valid UTC date `YYYY-MM-DD`; cannot precede the cached release date |
| `netplay_protocol` | Positive integer <= 2,147,483,647, from zip `version.txt`, checked against release policy |
| `min_launcher_for_self_update` | Stable version; reserved for phase 2, currently `0.3.0` |
| `notes_url` | Absolute HTTPS release page, no credentials/fragment; <= 4,096 characters |
| `notes_short.en`, `.es` | Nonempty plain text, each <= 2,048 Unicode characters; never HTML |
| `package.url` | Absolute HTTPS zip URL, same URL restrictions; phase 1 never fetches it |
| `package.size` | Positive integer bytes <= 9,007,199,254,740,991 (exact JSON integer range) |
| `package.sha256` | 64 lowercase hex characters; SHA-256 of uploaded zip bytes |
| `files_manifest_sha256` | 64 lowercase hex characters; SHA-256 of `MANIFEST.sha256` inside that zip |
| `critical` | Boolean; never forces an update |

Required fields cannot be omitted or coerced from strings. Readers ignore unknown
fields for additive schema-1 evolution. The generator uses sorted keys, two-space
indentation, UTF-8 without BOM and a final LF. Equal inputs and release dates
produce identical bytes.

Installed versions come from the leading number in `version.txt` line 1.
Comparison uses four integer components (missing fourth = zero), ignoring installed
suffixes such as `0.1.8.1-linux` and the `(melee ...)` annotation. Protocol numbers,
not release numbers, decide netplay compatibility. Warnings name both protocols
and ask players to update together without claiming all later versions match.

## Signature sidecar (phase-2 contract)

`update.json.sig` will be a detached **minisign Ed25519 signature**, using only the
modern prehashed `ED` variant. It contains an untrusted-comment line, a base64
packet (algorithm, 8-byte key ID, 64-byte signature), a trusted-comment line and
a base64 global signature. The main signature covers the BLAKE2b-512 digest of
the exact downloaded JSON bytes; the global signature binds the trusted comment
to the main signature. Verify both, following the
[upstream minisign format](https://jedisct1.github.io/minisign/) and
[reference implementation](https://github.com/jedisct1/minisign).
Reject legacy `Ed` packets to avoid algorithm ambiguity.

Pin the public key/key ID in the launcher binary. Downloaded keys and sidecar
key IDs cannot establish trust. The secret stays offline and outside both repos.
Verify before parsing/using metadata for downloads; missing, malformed,
unknown-key or mismatched signatures fail closed. Never reserialize JSON or
normalize whitespace/newlines before verification. Phase 2 requires negative
tests for tampered bytes, signatures and trusted comments.

**Signing is not implemented in phase 1:** keys and a compiled verifier do not
exist. The generator requires `--allow-unsigned`, prints UNSIGNED and emits no
`.sig`. It refuses to leave an existing sidecar paired with new unsigned bytes.
The Qt parser's `RequireSignature` policy rejects every input until a real
verifier exists. `NotifyOnlyUnsigned` validates metadata for notification only;
it never claims authenticity, downloads packages or installs anything. Manifest
SHA-256 fields describe integrity and do not authenticate the publisher.

## Publishing

Add exactly one block to `notes/<version>.md`:

```markdown
<!-- update-summary
en: A short plain-text summary of this release.
es: Un resumen breve de esta versión en texto plano.
-->
```

For a stable numeric version, after the ordinary release guard succeeds,
`publish.ps1` generates metadata from
the exact guarded zip and includes `update.json` in `gh release create` alongside
the zip and checksum. `-DryRun` generates/prints unsigned metadata too. Real phase-1
publication requires `-AllowUnsignedUpdate`. Phase 2 must replace this signing
stub with offline signing, upload the real `.sig` and forbid unsigned downloads.

Non-stable versions such as `0.3.0-rc3` skip manifest generation with a clear note,
including under `-DryRun`. They need no `-AllowUnsignedUpdate` flag and no bilingual
summary block. The publisher marks them `--prerelease --latest=false` and uploads
only the zip and checksum. Existing `update.json`/`.sig` files in a reused output
directory are left alone and never attached. The standalone generator continues
to reject prereleases so they cannot become stable-channel metadata.

Standalone generation (no publishing):

```powershell
python tools/release/generate_update_manifest.py --zip <output>/GDMelee-0.2.2-win64.zip --version 0.2.2 --protocol 6 --notes tools/release/notes/0.2.2.md --output <output>/update.json --allow-unsigned
```

## Checks and privacy

Background checks run on startup and while the launcher remains open, at most
once per 24 hours. The default-on toggle is `update_enabled`. Every attempt,
including failures, persists `update_last_attempt` in UTC; the skipped release is
`update_skipped_version`. Future/corrupt timestamps are treated as due. Manual
Check now bypasses interval/toggle but never playback, `--no-update-check` or
`GDMELEE_NO_UPDATE_CHECK=1`. Starting launcher playback or opening a Creator
project cancels a pending request. Checks stay paused throughout Creator's
lifetime, including asynchronous shutdown after its tab is removed, and resume
when shutdown finishes. Requests are asynchronous: 5 seconds to TLS/first response,
15 seconds total, bounded reads and redirects. Failures never open a modal.

Only a GET for metadata leaves, with `User-Agent: GDMeleeLauncher/<version>` and
normal transport headers/IP address. No user IDs, disc paths, telemetry, cookies,
authorization or game data are attached. The toggle has a visible privacy line.
`update_url.txt` beside the game can override the HTTPS endpoint. Plain HTTP is
allowed only on numeric loopback `127.0.0.1` or `::1` for offline fixtures. Remote
HTTP, credentials and unsafe redirects are refused. Once a redirect chain uses
HTTPS it cannot downgrade, including to loopback HTTP. Invalid overrides fail
silently without unexpectedly falling back to GitHub.

The last valid manifest is cached atomically in
`<userdata>/updates/last-manifest.json`. Startup/offline cache use supplies only
a muted About protocol hint, never a banner. A fresh newer release shows a
non-modal banner with localized notes, a release-page link and Skip this version.
Older/equal releases and skipped versions produce no banners.

Windows explicitly deploys `launcher/plugins/tls/qschannelbackend.dll` and
`launcher/bin/Qt6Network.dll`, required by the release guard. Schannel uses Windows
TLS without OpenSSL DLLs, per [Qt's guidance](https://doc.qt.io/qt-6/ssl.html).
Packaging tests an actual loopback HTTPS response under an SDK-free PATH,
using a test-only certificate pinned by the probe.
