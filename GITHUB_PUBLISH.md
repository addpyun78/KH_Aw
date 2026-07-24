# GitHub Publication Design

Target repository: `addpyun78/AndroidAW`  
Target branch: `kh-aw-marketplace`

The separate branch protects the existing AndroidAW main branch while placing `.agents/plugins/marketplace.json` at the Git repository root, which remote marketplace discovery requires.

## Release tags

Use tags such as `kh-aw-v3.2.0`. Before tagging:

```bash
python3 plugins/kh-aw/scripts/kh_aw_cli.py doctor --plugin-root plugins/kh-aw --marketplace-root .
python3 -m unittest discover -s plugins/kh-aw/tests -p 'test_*.py' -v
```

Review the Git diff to ensure the branch excludes browser profiles, cookie/login databases, `.git` copies, `node_modules`, runtime `data`, `output`, `scratch`, logs, backups, and user preferences.
