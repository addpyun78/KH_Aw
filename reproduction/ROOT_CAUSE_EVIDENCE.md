# Root Cause Evidence

## Cause 1: invalid cache-root assumption

Old rule: `plugin_root.name == plugin.json.name`.

Actual cache: parent `kh-aw`, leaf `3.2.1`.

Fix: accept either a source root whose leaf is the plugin name or a versioned root whose
parent is the plugin name and whose leaf equals the manifest version.

## Cause 2: raw-byte-only integrity

Machine Git setting: `core.autocrlf=true`.

Example old cached `LICENSE`:

- Manifest LF bytes: `1066`
- Cached CRLF bytes: `1087`
- Normalized LF SHA-256:
  `4a62358edee56daf26a6dbdd7d9a66f578866994502eacb038b381d30778f3d4`
- Manifest SHA-256:
  `4a62358edee56daf26a6dbdd7d9a66f578866994502eacb038b381d30778f3d4`

Fix: new manifests store raw and normalized-LF records; old manifests receive a
backward-compatible normalized comparison for UTF-8 text.

## Cause 3: monolithic doctor

The old plugin cache doctor also demanded repository-level marketplace, CI, reports,
and release-manifest files. Those files do not belong inside a versioned plugin cache.

Fix: plugin and package checks always run; marketplace and distribution checks run only
when an explicit marketplace root/mode is requested.

## Cause 4: unsupported slash command contract

The old policy hard-coded `/agents`, `/context`, `/artifact`, `/search`, `/diff`, and
`/test` as native requirements. Official documentation states that available slash
commands vary by environment.

Fix: requirements are behavioral capabilities. Native commands are preferred when
available; physical tool/subagent evidence can verify the same behavior.

## Cause 5: fragmented ownership

Six public skills could each appear to own part of one end-to-end workflow.

Fix: one public entrypoint with preserved internal workflow references, one task graph,
one state, one version ledger, and one claim verifier.
