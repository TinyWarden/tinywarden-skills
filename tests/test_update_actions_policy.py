"""Package-owned policy regression cases; no native mutation or APT imports."""
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
ROOT=Path(__file__).resolve().parents[1]/'skills/package-updates/actions'
class Error(Exception):
    def __init__(self,reason,subjects=()):
        super().__init__(reason); self.subjects=subjects
scope={'POLICY':{},'MaintenanceError':Error,'Path':Path,'json':json,'hashlib':hashlib,'stat':__import__('stat')}
def load(name,functions=None):
    tree=ast.parse((ROOT/name).read_text())
    nodes=[]
    for n in tree.body:
        if isinstance(n,ast.ImportFrom) and n.level: continue
        if isinstance(n,ast.Import) and any(x.name in ('apt','apt_pkg','apt.progress.base') for x in n.names):continue
        if functions is not None and not isinstance(n,(ast.Import,ast.ImportFrom)) and not(isinstance(n,ast.FunctionDef) and n.name in functions):continue
        if isinstance(n,(ast.FunctionDef,ast.ClassDef)):n.decorator_list=[]
        nodes.append(n)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),name,'exec'),scope)
load('apt_policy.py',{'source_security','tree_digest','digest','canonical','supported_hooks','configuration_digest'})
scope.update(HOOKS={'DPkg::Pre-Install-Pkgs':('/usr/bin/apt-listchanges --apt || test $? -lt 10','/usr/sbin/dpkg-preconfigure --apt || true'),'DPkg::Post-Invoke':('/usr/lib/needrestart/apt-pinvoke','test -x /usr/lib/needrestart/apt-pinvoke && /usr/lib/needrestart/apt-pinvoke || true')},HOOK_FILES=('/usr/bin/apt-listchanges','/usr/sbin/dpkg-preconfigure','/usr/lib/needrestart/apt-pinvoke','/usr/sbin/needrestart'))
load('apt_boot.py')
load('apt_plan.py')
load('apt_archives.py')
def record(name, paths=(), triggers=(), section='utils'):
    return {'name': name, 'paths': paths, 'triggers': triggers, 'section': section}

