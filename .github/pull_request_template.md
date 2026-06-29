## What changed


## Accuracy checklist (see MAINTENANCE.md)

- [ ] Every Buildbase API symbol / field / signature touched was verified against the SDK source (`@buildbase/sdk`)
- [ ] No invented APIs; code samples would actually run
- [ ] If the SDK version changed: bumped `version` in `plugins/buildbase/.claude-plugin/plugin.json`
- [ ] Relative links resolve; any reference file > 100 lines has a `## Contents`
- [ ] `SKILL.md` still under 500 lines
- [ ] Evals re-run if behavior changed (local `evaluation/`)
- [ ] No secrets, local paths, or private `os`-monorepo details added
- [ ] `python3 scripts/validate.py` passes locally
