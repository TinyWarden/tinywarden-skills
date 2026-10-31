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

SDK3 packages can declare separately permissioned actions. Domain operations belong
to the package; the platform owns authority, delivery, supervision and recovery
transport. Read-only monitoring grants never authorize an action. The released
Updates action uses the public `skill_actions` API and its private job state FD;
do not add APT behavior to the agent or generic SDK. See the canonical
[maintenance contracts](https://github.com/TinyWarden/tinywarden/blob/main/docs/reference/maintenance-actions.md).
Keep published package README bytes and catalogue identities unchanged when only
clarifying this boundary; update repository-level or central guidance instead.
Use `scripts/verify.py --include-unreleased` with an explicitly selected compatible
SDK to validate pending candidates without rewriting the public catalogue/pin.
The default verifier still uses the pinned SDK and checks unchanged released
identities outside `UNRELEASED.json`; candidate admission is a separate assertion.

Updates 1.3.0 uses standard APT commands, its own preview/receipts and the public
`skill_actions` API. Keep domain commands in its package; the app uses action-local
results and never gates them on other skills. SDK inspection receives no original
plan and never retries application. The generic runtime, SDK lock and agent do not
change for this package replacement. See the central human action reference for
all methods/endpoints and approval semantics.

Official packages use canonical `namespace/slug` IDs. The obsolete `alias` manifest
field is not supported by the current SDK. Update package metadata with a new
version when removing it; keep collector and action implementations package-owned.
SDK candidate verification uses the explicit source override and pending release
marker. Final publication pins the public SDK commit/archive/file hashes and
verifies a fresh cache before releasing candidate catalogue entries.
