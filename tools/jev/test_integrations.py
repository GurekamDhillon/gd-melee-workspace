import importlib.util
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IntegrationTests(unittest.TestCase):
    def test_standalone_upload_without_repo_layout_still_stores(self):
        server = load("standalone_upload", ROOT / "tools/release/crash_upload_server.py")
        body = b"==== GD's Melee crash report ====\nreason: synthetic\n"
        with tempfile.TemporaryDirectory() as directory, patch.object(server, "__file__", "/crash_upload_server.py"), self.assertLogs(server.log, level="WARNING"):
            server.store(directory, body, jev_enabled=True, offline=True)
            meta = json.loads(next(Path(directory).rglob("*.json")).read_text())
            self.assertEqual(meta["triage"]["source"], "unavailable")

    def test_opt_in_upload_http_path_persists_triage(self):
        server_module = load("upload_http", ROOT / "tools/release/crash_upload_server.py")

        async def exercise(directory):
            server = await server_module.start_crash_upload("127.0.0.1", 0, directory, jev_enabled=True, offline=True)
            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", server.sockets[0].getsockname()[1])
                body = b"==== GD's Melee crash report ====\nreason: FATAL synthetic\n"
                writer.write(b"POST /crash HTTP/1.1\r\nHost: localhost\r\nContent-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body)
                await writer.drain()
                response = await reader.read()
                writer.close()
                await writer.wait_closed()
                self.assertIn(b"200 OK", response)
                meta = json.loads(next(Path(directory).rglob("*.json")).read_text())
                self.assertEqual(meta["triage"]["source"], "stub")
            finally:
                server.close()
                await server.wait_closed()

        with tempfile.TemporaryDirectory() as directory:
            asyncio.run(exercise(directory))

    def test_sweep_opt_in_adds_triage_without_altering_result(self):
        sweep = load("sweep", ROOT / "tools/sweep/crash_sweep.py")
        with tempfile.TemporaryDirectory() as directory:
            run = sweep.Run("vanilla", "stage", "vanilla-st-icetop", "stage=icetop", 0, "icetop")
            run.result, run.detail = "CRASH", "FATAL BGM"
            sweep.write_results([run], directory, "fixture.exe", ["vanilla"], 0, jev_enabled=True, offline=True)
            rows = json.loads((Path(directory) / "results.json").read_text())
            self.assertEqual(rows[0]["result"], "CRASH")
            self.assertEqual(rows[0]["triage"]["choice"], "known_issue")
            self.assertIn("| triage |", (Path(directory) / "results.md").read_text())
            sweep.write_results([run], directory, "fixture.exe", ["vanilla"], 0)
            self.assertNotIn("triage", json.loads((Path(directory) / "results.json").read_text())[0])

    def test_upload_default_does_not_use_jev_and_opt_in_stores_stub(self):
        server = load("upload", ROOT / "tools/release/crash_upload_server.py")
        body = b"==== GD's Melee crash report ====\nreason: FATAL access violation\n"
        with tempfile.TemporaryDirectory() as directory:
            with patch("jev.urlopen", side_effect=AssertionError("network used")):
                server.store(directory, body)
                metadata = json.loads(next(Path(directory).rglob("*.json")).read_text())
                self.assertNotIn("triage", metadata)
                server.store(directory, body, jev_enabled=True, offline=True)
            metadata = json.loads(next(Path(directory).rglob("*.json")).read_text())
            self.assertEqual(metadata["triage"]["choice"], "real_bug")
            self.assertEqual(metadata["triage"]["source"], "stub")
