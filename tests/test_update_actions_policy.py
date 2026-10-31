"""Command outcomes and approval scope of independently delivered Updates actions."""
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.cache/sdk/sdk/python/runtime'))
parent = types.ModuleType('pu1_package')
parent.__path__ = [str(ROOT / 'skills/package-updates')]
sys.modules['pu1_package'] = parent
refresh = importlib.import_module('pu1_package.actions.refresh')
upgrade = importlib.import_module('pu1_package.actions.upgrade')
from skill_actions import ActionFailure


def context():
    return SimpleNamespace(job_id='job', binding={'content_sha256':'a'*64},
        plan_sha256='b'*64, check_start=lambda:None, commit=lambda facts:None)


def summary(upgraded=0, installed=0, removed=0, held=0):
    return f'{upgraded} upgraded, {installed} newly installed, {removed} to remove and {held} not upgraded.\n'.encode()


class RefreshTests(unittest.TestCase):
    def execute(self, commands):
        receipts=[]
        with patch.object(refresh,'preflight'),patch.object(refresh,'run',side_effect=commands) as runner,patch.object(refresh,'save',lambda c,n,r:receipts.append(json.loads(json.dumps(r)))):
            result=refresh.apply({'plan':refresh.PLAN,'settings':{'package_mode':'with-new-pkgs'}},context())
        return result,receipts,runner

    def test_repository_failure_keeps_real_exit_and_does_not_read_or_retry(self):
        result,receipts,runner=self.execute([(100,b'')])
        self.assertEqual(runner.call_count,1)
        self.assertEqual(runner.call_args.args[1],['/usr/bin/apt-get','update','--error-on=any'])
        self.assertEqual(result['facts']['refresh_exit'],100)
        self.assertTrue(result['local_verified'])
        self.assertFalse(result['process_running'])
        self.assertEqual(receipts[-1]['outcome'],'failed')

    def test_summary_error_does_not_erase_successful_refresh(self):
        result,receipts,runner=self.execute([(0,b''),(100,b'')])
        self.assertEqual(result['facts'],{'outcome':'summary_failed','refresh_exit':0,'summary_exit':100})
        self.assertEqual(result['reason']['key'],'actions.reason.maintenance_refresh_summary_failed')
        self.assertEqual(receipts[1]['refresh_exit'],0)
        self.assertEqual(runner.call_args.args[1],upgrade.PREVIEW)

    def test_zero_counts_are_known_and_monitoring_mode_does_not_widen_command(self):
        result,_,runner=self.execute([(0,b''),(0,summary())])
        self.assertIsNone(result['reason'])
        self.assertEqual(result['facts']['upgraded'],0)
        self.assertEqual(result['facts']['installed'],0)
        argv=runner.call_args.args[1]
        self.assertEqual(argv,upgrade.PREVIEW)
        for policy in ['APT::Get::Upgrade-Allow-New=false','APT::Ignore-Hold=false',
                       'APT::Get::allow-change-held-packages=false','APT::Get::Remove=false']:
            self.assertIn(policy,argv)

    def test_parser_failure_retains_both_completed_native_exits(self):
        result,_,_=self.execute([(0,b''),(0,b'unexpected native output\n')])
        self.assertEqual(result['facts']['refresh_exit'],0)
        self.assertEqual(result['facts']['summary_exit'],0)
        self.assertEqual(result['facts']['outcome'],'summary_failed')