class PolicyTests(unittest.TestCase):
    def test_upgrade_outcome_labels_preserve_uncertain_and_missing_evidence(self):
        tree = ast.parse((ROOT/'upgrade.py').read_text())
        definition = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_facts')
        namespace = {}
        exec(compile(ast.Module(body=[definition], type_ignores=[]), 'upgrade.py', 'exec'), namespace)
        facts = namespace['_facts']
        schema = json.loads((ROOT/'upgrade-result.schema.json').read_text())
        self.assertEqual(schema, json.loads((ROOT/'upgrade-recovery.schema.json').read_text()))
        for outcome in ['packages_applied', 'no_changes', 'failed', 'interrupted', 'not_started']:
            value = facts(outcome, 2)
            self.assertIn(value['outcome'], schema['properties']['outcome']['enum'])
            self.assertEqual(value['kept_back_count'], 2)
            self.assertIsNone(value['reboot_required'])
        self.assertEqual(facts('interrupted')['outcome'], 'Outcome uncertain')
        self.assertFalse(facts('packages_applied', native={'reboot_required': False})['reboot_required'])

    def setUp(self):
        self.ordinary = ('editor', 'amd64')
        self.handler = ('initramfs-tools', 'all')
        self.installed = {self.ordinary: record('editor'), self.handler:
            record('initramfs-tools', triggers=[('interest', 'update-initramfs')])}

    def blocked(self, changes, installed=None):
        with self.assertRaisesRegex(Error, 'maintenance_boot_review_required'):
            scope['boot_effects'](changes, installed or self.installed)

    def test_userspace_does_not_charge_or_classify_unrelated_boot(self):
        scope['boot_effects']({self.ordinary: self.installed[self.ordinary]}, self.installed)

    def test_candidate_initramfs_hook_blocks_whole_transaction(self):
        self.blocked({self.ordinary: record('editor', ['/usr/share/initramfs-tools/hooks/editor'])})

    def test_direct_boot_and_kernel_tooling(self):
        for name, paths, section in [('editor', ['/boot/vmlinuz'], 'utils'),
                ('grub-common', [], 'utils'), ('linux-foo', [], 'kernel')]:
            with self.subTest(name=name):
                self.blocked({self.ordinary: record(name, paths, section=section)})

    def test_explicit_trigger_reaches_unmodified_installed_handler(self):
        self.blocked({self.ordinary: record('editor', triggers=[('activate', 'update-initramfs')])})

    def test_old_trigger_also_applies_when_candidate_removes_it(self):
        self.installed[self.ordinary]['triggers'] = [('activate', 'update-initramfs')]
        self.blocked({self.ordinary: record('editor')})

    def test_file_trigger_and_declared_chain_reach_boot_handler(self):
        middle = ('middle', 'all')
        self.installed[middle] = record('middle', triggers=[('interest', '/usr/share/editor'),
                                                         ('activate', 'update-initramfs')])
        self.blocked({self.ordinary: record('editor', ['/usr/share/editor/data'])})

    def test_trigger_cycle_terminates(self):
        self.installed[self.ordinary]['triggers'] = [('activate', 'normal'), ('interest', 'normal')]
        scope['boot_effects']({self.ordinary: self.installed[self.ordinary]}, self.installed)

    def test_trigger_parser_rejects_malformed_or_unknown_metadata(self):
        self.assertEqual(scope['triggers']('activate-noawait update-initramfs # generated'),
                         [('activate', 'update-initramfs')])
        for text in ['activate', 'unknown name', 'interest name extra']:
            with self.assertRaisesRegex(Error, 'maintenance_metadata_invalid'):
                scope['triggers'](text)

    def test_archive_transport_alternatives_are_closed(self):
        scope['archive_methods'](['http://repo.invalid/p.deb', 'https://repo.invalid/p.deb'])
        for values in [[], ['file:/repo/p.deb'], ['cdrom:disc'],
                       ['https://repo.invalid/p.deb', 'mirror+file:/mirror/p.deb']]:
            with self.assertRaisesRegex(Error, 'maintenance_archive_method'):
                scope['archive_methods'](values)

    def test_unset_optional_paths_never_hash_the_working_directory(self):
        import json
        scope.update(json=json,hashlib=hashlib)
        def forbidden(path):
            raise AssertionError('unset APT path traversed the working directory')
        saved=scope['Path'];scope['Path']=forbidden
        try:self.assertEqual(scope['tree_digest'](['']),scope['digest']([]))
        finally:scope['Path']=saved

    def test_source_trust_and_expiry_bypass_spellings_are_rejected(self):
        for name, values in [('Trusted', ['yes','TRUE','1','on']),
                            ('Check-Valid-Until', ['no','FALSE','0','off']),
                            ('Allow-Insecure', ['true']), ('Allow-Weak', ['1'])]:
            for value in values:
                with self.assertRaisesRegex(Error, 'maintenance_repository_policy'):
                    scope['source_security'](name,value)
        scope['source_security']('Signed-By','/usr/share/keyrings/debian-archive-keyring.gpg')
        scope['source_security']('Trusted','no')
        for key in ('Valid-Until-Min', 'Valid-Until-Max', 'Date-Max-Future', 'InRelease-Path'):
            with self.assertRaisesRegex(Error, 'maintenance_repository_policy'):
                scope['source_security'](key, '60')
            scope['source_security'](key, '60', upgrade=False)

    def test_cached_release_expiry_and_future_dates_are_rechecked(self):
        from email.utils import formatdate, parsedate_to_datetime
        now = 1792843200
        scope['apt_pkg'] = SimpleNamespace(str_to_time=lambda value: int(parsedate_to_datetime(value).timestamp()))
        valid = {'Date': formatdate(now - 60, usegmt=True), 'Valid-Until': formatdate(now + 60, usegmt=True)}
        scope['valid_release_dates'](valid, now)
        scope['valid_release_dates']({'Date': valid['Date']}, now)
        for section in [dict(valid, **{'Valid-Until': formatdate(now, usegmt=True)}),
                        dict(valid, Date=formatdate(now + 11, usegmt=True)),
                        {'Valid-Until': valid['Valid-Until']}, dict(valid, Date='invalid')]:
            with self.assertRaisesRegex(Error, 'maintenance_repository_expired'):
                scope['valid_release_dates'](section, now)
        scope['apt_pkg'].str_to_time = lambda value: None if value == 'invalid' else int(parsedate_to_datetime(value).timestamp())
        with self.assertRaisesRegex(Error, 'maintenance_repository_expired'):
            scope['valid_release_dates'](dict(valid, **{'Valid-Until': 'invalid'}), now)

    def test_only_documented_noninteractive_hooks_are_supported(self):
        import types
        scope['Path'] = lambda name: types.SimpleNamespace(exists=lambda: False)
        for key, values, accepted in [('DPkg::Pre-Install-Pkgs', ['/usr/sbin/dpkg-preconfigure --apt || true'], True),
                ('DPkg::Pre-Install-Pkgs', ['/usr/bin/custom-prompt'], False),
                ('APT::Update::Post-Invoke', ['/usr/bin/custom-fetch'], False)]:
            scope['apt_pkg'] = types.SimpleNamespace(config=types.SimpleNamespace(keys=lambda: [key], value_list=lambda name: values))
            if accepted:
                scope['supported_hooks']()
            else:
                with self.assertRaisesRegex(Error, 'maintenance_hook_policy'):
                    scope['supported_hooks']()
        scope['Path'] = Path

    def test_missing_metadata_and_payload_traversal_are_blocked(self):
        with self.assertRaisesRegex(Error, 'maintenance_metadata_invalid'):
            scope['boot_effects']({('missing', 'all'): None}, {})
        for name in ['../boot/x', './usr/../boot/x', 'a\x00b']:
            with self.assertRaisesRegex(Error, 'maintenance_metadata_invalid'):
                scope['canonical_path'](name)


