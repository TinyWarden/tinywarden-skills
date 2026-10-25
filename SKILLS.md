# Skill repository convention

A TinyWarden skill repository exposes a regular root `SKILLS.json` on its default
branch. Administrators add its public `https://github.com/OWNER/REPOSITORY` URL in
**Settings → Skill repositories**. The app reads the catalogue without building or
executing repository source.

Format 1 has `format: 1` and a `skills` array. Each entry supplies `id`, `version`,
plain-text `name`/`description`, `content_sha256` and an `archive` object containing
`tag`, `asset`, `sha256` and `size`. The archive identifies a published stable GitHub
Release asset in the same repository. Publish the asset before adding its catalogue
entry. Use the current [SKILLS.json](SKILLS.json) as an example and the
[catalogue schema](https://github.com/TinyWarden/tinywarden/blob/main/docs/architecture/skill-repository.schema.json)
for field syntax.

Use stable `namespace/slug` IDs and stable semantic versions. Forks need a distinct
namespace. Package content hashes and ZIP hashes are different identities; preserve
both. The pinned SDK's `skill_tool.py pack` produces canonical package identities.

The Official badge describes verified publishing origin. Host access still requires
administrator review and remains bounded by the host agent's sandbox/local limits.
See [development and verification](README.md#development) and the
[TinyWarden documentation](https://github.com/TinyWarden/tinywarden/blob/main/docs/README.md).

The [author guide](https://github.com/TinyWarden/tinywarden/blob/main/docs/build-skills/README.md)
covers bootstrap, tests, resources, host access, independently authorized actions,
display, notifications and publication. This entry point does not replace the SDK contracts.
