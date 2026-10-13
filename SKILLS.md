# Skill repository convention

Paste a public `https://github.com/OWNER/REPOSITORY` URL in Settings → Skill
repositories. The app reads a regular root `SKILLS.json` from the default branch.
It never builds or executes repository source to discover packages.

Catalogue format 1 contains `format` and `skills`. Each skill has `id`, `version`,
plain-text `name` and `description`, `content_sha256`, and `archive`. The archive
has `tag`, `asset`, ZIP `sha256` and byte `size`. The tag identifies a published
stable GitHub Release in the same repository; the asset identifies its ZIP.
Publish assets first, then update the catalogue.

Only the newest stable release of each skill appears in the catalogue. The app
keeps installed versions and historical data independently. A repository cannot
replace a skill installed from a different source. Use a distinct namespace for
forks. Author-supplied publisher names cannot grant the Official badge.

The app supports 200 entries per repository, 512 KiB catalogue bytes, 10 MiB ZIPs,
20 configured repositories and 100 installed skills. Catalogue pages contain 50 items.
Names are at most 120 characters and descriptions at most 500. Versions are stable
`major.minor.patch`; each component is at most nine digits. IDs follow the SDK's
`namespace/slug` grammar. Release tags and ZIP names are bounded safe ASCII names,
at most 128 characters, without path separators. ZIPs must satisfy SDK admission.

Use [SKILLS.json](SKILLS.json) as a complete working example. The app publishes
the full operator/API contract and JSON schema in its architecture documentation.
Community authors can use the [SDK tools](https://github.com/TinyWarden/tinywarden-agent/blob/main/docs/skills/authoring.md)
to create and pack their own packages, then attach those ZIPs to GitHub Releases.
Both archive and canonical content hashes are returned by `skill_tool.py pack`.

Official means acquired through TinyWarden's verified repository identity and
ownership. It describes publishing origin; requested host access remains subject
to administrator approval and the agent's sandbox/local limits.
