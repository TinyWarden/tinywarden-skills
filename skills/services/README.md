# Services

One skill monitors the systemd services explicitly selected on each server. It
requires package format 2 / SDK 2 and the resource-capable TinyWarden agent.
Initial platform: Debian 13 amd64, system manager only.

Enable the skill after reviewing its two read-only permissions. Open the server's
Services settings, refresh discovery if needed, select services and save. There
are no default targets. New discoveries are never enrolled automatically.

Only continuous services are selectable. Oneshot, RemainAfterExit, bare templates
and socket/timer/path activated services are shown with an explanation. Loaded
instances have their own identities; aliases resolve to canonical IDs. Missing
selected services remain selected. A change of canonical identity requires review.

The default check interval is 60 seconds, unhealthy confirmation delay 60 seconds,
and boot startup grace 120 seconds. Positive delay requires two distinct fresh
observations. Zero delay allows the first unhealthy observation after boot grace.
Stopped, failed, missing, masked and invalid selected services become critical
after confirmation. Transient starting/stopping/restarting states use the same
confirmation. Running/reloading can recover independently of other targets.
Unreadable, unsupported or expired evidence is unknown, never inferred recovery.

Alerts identify the server and exact service. Removing a target ends monitoring
without a recovery; adding another target preserves existing incidents. Reset
settings restores scalar defaults and keeps the selection. Global defaults never
select targets for other servers.

Discovery is bounded at 512 entries and selection at 64. Partial discovery is
explicit; selected targets are always read separately. State is sampled: short
stops between checks may be missed. Running is not an application response check.
This skill cannot start, stop, restart, read logs or change any service.

Source acceptance uses captured fixtures and disposable systemd units. Publishing
the 1.0.0 ZIP and catalogue entry waits for the compatible platform publication.
