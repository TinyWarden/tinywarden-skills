# Contributing monitoring skills

This repository owns official package source, captured-observation tests and
independent catalogue/ZIP releases. Generic SDK and host observation capabilities
belong to the [host-agent repository](https://github.com/TinyWarden/tinywarden-agent).
The [platform contributor guide](https://github.com/TinyWarden/tinywarden/blob/main/docs/contributing/README.md)
explains the repository boundaries.
New authors should follow the complete
[Build skills journey](https://github.com/TinyWarden/tinywarden/blob/main/docs/build-skills/README.md).

Run `python3.13 -B scripts/verify.py` to check package behavior, SDK admission and
reproducible ZIP/catalogue output. Optional `--sandbox` checks additionally need a
supported delegated native Linux sandbox. They are not replaced by mocked tests.

Changing package files, including README, changes package content identity. Use a
new version and the normal release process; preserve published versions. Publish
ZIP assets before updating `SKILLS.json`. Keep SDK pins explicit and review affected
packages together. Use [SKILLS.md](SKILLS.md) for the repository contract and
[AGENTS.md](AGENTS.md) for LLM instructions.

Repository build tooling imports the pinned SDK's `runtime/packages/admission.py`
and `runtime/contracts/` modules. These are build-tool dependencies, not imports
for packaged skill code. The SDK starter is under `examples/skills/` in the agent
repository. For SDK development only, `TW_SKILL_SDK_SOURCE` can select an explicit
candidate source tree; unset it when verifying the published lock in a fresh cache.
This override must never silently replace the normal pinned bootstrap.
When `UNRELEASED.json` declares replacements, normal verification checks the
remaining published source against its unchanged catalogue identities. To include
the candidates, explicitly run `python3.13 -B scripts/verify.py --include-unreleased`
with a compatible SDK (and the explicit source override during SDK development).
This checks candidate admission and two reproducible builds without modifying the
public catalogue or SDK lock. It does not verify publication of candidate assets.
Update current guidance under the
[documentation policy](https://github.com/TinyWarden/tinywarden/blob/main/docs/contributing/documentation.md).
