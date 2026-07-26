# GitHub Publication Procedure

Repository: `https://github.com/addpyun78/KH_Aw`

Branch: `kh-aw-marketplace`
Tag pattern: `kh-aw-v4.0.0`

Published branch commit during this redesign: `f58fe40`.

Before a publish, run from the repository root:

```powershell
python -m pytest -q
Get-ChildItem plugins/kh-aw/scripts/*.mjs | ForEach-Object { node --check $_.FullName }
python plugins/kh-aw/scripts/kh_aw_cli.py build-package-manifest --plugin-root plugins/kh-aw
python plugins/kh-aw/scripts/kh_aw_cli.py build-release-manifest --marketplace-root .
python plugins/kh-aw/scripts/kh_aw_cli.py doctor --plugin-root plugins/kh-aw --marketplace-root . --distribution
python plugins/kh-aw/scripts/kh_aw_cli.py e2e --plugin-root plugins/kh-aw
python plugins/kh-aw/scripts/kh_aw_cli.py build-package --plugin-root plugins/kh-aw
```

Commit and publish only the exact state tested above. Install through the supported
Codex plugin manager, open a new session, invoke `@kh-aw`, and save that session evidence.
Do not edit a cache directory to simulate installation.
