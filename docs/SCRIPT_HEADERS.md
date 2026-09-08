# Script header convention

Every script in this repo should carry a small metadata block, right after the
shebang line (or at the very top for files with no shebang), that the wiki
generator (`docs/generate_inventory.py`) parses to build `docs/inventory.json`
— the data behind the searchable wiki at `docs/index.html`.

## Format

Works the same for `.sh` and `.py` (or any `#`-comment language):

```sh
#!/usr/bin/env bash
# ---
# purpose: One sentence — what this script does.
# usage: How it's invoked, key args/env vars to edit.
# tags: comma, separated, keywords
# ---
```

Fields:

- `purpose` — one sentence, present tense ("Generates...", "Converts...").
- `usage` — the actual invocation, e.g. `sbatch submit.sh` or
  `edit angles[] at top, then ./gen_submit_multiple_cases.sh`.
- `tags` — free-form, comma-separated. Use these consistently so filtering
  works:
  - stage tags: `prep`, `mesh`, `submission`, `postprocessing`, `analysis`,
    `cleanup`, `utility`
  - relationship tags: `dup` (has a near-duplicate elsewhere — say which one
    in `purpose` or a trailing `note:` line), `pipeline` (called by or calls
    another script in this repo), `template` (meant to be copied/edited, not
    run as-is)
  - `sec` if the script touches credentials, secrets, or user-account
    provisioning — required whenever it applies.

Optional extra line if useful:

```sh
# note: near-duplicate of convert_vtk2binary_snellius.py — differs in path layout
```

## Adding a new script

1. Add the header block.
2. Run `python3 docs/generate_inventory.py` from the repo root — this
   regenerates `docs/inventory.json` from every header in the repo.
3. Commit both the script and the updated `docs/inventory.json`.

A pre-commit hook (`.githooks/pre-commit`) does step 2 automatically and
stages the regenerated file — see `docs/HOOKS.md` to enable it.

## Why headers instead of a hand-maintained table

The wiki used to be a hand-typed table that drifts the moment someone adds a
script. Putting the metadata in the script itself means the source of truth
lives next to the code, and the wiki is a mechanical projection of it — never
manually edited.
