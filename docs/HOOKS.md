# Enabling the pre-commit hook

This repo ships a hook at `.githooks/pre-commit` that regenerates
`docs/inventory.json` from script headers (see `docs/SCRIPT_HEADERS.md`) and
stages it automatically before every commit. Git doesn't enable hooks from a
tracked folder by default, so each clone needs to opt in once:

```sh
git config core.hooksPath .githooks
```

After that, any commit that adds or edits a script's header block will
automatically pick up the change in `docs/inventory.json` — no manual step
needed.

To check it's active:

```sh
git config core.hooksPath   # should print .githooks
```

## CI backstop

`.github/workflows/deploy-wiki.yml` also runs `python3 docs/generate_inventory.py`
on every push to `main` and fails the build if it produces a diff — a
backstop for anyone who commits without the hook enabled. On success it
publishes `docs/` to GitHub Pages, so the public wiki always reflects what's
on `main`.

## One-time repo setup for the published wiki

GitHub Pages needs to be pointed at Actions once, after this workflow is
first pushed: **Settings → Pages → Build and deployment → Source →
GitHub Actions**. After that, every push to `main` that touches a script or
the `docs/` folder redeploys the wiki automatically — nothing manual.
