# Cache Shadowing Report

## Current machine snapshot

The cache inventory found `kh-aw` version `3.2.1` under:

`C:/Users/pyun7/.codex/plugins/cache/kh-aw-marketplace/kh-aw/3.2.1`

No duplicate physical version root was found in that cache scan. However, the installed
cache still contains the old six-skill package while the workspace contains the new
single-entry package. Cache presence alone does not prove that Codex has activated it.

## Detection behavior

`installation-status` scans plugin cache and marketplace roots, records manifest hashes,
groups identical versions at different roots, reports all discovered versions, marks
shadowing risk, and chooses the highest matching version only when resolution is not
ambiguous.

The local E2E injected two `4.0.0` roots under different marketplace names. The
inventory returned one duplicate group and `shadowingRisk: true`.

## Required repair

Install published version `4.0.0` through the supported plugin manager, start a new
Codex session, then verify that only `kh-aw` is visible. Do not edit cache files by hand
and do not infer activation from a cache directory.
