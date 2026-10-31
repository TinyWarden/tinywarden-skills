# Package updates

Monitors the APT package plan from cached indexes. **Check now** is read-only: it
does not refresh indexes or install packages. Choose plain upgrade or upgrade with
new dependencies in monitoring settings; missing/ambiguous evidence stays unknown.
Cached lists do not guarantee repository freshness or independent security coverage.

Updates 1.3.0 also supplies separately authorized **Refresh package lists** and
**Upgrade packages** operations. Use the server skill header's **Operations** menu,
or Fleet's **Skill actions…** picker. A single-server selection starts preparation
on that exact server. Monitoring permission does not grant root execution.

## Refresh package lists

Runs `apt-get update --error-on=any`, then `apt-get --simulate upgrade`. It installs
nothing. The summary uses the same fixed plain-upgrade options as Upgrade packages,
preserving holds and excluding new packages regardless of monitoring settings or
broader administrator APT defaults.
A repository error is a failure; a successful refresh followed by a failed summary
is reported separately. Both native command outputs and exits are retained.

## Upgrade packages

Reads a cached plain-upgrade preview without refreshing lists. No changes finishes
immediately. Otherwise, one explicit approval authorizes ordinary `apt-get upgrade`
for the selected server. The package/version list is a current preview; APT resolves
it when the command runs. It is not an immutable archive transaction.

The fixed command preserves holds and disallows new packages, removals, downgrades
and automatic repair. Configuration files use `--force-confdef`/`--force-confold`.
`DEBIAN_FRONTEND=noninteractive` and `NEEDRESTART_MODE=l` avoid interactive prompts.
Package maintainer scripts may restart services. No reboot, service disabling,
custom capacity forecast or automatic rollback is performed. APT owns its locks,
downloads, repositories and package installation; native errors remain visible.
A failed command may have partly changed packages.

## Permissions and results

Requires Debian 13 amd64, a recognized managed SDK3 agent (0.0.24+ for the explicit
local policy), local publisher/class permission and an exact version's app action
grant. Both operations need `apt-get` from the `apt` package; `python3-apt` is not
required. Both may run with monitoring paused and no other skills installed.
Another skill's settings, version, availability or health cannot gate these actions.
The app separately presents aggregate server health.

Actions own their receipts and outcomes. A known stopped command retains its exit
and releases exclusion, including failure. Lost or running evidence remains
uncertain; inspection never retries installation. The stable dialog shows state,
compact facts and a collapsed **Execution log**, with native command/output/exit
and bounded Copy/Download. Results survive reload in **Recent results** and Activity.

This version replaces the earlier custom exact-package/archive engine and its
whole-host verification policy. Administrators must review the new content and
renew action permissions. Monitoring settings, metrics and history remain compatible.

See the [user guide](https://github.com/TinyWarden/tinywarden/blob/main/docs/using/package-maintenance.md),
[action author guide](https://github.com/TinyWarden/tinywarden/blob/main/docs/build-skills/actions.md)
and [API/SDK contract](https://github.com/TinyWarden/tinywarden/blob/main/docs/reference/skills/actions.md).
