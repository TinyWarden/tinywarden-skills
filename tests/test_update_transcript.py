"""Native diagnostics retain concrete errors without retrying package work."""
import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import os
import re
import selectors
import signal
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'skills/package-updates/actions'


def definition(file, name, scope):
    tree = ast.parse((ROOT / file).read_text())
    nodes = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name == name]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), file, 'exec'), scope)
    return scope[name]


class UpdateTranscript(unittest.TestCase):
    def test_refresh_failure_keeps_actual_command_exit_and_never_retries(self):
        class Refusal(Exception):
            pass
        launches, events = [], []
        child = SimpleNamespace(returncode=100, poll=lambda: 100)
        def launch(argv, **kwargs):
            launches.append((argv, kwargs))
            return child
        scope = {'os': os, 're': re, 'selectors': selectors, 'signal': signal,
                 'MaintenanceError': Refusal, 'trusted_sources': lambda _: None,
                 'budget_clock': lambda: 0,
                 'log_command': lambda ctx, argv: events.append(('command', argv)),
                 'exit_code': lambda ctx, code: events.append(('exit', code)),
                 'subprocess': SimpleNamespace(Popen=launch, DEVNULL=-3, TimeoutExpired=TimeoutError)}
        refresh = definition('apt_refresh.py', 'strict_refresh', scope)
        with self.assertRaisesRegex(Refusal, 'maintenance_refresh_failed'):
            refresh(lambda: events.append(('start', True)), object())
        self.assertEqual(len(launches), 1)
        self.assertEqual(launches[0][0][0:3], ['/usr/bin/apt-get', 'update', '--error-on=any'])
        self.assertNotIn('stdout', launches[0][1])
        self.assertNotIn('stderr', launches[0][1])
        self.assertEqual(events[0], ('start', True))
        self.assertEqual(events[-1], ('exit', 100))

    def test_native_library_callbacks_keep_the_real_error_and_original_failure_flag(self):
        captured = []
        apt = SimpleNamespace(progress=SimpleNamespace(base=SimpleNamespace(AcquireProgress=object, InstallProgress=object)))
        scope = {'apt': apt, 'budget_clock': lambda: 0, 'tee': lambda chunk, stream: captured.append((stream, chunk))}
        progress = definition('apt_policy.py', 'FetchProgress', scope)()
        progress.fail(SimpleNamespace(owner=SimpleNamespace(error_text='403 Forbidden from repository')))
        self.assertTrue(progress.failed)
        self.assertEqual(captured, [('stderr', b'403 Forbidden from repository\n')])
        install = definition('apt_transaction.py', 'NativeInstallProgress', scope)()
        self.assertIsNone(install.error('example-package', 'subprocess returned error exit status 1'))
        install.status_change('example-package', 30, 'Unpacking example-package')
        self.assertIn(('stderr', b'example-package: subprocess returned error exit status 1\n'), captured)
        self.assertIn(('stdout', b'example-package: Unpacking example-package\n'), captured)

    def test_logging_api_absence_or_failure_cannot_authorize_or_retry_work(self):
        spec = importlib.util.spec_from_file_location('update_diagnostic_helpers', ROOT / 'logs.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        def broken(*args, **kwargs):
            raise OSError('diagnostic storage unavailable')
        context = SimpleNamespace(output=broken)
        module.output(context, 'diagnostic text')
        module.failure(context, ValueError('native failure'))
        module.output(object(), 'older runtime')
