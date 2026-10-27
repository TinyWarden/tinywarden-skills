# TinyWarden skills

Official skill packages for [TinyWarden](https://github.com/TinyWarden/tinywarden):

- [Disk space](skills/disk-local/README.md)
- [Filesystem trim](skills/fstrim-status/README.md)
- [Package updates](skills/package-updates/README.md)
- [Reboot status](skills/reboot-required/README.md)
- [Services](skills/services/README.md)

Open **Skills → Manage skills** in TinyWarden to install packages. Review requested
host access before enabling a skill. For Services choose monitored services on each
server; its initial selection is empty.

Monitoring observes and reports without changing the host. Updates 1.2.6 also
supplies separately authorized **Refresh package lists** and **Conservative upgrade**
actions through the [Fleet maintenance workflow](https://github.com/TinyWarden/tinywarden/blob/main/docs/using/package-maintenance.md).
Open a server's **Manage server → Skill actions… → Package updates**, or select servers
and use **More actions → Skill actions…**. The app groups available actions by skill.
Use managed agent 0.0.22+ and a compatible app; monitoring permission never grants
action execution. The skill owns package-management behavior; the universal agent
supplies generic delivery, authorization, supervision and recovery. No official
skill automatically reboots a server or executes filesystem trim.

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
