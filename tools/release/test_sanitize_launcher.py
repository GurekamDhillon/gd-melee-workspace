"""The deployed Qt images must stay loadable while omitting build-user paths."""
import struct
import unittest

from sanitize_launcher import sanitize_image


def image(payload, signed=False):
    data = bytearray(512)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 0x3c, 0x80)
    data[0x80:0x84] = b'PE\0\0'
    struct.pack_into('<H', data, 0x98, 0x20b)
    if signed:
        struct.pack_into('<II', data, 0x98 + 112 + 4 * 8, 500, 12)
    return bytes(data) + payload


class SanitizerTests(unittest.TestCase):
    def test_redacts_ascii_and_wide_source_paths_without_moving_bytes(self):
        before = image(b'begin\0C:\\Users\\qt\\work\\qt\\core.cpp\0'
                       + 'C:/Users/Alice/project/window.cpp\0'.encode('utf-16le')
                       + b'end\0')
        after, count = sanitize_image(before)
        self.assertEqual(len(after), len(before))
        self.assertEqual(count, 2)
        self.assertNotIn(b'C:\\Users\\qt\\', after)
        self.assertNotIn('C:/Users/Alice/'.encode('utf-16le'), after)
        self.assertTrue(after.endswith(b'end\0'))
        self.assertIn(b'work\\qt\\core.cpp\0', after)
        self.assertIn('project/window.cpp\0'.encode('utf-16le'), after)

    def test_signed_images_are_never_modified(self):
        with self.assertRaisesRegex(ValueError, 'signed'):
            sanitize_image(image(b'C:\\Users\\qt\\private\0', signed=True))

    def test_explicit_unsigned_copy_removes_certificate_directory_and_payload(self):
        before = image(b'C:\\Users\\qt\\private\0', signed=True)
        try:
            after, count = sanitize_image(before, strip_signature=True)
        except ValueError as error:
            self.fail('explicit unsigned-copy policy still refused redaction: '+str(error))
        self.assertEqual(count, 1)
        self.assertEqual(len(after), len(before))
        self.assertEqual(after[0x98 + 112 + 4*8:0x98 + 112 + 4*8 + 8], bytes(8))
        self.assertNotIn(b'C:\\Users\\qt\\', after)

    def test_clean_images_remain_byte_identical(self):
        data = image(b'C:\\Users\\Public\\shared\0C:\\Users\\Default\\template\0')
        self.assertEqual(sanitize_image(data), (data, 0))

    def test_non_pe_input_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'PE'):
            sanitize_image(b'not an executable')


if __name__ == '__main__':
    unittest.main()
