# Instructions for LLM assistants

Read [CONTRIBUTING.md](CONTRIBUTING.md), [SKILLS.md](SKILLS.md) and the
[working guide](docs/agents/README.md). Human documentation starts at the
[TinyWarden documentation index](https://github.com/TinyWarden/tinywarden/blob/main/docs/README.md).

- Keep monitoring behavior in standalone packages using supported SDK operations.
  Do not add per-skill app or host-agent branches to implement a compatible skill.
- Preserve immutable published package identities. README/LICENSE bytes are part
  of package content; a change requires a new version and catalogue identity.
- Use the SDK pinned by `SDK.lock.json`; ordinary verification must not require a
  sibling source checkout or silently select an unpublished SDK.
- Test captured observations, boundaries, missing/incomplete evidence and overrides.
  A real collection check additionally needs the supported sandbox and reviewed
  declared host access. Never change host services merely to run unit fixtures.
- Let the platform own health aggregation, history, notifications and rendering.
  Declare typed metadata and display bindings rather than custom UI code.
- Run `python3.13 -B scripts/verify.py` after package/release changes. Keep assets
  published before their catalogue entries, with exact hashes and byte sizes.
- Update public human references with contract changes. Preserve licenses and keep
  credentials, fleet data and private working memory out of this repository.
