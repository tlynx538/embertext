import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from editor import Editor


class EditorJourneys(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = Editor(self.root)

    def tearDown(self):
        self.root.destroy()

    def test_new_edit_save_as_arbitrary_suffix_and_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'journal.custom'
            self.app.current.text.insert('1.0', 'draft')
            self.app.root.update()
            self.assertTrue(self.app.current.document.dirty)
            with patch('editor.filedialog.asksaveasfilename', return_value=str(path)):
                self.assertTrue(self.app.save_current())
            self.assertEqual(path.read_text(), 'draft')
            self.assertFalse(self.app.current.document.dirty)
            self.assertTrue(self.app.open_path(path))
            self.assertEqual(self.app.current.text.get('1.0', 'end-1c'), 'draft')

    def test_cancel_close_retains_tab_and_edits(self):
        self.app.current.text.insert('1.0', 'keep me')
        self.app.root.update()
        with patch('editor.messagebox.askyesnocancel', return_value=None):
            self.assertFalse(self.app.close_current())
        self.assertEqual(self.app.current.text.get('1.0', 'end-1c'), 'keep me')
        self.assertEqual(len(self.app.tabs.tabs()), 1)

    def test_failed_save_does_not_close_or_clear_dirty(self):
        self.app.current.text.insert('1.0', 'keep me')
        self.app.root.update()
        with patch('editor.filedialog.asksaveasfilename', return_value='/not-present/sub/file.txt'), \
                patch('editor.messagebox.showerror'):
            self.assertFalse(self.app.save_current())
            with patch('editor.messagebox.askyesnocancel', return_value=True):
                self.assertFalse(self.app.close_current())
        self.assertTrue(self.app.current.document.dirty)
        self.assertEqual(len(self.app.tabs.tabs()), 1)

    def test_failed_open_keeps_current_edit(self):
        self.app.current.text.insert('1.0', 'unfinished')
        self.app.root.update()
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / 'broken.any'
            bad.write_bytes(b'\xff')
            with patch('editor.messagebox.showerror'):
                self.assertFalse(self.app.open_path(bad))
        self.assertEqual(self.app.current.text.get('1.0', 'end-1c'), 'unfinished')
        self.assertTrue(self.app.current.document.dirty)
        self.assertEqual(len(self.app.tabs.tabs()), 1)

    def test_cancel_save_as_keeps_dirty_tab_and_quit_is_cancellable(self):
        self.app.current.text.insert('1.0', 'unfinished')
        with patch('editor.filedialog.asksaveasfilename', return_value=''):
            self.assertFalse(self.app.save_current())
        with patch('editor.messagebox.askyesnocancel', return_value=None):
            self.assertFalse(self.app.quit())
        self.assertTrue(self.app.root.winfo_exists())
        self.assertTrue(self.app.current.document.dirty)

    def test_find_replace_and_undo(self):
        self.app.current.text.insert('1.0', 'one ONE')
        self.app.open_find()
        self.app.find_entry.insert(0, 'one')
        self.app.replace_entry.insert(0, 'two')
        self.app.replace_all_matches()
        self.assertEqual(self.app.current.text.get('1.0', 'end-1c'), 'two two')
        self.app.current.text.edit_undo()
        self.assertEqual(self.app.current.text.get('1.0', 'end-1c'), 'one ONE')

    def test_find_after_emoji_selects_expected_text_and_wraps(self):
        self.app.current.text.insert('1.0', '😀 find and find')
        self.app.open_find()
        self.app.find_entry.insert(0, 'find')
        self.assertTrue(self.app.find_match())
        self.assertEqual(self.app.current.text.get('sel.first', 'sel.last'), 'find')
        self.assertEqual(self.app.current.text.index('sel.first'), '1.3')
        self.assertTrue(self.app.find_match())
        self.assertEqual(self.app.current.text.index('sel.first'), '1.12')

    def test_symlink_save_error_keeps_alias_and_dirty_tab(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'target.txt'
            alias = Path(directory) / 'alias.txt'
            target.write_text('before')
            alias.symlink_to(target)
            self.assertTrue(self.app.open_path(alias))
            self.app.current.text.insert('end-1c', ' after')
            with patch('editor.messagebox.showerror') as error:
                self.assertFalse(self.app.save_current())
                self.assertIn('symbolic link', error.call_args.args[1])
            self.assertTrue(alias.is_symlink())
            self.assertEqual(target.read_text(), 'before')
            self.assertTrue(self.app.current.document.dirty)

    def test_find_dialog_escape_closes_and_can_reopen(self):
        self.app.open_find()
        previous = self.app.find_window
        self.root.deiconify()
        self.root.update()
        previous.focus_force()
        previous.event_generate('<Escape>')
        self.root.update()
        self.assertFalse(previous.winfo_exists())
        self.app.open_find()
        self.assertTrue(self.app.find_window.winfo_exists())


if __name__ == '__main__':
    unittest.main()