class ConfigurationIdentityTests(unittest.TestCase):
    def config(self, pairs, options):
        return SimpleNamespace(keys=lambda:list(pairs)+['DPkg::Options::']*len(options),
            find=lambda key:pairs.get(key,''),value_list=lambda key:options)
    def test_named_key_order_does_not_change_authorized_inputs(self):
        first={'Acquire::Retries':'0','APT::Sandbox::User':'_apt'}
        scope['apt_pkg']=SimpleNamespace(config=self.config(first,['--force-confdef','--force-confold']))
        before=scope['configuration_digest']()
        scope['apt_pkg'].config=self.config(dict(reversed(list(first.items()))),['--force-confdef','--force-confold'])
        self.assertEqual(before,scope['configuration_digest']())
    def test_named_value_and_anonymous_list_order_changes_are_detected(self):
        scope['apt_pkg']=SimpleNamespace(config=self.config({'Acquire::Retries':'0'},['first','second']))
        before=scope['configuration_digest']()
        scope['apt_pkg'].config=self.config({'Acquire::Retries':'1'},['first','second'])
        self.assertNotEqual(before,scope['configuration_digest']())
        scope['apt_pkg'].config=self.config({'Acquire::Retries':'0'},['second','first'])
        self.assertNotEqual(before,scope['configuration_digest']())

