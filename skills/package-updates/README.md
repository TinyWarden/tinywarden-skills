# Package updates

Monitoring simulates pending APT upgrades using the server’s locally cached package
lists. It does not change those lists or install packages, and does not verify
repository freshness or security-update counts.

This skill uses Python SDK v3. Supported platform: Debian 13 on amd64.
Actions require managed agent 0.0.22+ and a compatible app; see
[skill compatibility](https://github.com/TinyWarden/tinywarden/blob/main/docs/reference/skills/compatibility.md).
Settings and individual server inheritance are supplied by the TinyWarden engine.

## Refresh package lists

The separate Refresh package lists action runs the fixed APT index refresh with
strict repository checks. It never installs packages. Preparation checks policy
without running the refresh; execution requires both an exact package action grant
in TinyWarden and local administrator trust for its publisher and execution class.
Monitoring permission alone does not permit this action.

The action needs `apt` and `python3-apt`. It refuses unsafe repository settings and
unsupported APT update hooks. A failed or interrupted refresh may have changed some
indexes; it reports that uncertainty and saves its result in the job workspace.
Recovery inspects the saved result while native package/list locks are held and
does not repeat the refresh. See the public
[action authoring guide](https://github.com/TinyWarden/tinywarden/blob/main/docs/build-skills/actions.md).

The read-only command declares dpkg, APT's file/mirror/HTTP(S) method helpers and
`/etc/apt/mirrors` so Debian mirror-based sources can resolve cached package plans.
The helpers run inside the same isolated command: network sockets remain denied,
host inputs remain read-only, and APT hooks/authentication files are not exposed.
SDK assets must support explicitly approved helpers under `/usr/lib` and preserve
the distro's merged `/usr` aliases. Failed or incomplete simulations remain Unknown.

## Notification Details

`notifications.json` declares a bounded, translated Details paragraph from accepted
assessment evidence and effective settings. The app owns notification triggers,
severity, identities, headers and links; only bold, italic and underline are supported.
Missing or invalid bound values keep the generic notification. See the public app
[Details API](https://github.com/TinyWarden/tinywarden/blob/main/docs/architecture/skill-notification-details.md).

## Pending package list

Details displays package names, installed/available versions and planned upgrades,
new dependencies, removals or held-back packages using the shared table API.
Only recognized `Inst`/`Remv` records and the held-back names stanza are extracted
from the existing simulation. No additional command or access permission is used.
APT action records ending with an empty `[]` marker are accepted too; these must
not silently omit a package while its upgrade remains in the reported total.
Missing versions appear as —; APT's held-back names alone do not supply versions
or reasons. The list keeps at most 100 rows, labels truncation and reports partial
parsing separately. Unrecognized details never alter authoritative counts or
severity and arbitrary command output is never published. With no pending actions
and a complete parse, Details is omitted. Compatible older graph data is retained.

## Conservative upgrade

The separately authorized Conservative upgrade action refreshes package lists and
prepares an exact plan of upgrades to already installed packages. Review the
package names, installed/new versions, download size and kept-back packages in
Fleet, then explicitly approve that plan. Downloads and final native inputs are
checked against the approved plan; a changed plan must be prepared again.

The action preserves held packages and refuses additions, removals, downgrades,
unsafe repositories, unsupported hooks, boot/kernel/initramfs changes and
insufficient writable space/inodes. It retains native locks through final checks
and the single package-manager invocation. Local configuration is retained;
package maintainer scripts still run and may restart services. Completion reports
reboot, configuration and service review requirements; missing evidence remains
unknown. This action does not run full-upgrade or automatically repair failures.

An interrupted or failed installation may leave partial changes. The job's durable
receipt and read-only inspector retain that uncertainty and prevent automatic
reapplication. A successful receipt is checked against the installed package state
and selection policy before verification. Local repair may be needed before
reconciliation. Snapshot or otherwise prepare recovery for important servers;
package downgrades are not a general OS rollback.

The SDK retains unfinished action workspaces and package bytes for recovery. Settled, acknowledged jobs may release temporary staging and cached archives; immutable execution receipts remain available to prevent replay.
