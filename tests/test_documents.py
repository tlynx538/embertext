import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from documents import Document, load_document, save_document


class DocumentTests(unittest.TestCase):
    def test_arbitrary_suffix_and_dirty_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'notes.unknown-extension'
            doc = Document(text='hello')
            doc.text = 'hello world'
            self.assertTrue(doc.dirty)
            save_document(doc, path)
            self.assertEqual(path.read_bytes(), b'hello world')
            self.assertEqual(doc.path, path)
            self.assertFalse(doc.dirty)
            doc.text = 'hello'
            self.assertTrue(doc.dirty)

    def test_utf8_bom_and_crlf_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'data.xyz'
            path.write_bytes(b'\xef\xbb\xbfA\r\nB\r\n')
            doc = load_document(path)
            self.assertEqual(doc.text, 'A\nB\n')
            self.assertFalse(doc.dirty)
            doc.text += 'C\n'
            save_document(doc)
            self.assertEqual(path.read_bytes(), b'\xef\xbb\xbfA\r\nB\r\nC\r\n')

    def test_invalid_utf8_does_not_return_document(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.txt'
            path.write_bytes(b'good\xffbad')
            with self.assertRaises(UnicodeDecodeError):
                load_document(path)

    def test_failed_replace_keeps_file_and_dirty_document(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'file.cfg'
            path.write_text('original')
            doc = load_document(path)
            doc.text = 'changed'
            with patch('documents.os.replace', side_effect=OSError('write failed')):
                with self.assertRaises(OSError):
                    save_document(doc)
            self.assertEqual(path.read_text(), 'original')
            self.assertEqual(doc.text, 'changed')
            self.assertTrue(doc.dirty)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_failed_save_as_does_not_change_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'old.txt'
            path.write_text('one')
            doc = load_document(path)
            doc.text = 'two'
            with self.assertRaises(OSError):
                save_document(doc, Path(directory) / 'absent' / 'new.anything')
            self.assertEqual(doc.path, path)
            self.assertTrue(doc.dirty)
            self.assertEqual(path.read_text(), 'one')

    def test_symlink_save_refused_without_changing_alias_target_or_dirty_state(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'original.txt'
            alias = Path(directory) / 'alias.txt'
            target.write_text('before')
            alias.symlink_to(target)
            doc = load_document(alias)
            doc.text = 'after'
            with self.assertRaisesRegex(ValueError, 'symbolic link'):
                save_document(doc)
            self.assertTrue(alias.is_symlink())
            self.assertEqual(target.read_text(), 'before')
            self.assertEqual(doc.path, alias)
            self.assertTrue(doc.dirty)


if __name__ == '__main__':
    unittest.main()