class RefreshReaderTests(unittest.TestCase):
    def reader(self, output, code=0, diagnostics=0):
        import contextlib
        import importlib.util
        import io
        import os
        spec=importlib.util.spec_from_file_location('refresh_plan_parser',ROOT.parent/'skill.py')
        skill=importlib.util.module_from_spec(spec);spec.loader.exec_module(skill)
        calls=[]
        child=SimpleNamespace(stdout=io.BytesIO(output),stderr=io.BytesIO(b''),wait=lambda:code,returncode=code)
        def launch(argv,**kwargs):
            calls.append((argv,kwargs));return child
        namespace={'MaintenanceError':Error,'parse_output':skill.parse_output,'os':os,
                   'log_command':lambda *a:None,'exit_code':lambda *a:None,
                   'read_simulation_output':lambda child:(output,diagnostics),
                   'package_lock':contextlib.nullcontext,'readonly_budget':lambda *a,**k:contextlib.nullcontext(),
                   'subprocess':SimpleNamespace(Popen=launch,DEVNULL=-3,PIPE=-1,STDOUT=-2)}
        tree=ast.parse((ROOT/'refresh.py').read_text())
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'available_updates','valid_summary'} or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SUMMARY_KEYS' for t in n.targets)]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'refresh.py','exec'),namespace)
        return namespace,calls

    def test_refresh_reads_a_fixed_simulation_and_returns_counts(self):
        output=b'2 upgraded, 1 newly installed, 0 to remove and 3 not upgraded.\n'
        for mode,argv in [('upgrade',['/usr/bin/apt-get','--simulate','upgrade']),('with-new-pkgs',['/usr/bin/apt-get','--simulate','--with-new-pkgs','upgrade'])]:
            ns,calls=self.reader(output)
            self.assertEqual(ns['available_updates']({'package_mode':mode}),{'upgraded':2,'installed':1,'removed':0,'held_back':3})
            self.assertEqual(calls[0][0],argv)
            self.assertEqual(calls[0][1]['env']['LC_ALL'],'C')

    def test_refresh_rejects_failed_ambiguous_or_oversized_reads(self):
        for output,code in [(b'0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.\n',1),(b'partial output\n',0),(b'x'*(1024*1024+1),0)]:
            ns,_=self.reader(output,code)
            with self.assertRaisesRegex(Error,'maintenance_reader_failed'):
                ns['available_updates']({'package_mode':'upgrade'})

    def test_receipt_summary_is_bounded_and_cannot_claim_failure_as_a_result(self):
        ns,_=self.reader(b'')
        good={'upgraded':0,'installed':0,'removed':0,'held_back':0}
        self.assertTrue(ns['valid_summary'](good,'refreshed'))
        self.assertFalse(ns['valid_summary'](good,'failed'))
        for bad in [None,{},dict(good,upgraded=True),dict(good,removed=-1),dict(good,upgraded=1000001),dict(good,extra=0)]:
            self.assertFalse(ns['valid_summary'](bad,'refreshed'))

    def test_simulation_diagnostics_are_not_silently_merged_into_success(self):
        ns,_=self.reader(b'0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.\n',diagnostics=1)
        with self.assertRaisesRegex(Error,'maintenance_reader_failed'):
            ns['available_updates']({'package_mode':'upgrade'})

    def test_both_streams_share_one_bounded_budget(self):
        import os,selectors,subprocess,sys
        tree=ast.parse((ROOT/'refresh.py').read_text())
        ns={'os':os,'selectors':selectors,'MaintenanceError':Error,'tee':lambda *a:None}
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='read_simulation_output']
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'refresh.py','exec'),ns)
        for count in [10000,700000]:
            child=subprocess.Popen([sys.executable,'-c',f'import os;os.write(1,b"x"*{count});os.write(2,b"y"*{count})'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                if count==10000:self.assertEqual(ns['read_simulation_output'](child),(b'x'*count,count))
                else:
                    with self.assertRaisesRegex(Error,'maintenance_reader_failed'):ns['read_simulation_output'](child)
            finally:
                if child.poll() is None:child.kill()
                child.wait();child.stdout.close();child.stderr.close()
