import hashlib
import unittest

import install_ultimate as IU


class InstallAuditTest(unittest.TestCase):
    def test_old_moveset_without_audit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unaudited"):
            IU.verify_moveset_audit({"rows": {}}, b"[]")

    def test_stale_source_is_rejected(self):
        doc = {"audit": {"version": 1, "source_sha256": hashlib.sha256(b"old").hexdigest(),
                         "converter_sha256": IU.acmd_converter_digest()}}
        with self.assertRaisesRegex(ValueError, "stale"):
            IU.verify_moveset_audit(doc, b"new")


if __name__ == "__main__":
    unittest.main()
