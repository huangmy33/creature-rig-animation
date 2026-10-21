# Changelog

## 0.1.0 — Open-source preparation

### Added
- MIT license, bilingual README, contribution and security policies, issue/PR templates.
- Dependency manifests and npm lockfile; ignore rules for private/generated assets.
- Original procedural tube fixture and a repeatable end-to-end demo.
- Regression tests and GitHub Actions for unit checks and Blender smoke testing.
- Preserve the uploaded version's expanded multi-view reviews and contact sheets.

### Fixed
- Scene graph transforms and repeated mesh instances in geometry inspection and guide extraction.
- Legacy/layered Blender Action access, portable validator paths, and current render settings.
- Cyclic/malformed guide hierarchies, invalid extraction parameters, and silent unsupported cycle values.
- Invalid GLB chunk lengths, accidental animation-output overwrite, missing review images.
- Explicit loop checking includes the actual first and last animation frames.

### Scope
- Early release; no claims of broad adoption or production certification.
- Procedural chain smoke tests do not validate all real creatures or wing rigs.
- Test environment and remaining limitations are described in README.