class UpgradeTests(unittest.TestCase):
    def test_preview_is_read_only_and_no_change_needs_no_installation(self):
        with patch.object(upgrade,'preflight'),patch.object(upgrade,'run',return_value=(0,summary())) as runner:
            result=upgrade.prepare({},context())
        self.assertFalse(result['has_changes'])
        self.assertEqual(result['effect'],'none')
        self.assertEqual(result['result']['facts']['outcome'],'Nothing to upgrade')
        self.assertIn('--simulate',runner.call_args.args[1])
        self.assertNotIn('update',runner.call_args.args[1])

    def test_preview_reconciles_installed_and_candidate_versions(self):
        output=b'Inst editor [1.0] (2.0 Debian:stable [amd64])\nConf editor (2.0 Debian:stable [amd64])\n'+summary(1,held=2)
        value=upgrade.preview(output,0)
        self.assertEqual(value['packages'],[{'name':'editor','installed_version':'1.0','candidate_version':'2.0'}])
        self.assertEqual(value['kept_back_count'],2)
        for invalid in [summary(1),b'Inst editor (2.0 Debian:stable [amd64])\n'+summary(0,1),summary(0,0,1),b'E: broken state\n'+summary()]:
            with self.assertRaises(upgrade.CommandError):upgrade.preview(invalid,0)

    def execute(self,code):
        plan={'operation':'upgrade_packages','command_policy':upgrade.POLICY}
        with patch.object(upgrade,'preflight'),patch.object(upgrade,'load',side_effect=FileNotFoundError),patch.object(upgrade,'save') as save,patch.object(upgrade,'run',return_value=(code,b'')) as run:
            result=upgrade.apply({'plan':plan},context())
        return result,save,run

    def test_success_comes_from_native_command_and_its_own_receipt(self):
        result,save,runner=self.execute(0)
        self.assertIsNone(result['reason'])
        self.assertTrue(result['local_verified'])
        self.assertEqual(json.loads(result['receipt_json'])['exit_code'],0)
        self.assertEqual(runner.call_count,1)
        self.assertNotIn('--simulate',runner.call_args.args[1])
        self.assertEqual(runner.call_args.args[1][-1],'upgrade')

    def test_known_dpkg_failure_is_settled_with_possible_changes_and_no_retry(self):
        result,_,runner=self.execute(100)
        self.assertEqual(result['facts'],{'outcome':'Failed','exit_code':100})
        self.assertTrue(result['local_verified'])
        self.assertEqual(result['effect'],'changed')
        self.assertFalse(result['process_running'])
        self.assertEqual(runner.call_count,1)

    def test_start_fence_or_existing_receipt_prevents_command_execution(self):
        with patch.object(upgrade,'preflight'),patch.object(upgrade,'load',return_value={'outcome':'running'}),patch.object(upgrade,'run') as run:
            with self.assertRaises(ActionFailure):upgrade.apply({'plan':{'operation':'upgrade_packages','command_policy':upgrade.POLICY}},context())
            run.assert_not_called()
        ctx=context();ctx.check_start=lambda:(_ for _ in ()).throw(ValueError('expired'))
        with patch.object(upgrade,'preflight'),patch.object(upgrade,'load',side_effect=FileNotFoundError),patch.object(upgrade,'run') as run:
            with self.assertRaisesRegex(ValueError,'expired'):upgrade.apply({'plan':{'operation':'upgrade_packages','command_policy':upgrade.POLICY}},ctx)
            run.assert_not_called()

    def test_inspection_without_plan_never_replays_and_preserves_uncertainty(self):
        for receipt in [None,{'outcome':'running'},{'outcome':'Failed','exit_code':100}]:
            facts=[];ctx=context();ctx.plan_sha256=None;ctx.commit=facts.append
            with patch.object(upgrade,'load',side_effect=FileNotFoundError if receipt is None else None,return_value=receipt),patch.object(upgrade,'run') as run:
                upgrade.inspect({},ctx)
            self.assertEqual(facts[0]['outcome'],'Outcome uncertain' if receipt is None or receipt['outcome']=='running' else 'Failed')
            run.assert_not_called()

    def test_receipt_verification_rejects_changed_receipt_or_plan(self):
        ctx=context();receipt={'outcome':'Upgrade completed','exit_code':0,'plan_sha256':ctx.plan_sha256}
        with patch.object(upgrade,'load',return_value=receipt):
            self.assertTrue(upgrade.verify({'receipt':receipt},ctx)['verified'])
            self.assertFalse(upgrade.verify({'receipt':{**receipt,'exit_code':100}},ctx)['verified'])
            ctx.plan_sha256='c'*64
            self.assertFalse(upgrade.verify({'receipt':receipt},ctx)['verified'])


if __name__=='__main__':unittest.main()
