# TinyWarden skills

Official monitoring skills for [TinyWarden](https://github.com/TinyWarden/tinywarden):
Disk space, Filesystem trim, Package updates and Reboot status. Each package owns
its Python code, settings, messages, notifications and display descriptor.

In the app, open Skills → Manage skills (`/skills/manage`). This repository is available by default.
Installation adds a skill disabled; review its server access before enabling it.
Updates are manual and preserve compatible settings and retained history.

Skills monitor and report. These packages do not install operating-system updates,
reboot servers or execute filesystem trim.

## Develop and verify

Python 3.13 is the supported SDK runtime. The SDK is fetched at the exact commit
and hashes in SDK.lock.json into ignored `.cache/sdk`. No app or agent checkout
is required. The generic SDK is maintained in the agent repository.

```sh
python3.13 -B scripts/verify.py
python3.13 -B scripts/build.py --output /tmp/tinywarden-skill-release
```

The build creates ready ZIPs and SKILLS.json without executing skill collection.
Package tests use captured observations and mocked host inputs. The optional
`--sandbox` test needs bubblewrap, libseccomp2, unprivileged namespaces and delegated
cgroup controllers; use a supported native systemd session as described by the
[SDK guide](https://github.com/TinyWarden/tinywarden-agent/blob/main/docs/skills/authoring.md).

See [repository convention](SKILLS.md), [publishing](docs/publishing.md), and each
package's README. All code is Apache-2.0; preserve package licenses when deriving
community skills. Forks should use their own skill namespace.
