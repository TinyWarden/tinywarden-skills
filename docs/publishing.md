# Publishing skills

Edit packages in `skills/`. Increment a package's version whenever any included
file changes; documentation is part of canonical package identity. Do not replace
different content under an existing ID/version.

1. Verify captured-observation tests and static SDK admission using `scripts/verify.py`.
2. Build into a new output directory with `scripts/build.py --output PATH`.
3. Review the source commit and artifacts; publish each ZIP on its matching
   `slug-vVERSION` release tag in this repository. Releases must be public, published
   and stable. Keep past assets available and do not replace released bytes.
4. Commit the generated SKILLS.json after all referenced release assets exist.
5. In the app, check for updates, review the new version's access, and confirm.

Packaging uses the pinned SDK's canonical ZIP writer and extractor and verifies
the resulting content identity. It never runs host collection. Updating a skill
requires no app or agent binary change when it uses the existing SDK/API.

The initial packages were moved byte-for-byte from agent commit
`f1ef63d619ced336ffa09c7cdfea4f2125042b4b`. Their package versions and canonical
content identities remain intact; source location is outside package identity.

## Compatible SDK and unreleased source

`UNRELEASED.json` excludes accepted development packages from the published build
and catalogue. Services 1.0.0 uses the resource platform and managed agent 0.0.11.
Publish a compatible platform before exposing a package that needs new features.

For local acceptance, set `TW_SKILL_SDK_SOURCE` to the reviewed agent checkout.
Its runtime file hashes are checked. `scripts/build.py --include-unreleased` then
prepares released and pending ZIPs in a new output directory; it does not publish
or rewrite the root catalogue. Normal builds use SDK.lock.json. At publication,
pin the exact published SDK commit and archive/file hashes, remove the package
from UNRELEASED.json, publish its ZIP, then update SKILLS.json. Do not advertise a
release asset that does not exist. Services was accepted with the same bytes under
both the reviewed source SDK and its published, hash-pinned commit.
