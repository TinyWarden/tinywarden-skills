# TinyWarden skills

Official monitoring packages for [TinyWarden](https://github.com/TinyWarden/tinywarden):

- [Disk space](skills/disk-local/README.md)
- [Filesystem trim](skills/fstrim-status/README.md)
- [Package updates](skills/package-updates/README.md)
- [Reboot status](skills/reboot-required/README.md)
- [Services](skills/services/README.md)

Open **Skills → Manage skills** in TinyWarden to install packages. Review requested
host access before enabling a skill. For Services choose monitored services on each
server; its initial selection is empty.

These skills observe and report. They do not install operating-system updates,
reboot servers or execute filesystem trim. Administrative package actions live in
the separate [Fleet maintenance workflow](https://github.com/TinyWarden/tinywarden/blob/main/docs/using/package-maintenance.md); they do not expand a skill’s host permissions.

## Development

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
