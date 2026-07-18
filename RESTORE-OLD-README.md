# Restoring the previous profile README

The redesign does **not** delete these existing files:

- `dark-v2.svg`
- `light-v2.svg`
- the old contribution-snake workflow and `output` branch

A copy of the previous README is stored at:

```text
archive/README-before-terminal-redesign.md
```

To restore the old profile:

1. Open `archive/README-before-terminal-redesign.md`.
2. Copy all of its contents.
3. Replace the contents of the root `README.md` with that copy.
4. Commit the change.

You may also create a Git branch named `backup/profile-readme-2026-07-18`
before installing the redesign. That preserves the entire repository state, not
only the README.
