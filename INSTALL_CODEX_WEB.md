# Codex Web / Plugin Installation

## A. GitHub remote marketplace package

This repository branch is structured as a Codex Git marketplace. The marketplace root must be the repository root containing:

- `.agents/plugins/marketplace.json`
- `plugins/kh-aw/.codex-plugin/plugin.json`

Use the Git source `addpyun78/AndroidAW` and the branch/ref `kh-aw-marketplace` when the Codex plugin-management surface offers **Add marketplace**, **Custom marketplace**, or a Git marketplace source field.

Then open the added marketplace, select **KH_Aw**, install it, and start a fresh Codex thread with the plugin selected or mentioned.

## B. Workspace-managed Codex web

OpenAI's current plugin help describes installation through **Workspace settings > Plugins**. Whether a custom Git marketplace can be added directly depends on the plan, workspace role, supported Codex surface, and admin policy. If the web UI only exposes the public Plugin Directory, the workspace admin must make the plugin available or the plugin must complete OpenAI's public publishing/review process.

## C. Verification after installation

In a new Codex thread, ask KH_Aw to run its doctor command and report the six installed skills. Then perform a low-risk repository test:

1. Create a tiny exact instruction file.
2. Initialize in analysis-folder-not-provided mode.
3. Confirm `analysis/analysis-ledger.json` is required.
4. Run `advance --stage analyze` before filling it.
5. Confirm the result is `repair-required-nonterminal`, not false success or terminal shutdown.

## D. Update flow

Update the Git branch, bump `plugins/kh-aw/.codex-plugin/plugin.json` semver, refresh/upgrade the marketplace in Codex, reinstall or refresh KH_Aw, and start a new thread so the updated skills are loaded.

## Installation limitation stated plainly

The package and Git marketplace can be prepared and hosted on GitHub. A listing in OpenAI's public Plugin Directory is not created merely by pushing to GitHub; it requires the applicable OpenAI publisher submission, review, and workspace availability controls.
