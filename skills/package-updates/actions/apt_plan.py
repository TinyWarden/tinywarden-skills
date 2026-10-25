"""Structured, exact conservative plans; no simulation-output authorization."""
from .apt_policy import (POLICY, MaintenanceError, apt, apt_pkg, Path, os, time, re, file_digest, tree_digest, digest, canonical, trusted_sources, configuration_digest, MAX_ROWS, MAX_PLAN_BYTES)
from .apt_boot import installed_metadata, boot_effects, local_identity
from .apt_archives import mirror_sources, mirror_aliases, archive_methods

POLICY.update(validity_policy=1)

def valid_release_dates(section, now):
    try:
        created = apt_pkg.str_to_time(section['Date'])
        expires = apt_pkg.str_to_time(section['Valid-Until']) if 'Valid-Until' in section else None
    except (KeyError, ValueError, OverflowError):
        raise MaintenanceError('maintenance_repository_expired') from None
    if type(created) is not int or 'Valid-Until' in section and type(expires) is not int:
        raise MaintenanceError('maintenance_repository_expired')
    if created <= 0 or created > now + 10 or expires is not None and (expires <= created or expires <= now):
        raise MaintenanceError('maintenance_repository_expired')

def valid_indexes(cache):
    # Cache trust does not itself recheck a cached Release's wall-clock expiry.
    # Ask libapt for its actual index destinations without running an acquisition.
    fetcher = apt_pkg.Acquire()
    try:
        if not cache._list.get_indexes(fetcher, True) or any(not m.is_trusted for m in cache._list.list):
            raise MaintenanceError('maintenance_repository_policy')
        directory = Path(apt_pkg.config.find_dir('Dir::State::lists'))
        indexes = [item for item in fetcher.items if item.desc_uri.endswith('/InRelease')]
        if len(indexes) != len(cache._list.list):
            raise MaintenanceError('maintenance_repository_policy')
        for item in indexes:
            if Path(item.destfile).parent != directory / 'partial':
                raise MaintenanceError('maintenance_repository_policy')
            path = directory / Path(item.destfile).name
            if not path.exists():
                path = path.with_name(path.name.removesuffix('InRelease') + 'Release')
            file_digest(path)
            with os.fdopen(apt_pkg.open_maybe_clear_signed_file(str(path))) as source:
                records = apt_pkg.TagFile(source)
                section = next(records, None)
                if section is None or next(records, None) is not None:
                    raise MaintenanceError('maintenance_repository_expired')
                valid_release_dates(section, time.time())
    finally:
        fetcher.shutdown()

def resolve():
    cache = apt.Cache(progress=apt.progress.base.OpProgress())
    if cache.broken_count:
        raise MaintenanceError('maintenance_package_state')
    mirrors = mirror_sources(cache)
    valid_indexes(cache)
    cache.upgrade(dist_upgrade=False)
    packages = []
    installed = installed_metadata(cache)
    changes = {}
    for package in cache.get_changes():
        old, new = package.installed, package.candidate
        if (not old or not new or package.marked_delete or package.marked_reinstall or
                package._pkg.selected_state == apt_pkg.SELSTATE_HOLD or
                new.architecture != old.architecture or apt_pkg.version_compare(new.version, old.version) <= 0):
            raise MaintenanceError('maintenance_package_policy')
        if not new.downloadable or not new.origins or not all(origin.trusted for origin in new.origins):
            raise MaintenanceError('maintenance_repository_policy')
        if not re.fullmatch('[0-9a-f]{64}', new.sha256):
            raise MaintenanceError('maintenance_archive_invalid')
        archive_methods(new.uris, mirrors)
        changes[(package.shortname, old.architecture)] = dict(installed[(package.shortname, old.architecture)], section=new.section)
        packages.append({'name': package.shortname, 'architecture': new.architecture,
                         'installed_version': old.version, 'candidate_version': new.version,
                         'archive_sha256': new.sha256, 'archive_bytes': new.size,
                         'installed_bytes': new.installed_size})
    boot_effects(changes, installed)
    packages.sort(key=lambda p: (p['name'], p['architecture']))
    if len(packages) > MAX_ROWS:
        raise MaintenanceError('maintenance_plan_limit')
    changed = {(p['name'], p['architecture']) for p in packages}
    kept = sorted([{'name': p.shortname, 'architecture': p.installed.architecture,
                    'held': p._pkg.selected_state == apt_pkg.SELSTATE_HOLD}
                   for p in cache if p.installed and p.is_upgradable and
                   (p.shortname, p.installed.architecture) not in changed], key=lambda p: (p['name'], p['architecture']))
    if len(kept) > MAX_ROWS:
        raise MaintenanceError('maintenance_plan_limit')
    sources = [*trusted_sources(), *mirrors.values()]
    plan = {'schema_version': 1, 'action': 'packages.upgrade_conservative.v1', 'provider_version': 1,
            'policy_sha256': digest(POLICY),
            'state_sha256': file_digest(apt_pkg.config.find_file('Dir::State::status')),
            'sources_sha256': tree_digest(sources),
            'indexes_sha256': tree_digest([apt_pkg.config.find_dir('Dir::State::lists')],
                                         [Path(apt_pkg.config.find_dir('Dir::State::lists')) / 'auxfiles'],
                                         mirror_aliases(mirrors)),
            'config_sha256': configuration_digest(), 'local_sha256': local_identity(),
            'selection_sha256': selections(cache),
            'packages': packages, 'kept_back': kept, 'package_count': len(packages), 'kept_back_count': len(kept),
            'download_bytes': sum(p['archive_bytes'] for p in packages),
            'unpacked_bytes': sum(p['installed_bytes'] for p in packages)}
    if len(canonical(plan)) > MAX_PLAN_BYTES:
        raise MaintenanceError('maintenance_plan_limit')
    return cache, plan

def selections(cache):
    return digest(sorted((p.shortname, p.installed.architecture, p._pkg.selected_state,
                          p.is_auto_installed) for p in cache if p.installed))
