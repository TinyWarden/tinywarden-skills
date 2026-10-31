"""Real child output/exit survives the package's diagnostic helpers."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from test_update_actions_policy import refresh

command=sys.modules[refresh.__package__+'.command']
logs=sys.modules[refresh.__package__+'.logs']

class UpdateTranscript(unittest.TestCase):
    def test_real_child_output_and_nonzero_exit_are_preserved(self):
        events=[]
        ctx=SimpleNamespace(output=lambda text,stream='stdout':events.append((stream,text)))
        chunks=[]
        with patch.object(command,'tee',lambda data,stream:chunks.append((stream,data))):
            code,output=command.run(ctx,[sys.executable,'-c','import sys;print("native output");sys.exit(17)'],capture=True)
        self.assertEqual(code,17)
        self.assertEqual(output,b'native output\n')
        self.assertIn(('stdout',b'native output\n'),chunks)
        self.assertEqual(events[-1],('exit','17'))

    def test_diagnostic_failure_never_changes_execution_authority(self):
        def broken(*args,**kwargs):raise OSError('log unavailable')
        ctx=SimpleNamespace(output=broken)
        logs.output(ctx,'text')
        logs.failure(ctx,ValueError('native error'))
        logs.output(object(),'older runtime')

if __name__=='__main__':unittest.main()
