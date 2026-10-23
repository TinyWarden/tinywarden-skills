# Skill repository guide for LLM assistants

Read [AGENTS.md](../../AGENTS.md), [CONTRIBUTING.md](../../CONTRIBUTING.md) and
[SKILLS.md](../../SKILLS.md).

| Area | Ownership |
| --- | --- |
| `skills/` | Package code, schemas, catalogues, README/LICENSE and descriptors |
| `tests/` | Captured observations, behavior boundaries and optional sandbox tests |
| `scripts/sdk.py`, `SDK.lock.json` | Exact reviewed SDK bootstrap and file hashes |
| `scripts/build.py` | Canonical reproducible package ZIPs and catalogue construction |
| `scripts/verify.py` | Behavior, SDK admission and catalogue/ZIP reproducibility |
| `SKILLS.json` | Public published-release catalogue |

Run verification with Python 3.13. Use a new absolute output directory for a build.
A README-only edit inside a package still changes its canonical content hash.
A root guide edit does not justify rebuilding or publishing unchanged packages.
Do not change SDK pins merely to bypass a local test prerequisite.
Build-tool imports use the pinned SDK's `packages.admission` and `contracts`
modules. Packaged skills depend on the documented SDK entry points and host
interface, not those internal module paths. When an SDK layout changes, update
the exact archive/file lock and verify a fresh cache without a source override.
Keep official package source and catalogue/ZIP identities unchanged during an
SDK-only migration; no repository merge or skill release is implied.

## Load context by task

- Start with the [author journey](https://github.com/TinyWarden/tinywarden/blob/main/docs/build-skills/README.md).
- For collection/state/health use the
  [SDK reference](https://github.com/TinyWarden/tinywarden/blob/main/docs/reference/skills/sdk.md)
  and [host access](https://github.com/TinyWarden/tinywarden/blob/main/docs/reference/skills/host-access.md).
  Test incomplete evidence, boundaries, clocks and reset state.
  Compatible reducer memory survives monitoring gaps; it is not current health.
  Use fresh evidence to reassess remembered results and pending deadlines. Generic
  SDK host observations use UTC independently of the server timezone; do not add
  per-package timezone or clock allowances.
- For multi-target checks use
  [resources](https://github.com/TinyWarden/tinywarden/blob/main/docs/build-skills/resources.md):
  empty selection, missing evidence and membership changes must not fabricate
  health or restart unrelated incidents.
- For metadata use the
  [display](https://github.com/TinyWarden/tinywarden/blob/main/docs/reference/skills/display.md)
  and [notification](https://github.com/TinyWarden/tinywarden/blob/main/docs/reference/skills/notifications.md)
  contracts. The app owns layout, status components and widths.
- For release use [publishing](https://github.com/TinyWarden/tinywarden/blob/main/docs/build-skills/publishing.md)
  and [compatibility](https://github.com/TinyWarden/tinywarden/blob/main/docs/reference/skills/compatibility.md).

Update the reference and human guide under the
[documentation policy](https://github.com/TinyWarden/tinywarden/blob/main/docs/contributing/documentation.md).
Frozen package README changes require the versioned release process.
