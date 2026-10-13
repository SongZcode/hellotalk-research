from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import apk_inventory
import dex_strings
import ht_frame as frame


class FrameTests(unittest.TestCase):
    def make(self, value, compressed=True, magic=frame.MAGIC_UP):
        return frame.pack_json(frame.build_opcode(0x17, 1), 0, value, compress=compressed, magic=magic)

    def test_round_trip_and_true_length_field(self):
        for compressed in (True, False):
            for magic in (frame.MAGIC_UP, frame.MAGIC_DN, frame.MAGIC_PUSH):
                raw=self.make({'text':'synthetic','url':'https://example.invalid/test'},compressed,magic)
                result=frame.parse(raw)
                self.assertEqual(result['body_len'],len(raw)-20)
                self.assertEqual(result['body']['text'],'synthetic')
                self.assertNotIn('hdr_len',result)

    def test_short_json_and_empty_binary_control_frame(self):
        raw=self.make({},False)
        self.assertEqual(len(raw),22)
        self.assertEqual(frame.parse(raw)['body'],{})
        raw=frame.pack(frame.MAGIC_DN,b'\0'*4,0,b'')
        self.assertEqual(frame.parse(raw)['body_len'],0)

    def test_short_header(self):
        self.assertEqual(frame.parse(b'\0'*19)['error'],'too short')

    def test_mismatched_declared_length(self):
        raw=bytearray(self.make({'text':'synthetic'}))
        struct.pack_into('<I',raw,16,1)
        self.assertEqual(frame.parse(bytes(raw))['error'],'body length mismatch')

    def test_unknown_magic(self):
        raw=self.make({'text':'synthetic'})
        self.assertEqual(frame.parse(b'bad!'+raw[4:])['error'],'unknown magic')

    def test_compression_expansion_limit(self):
        raw=self.make({'text':'x'*10000})
        self.assertIn('exceeds limit',frame.parse(raw,max_body_bytes=1000)['inflate_error'])

    def test_truncated_and_trailing_compressed_streams(self):
        body=zlib.compress(b'{"synthetic":true}')
        for value in (body[:-1],body+b'extra'):
            raw=frame.pack(frame.MAGIC_UP,b'\0'*4,0,value)
            self.assertIn('inflate_error',frame.parse(raw))

    def test_uncompressed_limit_and_invalid_limit(self):
        self.assertEqual(frame.parse(self.make({'text':'x'*200},False),max_body_bytes=100)['error'],'body exceeds limit')
        with self.assertRaises(ValueError): frame.parse(b'',max_body_bytes=0)


class ApkTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.apk=Path(self.temp.name)/'synthetic.apk'
        with zipfile.ZipFile(self.apk,'w') as archive:
            archive.writestr('AndroidManifest.xml','synthetic')
            archive.writestr('classes.dex',b'\0/member_privilege_center\0/example_api\0')
            archive.writestr('classes2.dex',b'\0/second_example_api\0')
            archive.writestr('assets/readme.txt','synthetic')
            archive.writestr('lib/arm64-v8a/libsample.so','synthetic')
            archive.writestr('lib/x86/libsample.so','synthetic')

    def test_inventory_counts_without_extraction(self):
        result=apk_inventory.inventory(self.apk)
        self.assertTrue(result['android_manifest'])
        self.assertEqual(len(result['dex']),2)
        self.assertEqual(result['abi'],{'arm64-v8a':1,'x86':1})
        self.assertEqual(result['asset_entries'],1)
        self.assertEqual(list(Path(self.temp.name).iterdir()),[self.apk])

    def test_inventory_command_json(self):
        output=io.StringIO()
        with redirect_stdout(output): self.assertEqual(apk_inventory.main([str(self.apk)]),0)
        self.assertEqual(json.loads(output.getvalue())['native_libraries'],2)

    def test_ascii_search_with_explicit_path(self):
        output=io.StringIO()
        with redirect_stdout(output): self.assertEqual(dex_strings.main(['--apk',str(self.apk),'example_api']),0)
        self.assertIn('/example_api',output.getvalue())
        self.assertIn('/second_example_api',output.getvalue())

    def test_default_search_keys(self):
        output=io.StringIO()
        with redirect_stdout(output): dex_strings.main(['--apk',str(self.apk)])
        self.assertIn('/member_privilege_center',output.getvalue())

    def test_missing_file_reports_error(self):
        with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                apk_inventory.main([str(self.apk.parent/'missing.apk')])
        self.assertEqual(error.exception.code,2)

    def test_invalid_zip_reports_error(self):
        self.apk.write_bytes(b'not a zip')
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit): apk_inventory.main([str(self.apk)])


if __name__ == '__main__':
    unittest.main()
