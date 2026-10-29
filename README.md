# TinyWarden skills

Official skill packages for [TinyWarden](https://github.com/TinyWarden/tinywarden):

- [Disk space](skills/disk-local/README.md)
- [Filesystem trim](skills/fstrim-status/README.md)
- [Package updates](skills/package-updates/README.md)
- [Reboot status](skills/reboot-required/README.md)
- [Services](skills/services/README.md)

For current installation support and app workflows, use the
[human skill guide](https://github.com/TinyWarden/tinywarden/blob/main/docs/using/skills.md).
The package READMEs above are part of immutable releases. Their release-time notes
remain historical; published availability is recorded in [SKILLS.json](SKILLS.json).
Services 1.0.0 is published and usable with a compatible platform despite its
packaged README's original publication-pending note.

Open **Skills → Manage skills** in TinyWarden to install packages. Review requested
host access before enabling a skill. For Services choose monitored services on each
server; its initial selection is empty.

Monitoring observes and reports without changing the host. Package updates also
supplies separately authorized **Refresh package lists** and **Conservative upgrade**
actions through the [Fleet maintenance workflow](https://github.com/TinyWarden/tinywarden/blob/main/docs/using/package-maintenance.md).
Open a server's **Manage server → Skill actions… → Package updates**, or select servers
and use **More actions → Skill actions…**. The app groups available actions by skill.
Current Updates releases (1.2.9+) need managed agent 0.0.24+ and a compatible app;
monitoring permission never grants action execution. A single-server selection
starts preparation immediately. Conservative upgrade then waits for **Approve and
run** on the exact plan; Refresh needs no extra confirmation. Bulk selections
retain target review. One progress window shows preparation, review and results;
reopen it from **View progress** or Fleet Activity. Updating the selected package
requires reviewing its action permissions again. The skill owns package-management
behavior; the universal agent
supplies generic delivery, authorization, supervision and recovery. No official
skill automatically reboots a server or executes filesystem trim.

Updates 1.2.11 adds optional package-owned progress messages through the shared
[operation logging API](https://github.com/TinyWarden/tinywarden/blob/main/docs/build-skills/actions.md#report-useful-progress).
Agent 0.0.25+ and a compatible app show those entries during execution and in saved
Activity results. Older compatible agents keep the same action behavior with
platform stage events only. Logging never grants permission or repeats work.

## Development

Start with the [human skill-building guide](https://github.com/TinyWarden/tinywarden/blob/main/docs/build-skills/README.md)
and [action authoring](https://github.com/TinyWarden/tinywarden/blob/main/docs/build-skills/actions.md).
To contribute an item to that picker, follow
[Add items to Fleet Skill actions](https://github.com/TinyWarden/tinywarden/blob/main/docs/build-skills/actions.md#add-items-to-fleet-skill-actions).

Use Python 3.13. The SDK is fetched at the exact commit and hashes in
[SDK.lock.json](SDK.lock.json); no app or host-agent checkout is required.

```sh
python3.13 -B scripts/verify.py
python3.13 -B scripts/build.py --output /tmp/tinywarden-skill-release
```

Choose a new output directory for builds. See the [repository convention](SKILLS.md),
[contribution instructions](CONTRIBUTING.md) and
[TinyWarden documentation](https://github.com/TinyWarden/tinywarden/blob/main/docs/README.md).
Packages are Apache-2.0; preserve their licenses when adapting them.
