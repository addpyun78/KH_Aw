# Installation, Cache, and Shadowing Comparison

## Normal shapes

- Source checkout: `<repo>/plugins/kh-aw`
- Versioned cache: `<CODEX_HOME>/plugins/cache/<marketplace>/kh-aw/<version>`
- Project runtime: `<project>/.kh_aw/runtime/<version>`

The old folder-name rule accepted only the source checkout because it compared the
physical leaf directory directly with `plugin.json.name`. A valid cache leaf is the
version, so the comparison produced a false failure.

The old package manifest also hashed raw bytes only. With Git `core.autocrlf=true`,
UTF-8 text was converted from LF to CRLF while content stayed equivalent. The redesign
stores raw plus normalized-LF hashes and accepts either exact raw bytes or the declared
normalized UTF-8 text form.

Duplicate versions and multiple roots are not silently ignored. `installation-status`
lists every candidate, groups duplicate versions, marks shadowing risk, and reports the
selected highest matching version.
