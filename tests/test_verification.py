"""A pending replacement must not weaken checks for any published identity."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from verify import verify_catalogue


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.stable = {'id': 'acme/stable', 'version': '1.0.0'}
        self.old = {'id': 'acme/pending', 'version': '1.0.0'}
        self.new = {'id': 'acme/pending', 'version': '2.0.0'}
        self.published = {'format': 1, 'skills': [self.stable, self.old]}

    def test_explicit_candidate_and_released_subset(self):
        verify_catalogue({'format': 1, 'skills': [self.stable]}, self.published, ['pending'], False)
        verify_catalogue({'format': 1, 'skills': [self.stable, self.new]}, self.published, ['pending'], True)

    def test_released_identity_change_is_rejected(self):
        changed = {**self.stable, 'version': '9.0.0'}
        with self.assertRaisesRegex(ValueError, 'Released catalogue'):
            verify_catalogue({'format': 1, 'skills': [changed, self.new]}, self.published, ['pending'], True)

    def test_candidate_must_be_explicit_and_complete(self):
        for entries, include in [([self.stable, self.new], False), ([self.stable], True)]:
            with self.assertRaisesRegex(ValueError, 'candidate catalogue scope'):
                verify_catalogue({'format': 1, 'skills': entries}, self.published, ['pending'], include)

    def test_candidate_cannot_replace_published_bytes_at_same_version(self):
        changed = {**self.old, 'content_sha256': 'different'}
        with self.assertRaisesRegex(ValueError, 'version is immutable'):
            verify_catalogue({'format': 1, 'skills': [self.stable, changed]}, self.published, ['pending'], True)
