import subprocess
import unittest
from unittest.mock import patch
import mirror


class MirrorTests(unittest.TestCase):
    def test_version_boundary_and_variants(self):
        for tag in ['7.0.0', '25.6.0', '26.09.29']:
            self.assertTrue(mirror.versioned(tag), tag)
        for tag in ['4.168-latest', '6.99.99', 'beta', 'beta-resolute', '26.06.05-resolute', 'latest', '26', '26.1', '26.1.1/unsafe']:
            self.assertFalse(mirror.versioned(tag), tag)

    @patch('mirror.run')
    def test_cached_image_never_contacts_upstream(self, run):
        run.return_value = b'{}'
        mirror.mirror('docker.io/example:25.6.0', 'ghcr.io/example:25.6.0')
        run.assert_called_once_with('inspect', '--raw', 'docker://ghcr.io/example:25.6.0')

    def test_only_missing_manifests_are_cache_misses(self):
        for message, missing in [(b'manifest unknown', True), (b'name unknown', True),
                                 (b'unauthorized', False), (b'timeout', False), (b'toomanyrequests', False)]:
            error = subprocess.CalledProcessError(1, 'skopeo', stderr=message)
            with self.subTest(message=message), patch('mirror.run', side_effect=error):
                if missing:
                    self.assertFalse(mirror.exists('ghcr.io/example:25.6.0'))
                else:
                    with self.assertRaises(subprocess.CalledProcessError):
                        mirror.exists('ghcr.io/example:25.6.0')

    @patch('mirror.exists', return_value=False)
    @patch('mirror.run')
    def test_copy_pins_source_and_preserves_manifest(self, run, exists):
        run.side_effect = [b'{}', b'', b'{}']
        mirror.mirror('docker.io/example:25.6.0', 'ghcr.io/example:25.6.0')
        copy = run.call_args_list[1].args
        self.assertEqual(copy[:6], ('copy', '--all', '--preserve-digests', '--retry-times', '3',
                         'docker://docker.io/example@sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a'))

    @patch('mirror.exists', return_value=False)
    @patch('mirror.run', side_effect=[b'{}', b'', b'{"different":true}'])
    def test_digest_mismatch_fails(self, run, exists):
        with self.assertRaisesRegex(RuntimeError, 'digest mismatch'):
            mirror.mirror('docker.io/example:25.6.0', 'ghcr.io/example:25.6.0')
