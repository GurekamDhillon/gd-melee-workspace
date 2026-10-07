import contextlib
import io
from http.client import IncompleteRead
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import URLError

import jev


class ClientTests(unittest.TestCase):
    def test_offline_never_contacts_network_and_is_deterministic(self):
        q = {"impact": {"type": "score", "instructions": "Rate impact", "criteria": ["cosmetic", "wrong result", "stuck player", "online desync", "crash/data loss"]}}
        with patch("jev.urlopen", side_effect=AssertionError("network used")):
            a = jev.call({"finding": "Crash when saving"}, q, offline=True)
            self.assertEqual(a, jev.call({"finding": "Crash when saving"}, q, offline=True))
        self.assertEqual(a["impact"]["score"], 4)
        self.assertEqual(a["impact"]["source"], "stub")

    def test_missing_key_degrades_without_exception_details(self):
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertIsNone(jev.call("text", {"q": {"type": "noul", "instructions": "yes?"}}))
        self.assertEqual(err.getvalue().strip(), "jev: unavailable")

    def test_network_failure_retries_once_and_hides_errors(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "test-only"}), patch("jev.urlopen", side_effect=URLError("private detail")) as transport, patch("jev.time.sleep"), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertIsNone(jev.call("text", {"q": {"type": "noul", "instructions": "yes?"}}))
        self.assertEqual(transport.call_count, 2)
        self.assertEqual(err.getvalue().strip(), "jev: unavailable")

    def test_truncated_http_response_retries_then_degrades(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "test-only"}), patch("jev.urlopen", side_effect=IncompleteRead(b"", 10)) as transport, patch("jev.time.sleep"), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertIsNone(jev.call("text", {"q": {"type": "noul", "instructions": "yes?"}}))
        self.assertEqual(transport.call_count, 2)
        self.assertEqual(err.getvalue().strip(), "jev: unavailable")

    def test_redacts_user_paths_credentials_and_disc_assignments(self):
        text = 'at "C:\\Users\\Someone\\My Game\\main.c" and /home/person/game/log\nAuthorization: Bearer fake-token\nTYPESAFE_API_KEY=fake-key\nGW_ISO_ACE=private-disc\n'
        clean = jev.sanitize(text)
        for private in ("Someone", "person", "fake-token", "fake-key", "private-disc"):
            self.assertNotIn(private, clean)

    def test_malformed_answer_is_unavailable(self):
        response = io.BytesIO(json.dumps({"answers": {"q": {"type": "noul", "noul": 3}}}).encode())
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "test-only"}), patch("jev.urlopen", return_value=response), contextlib.redirect_stderr(io.StringIO()):
            self.assertIsNone(jev.call("text", {"q": {"type": "noul", "instructions": "yes?"}}))

    def test_invalid_probability_structure_is_unavailable(self):
        response = io.BytesIO(json.dumps({"answers": {"q": {"type": "choice", "choice": "a", "confidence": 1, "probabilities": ["a", "b"]}}}).encode())
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "test-only"}), patch("jev.urlopen", return_value=response), contextlib.redirect_stderr(io.StringIO()):
            self.assertIsNone(jev.call("text", {"q": {"type": "choice", "instructions": "choose", "criteria": {"a": None, "b": None}}}))
