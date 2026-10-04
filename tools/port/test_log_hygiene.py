"""Scan simulated run artifacts; never open a disc or launch the game."""
import argparse
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import demo_tour
import runs


def variants(secret):
    forms = {secret, secret.replace('\\', '/'), secret.replace('/', '\\')}
    return forms | {json.dumps(v, ensure_ascii=ascii)[1:-1]
                    for v in forms for ascii in (True, False)}


def leaks(folder, secrets):
    # Return artifact names only: a failing test must not echo private values.
    return [file.name for file in folder.rglob('*') if file.is_file()
            and any(v.casefold() in file.read_text(encoding='utf-8').casefold()
                    for secret in secrets for v in variants(secret))]


class LogHygieneTests(unittest.TestCase):
    def test_simulated_run_folder_and_stdout(self):
        disc = r'Z:\synthetic-private\selected.iso'
        other = r'Z:\synthetic-private\other.gcm'
        text = '\n'.join(sorted(variants(disc) | variants(other)))
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,
                {'GW_ISO_ACE': other, 'MELEE_RUN_LABEL': text}):
            root = Path(tmp)
            api = Mock()
            api.check.side_effect = lambda value: value
            api.path.return_value = 'synthetic-wrapper'
            api.k.WaitForSingleObject.return_value = 0
            child = Mock(pid=123, created=42)
            child.code.return_value = 0
            args = argparse.Namespace(sandbox=root, command=['--iso', disc],
                                      max_seconds=0, unattended=False)
            stdout = io.StringIO()
            with patch.object(runs, 'WinAPI', return_value=api), \
                 patch.object(runs, 'JobChild', return_value=child) as create, \
                 patch.object(runs, '_command_discs', set()), patch('sys.stdout', stdout):
                self.assertEqual(runs.launch(args), 0)
                self.assertIn(disc, create.call_args.args[1])
                runs.atomic_json(root/'heartbeat.json', {'note': text})
                (root/'hang.txt').write_text(runs.redact(text), encoding='utf-8')
                runs.diagnose(root, 'HUNG '+text, {})
            demo_tour.write_public(root/'plan.json', json.dumps({'note': text}), disc)
            demo_tour.capture_public(io.StringIO(text), root/'runner.log', disc)
            nested = root/'crashlogs'
            nested.mkdir()
            demo_tour.write_public(nested/'fixture.log', text, disc)
            self.assertEqual(leaks(root, (disc, other)), [])
            for secret in (disc, other):
                self.assertFalse(any(v.casefold() in stdout.getvalue().casefold()
                                     for v in variants(secret)))
            self.assertEqual(runs.read_json(root/'run.json')['command'][-1], '<disc>')

    def test_scanner_detects_nested_escaped_case_insensitive_leak(self):
        secret = r'Z:\synthetic-private\fixture.iso'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root/'crashlogs'
            nested.mkdir()
            (nested/'fixture.json').write_text(json.dumps({'note': secret.upper()}), encoding='utf-8')
            self.assertEqual(leaks(root, (secret,)), ['fixture.json'])


if __name__ == '__main__':
    unittest.main()
