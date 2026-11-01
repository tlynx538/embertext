"""EmberText: a small tabbed local text editor."""

import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from documents import Document, load_document, save_document
from editing import HIGHLIGHT_LIMIT, find_next, replace_all, syntax_spans


class Editor:
    def __init__(self, root):
        self.root = root
        root.title('EmberText')
        root.geometry('920x620')
        self.tabs = ttk.Notebook(root)
        self.tabs.pack(fill='both', expand=True)
        self.tabs.bind('<<NotebookTabChanged>>', lambda _: self.update_status())
        self.status = ttk.Label(root, anchor='w', padding=(8, 3))
        self.status.pack(fill='x')
        self.views = {}
        self.find_window = None
        self._menus()
        self._shortcuts()
        root.protocol('WM_DELETE_WINDOW', self.quit)
        self.new_document()

    @property
    def current(self):
        selected = self.tabs.select()
        return self.views.get(selected)

    def _menus(self):
        menu = tk.Menu(self.root)
        self.root.configure(menu=menu)
        mod = '⌘' if sys.platform == 'darwin' else 'Ctrl+'
        file_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label='File', menu=file_menu)
        for label, action, accel in (
            ('New', self.new_document, mod + 'N'),
            ('Open…', self.open_dialog, mod + 'O'),
            ('Save', self.save_current, mod + 'S'),
            ('Save As…', self.save_as, mod + 'Shift+S'),
            ('Close Tab', self.close_current, mod + 'W'),
            ('Quit', self.quit, mod + 'Q')):
            file_menu.add_command(label=label, command=action, accelerator=accel)
        edit_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label='Edit', menu=edit_menu)
        for label, action, accel in (
            ('Undo', lambda: self._edit('edit_undo'), mod + 'Z'),
            ('Redo', lambda: self._edit('edit_redo'), mod + 'Shift+Z'),
            ('Cut', lambda: self._edit('event_generate', '<<Cut>>'), mod + 'X'),
            ('Copy', lambda: self._edit('event_generate', '<<Copy>>'), mod + 'C'),
            ('Paste', lambda: self._edit('event_generate', '<<Paste>>'), mod + 'V'),
            ('Find / Replace…', self.open_find, mod + 'F')):
            edit_menu.add_command(label=label, command=action, accelerator=accel)

    def _shortcuts(self):
        modifier = 'Command' if sys.platform == 'darwin' else 'Control'
        for key, fn in (('n', self.new_document), ('o', self.open_dialog),
                        ('s', self.save_current), ('w', self.close_current),
                        ('q', self.quit), ('f', self.open_find)):
            self.root.bind_all(f'<{modifier}-{key}>', lambda event, action=fn: (action(), 'break')[1])
        self.root.bind_all(f'<{modifier}-Shift-s>', lambda _: (self.save_as(), 'break')[1])
        self.root.bind_all(f'<{modifier}-Shift-z>', lambda _: (self._edit('edit_redo'), 'break')[1])
        # Tk Text provides native Cmd/Ctrl undo, redo and clipboard bindings.

    def _edit(self, method, *args):
        if self.current:
            try:
                getattr(self.current.text, method)(*args)
            except tk.TclError:
                pass

    def new_document(self):
        self._add_tab(Document())

    def _add_tab(self, document):
        frame = ttk.Frame(self.tabs)
        gutter = tk.Canvas(frame, width=45, background='#eeeeee', highlightthickness=0)
        gutter.pack(side='left', fill='y')
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side='right', fill='y')
        text = tk.Text(frame, undo=True, maxundo=-1, wrap='none', font=('TkFixedFont', 12),
                       tabs=('32',), padx=5)
        text.pack(side='left', fill='both', expand=True)
        view = TabView(document, frame, text, gutter)
        text.tag_configure('keyword', foreground='#7540a4')
        text.tag_configure('string', foreground='#a64528')
        text.tag_configure('comment', foreground='#677b67')
        def on_scroll(first, last):
            scrollbar.set(first, last)
            self._draw_lines(view)
        text.configure(yscrollcommand=on_scroll)
        scrollbar.configure(command=lambda *args: (text.yview(*args), self._draw_lines(view)))
        text.insert('1.0', document.text)
        text.edit_reset()
        text.edit_modified(False)
        text.bind('<<Modified>>', lambda _: self._changed(view))
        text.bind('<KeyRelease>', lambda _: self.update_status())
        text.bind('<ButtonRelease-1>', lambda _: self.update_status())
        text.bind('<Configure>', lambda _: self._draw_lines(view))
        self.tabs.add(frame)
        self.views[str(frame)] = view
        self.tabs.select(frame)
        self._title(view)
        self.update_status()
        text.focus_set()
        self._schedule_highlight(view)
        return view

    def _changed(self, view):
        if not view.text.edit_modified():
            return
        view.text.edit_modified(False)
        view.document.text = view.text.get('1.0', 'end-1c')
        self._title(view)
        self.update_status()
        self._draw_lines(view)
        self._schedule_highlight(view)

    def _title(self, view):
        name = view.document.path.name if view.document.path else 'Untitled'
        self.tabs.tab(view.frame, text=('* ' if view.document.dirty else '') + name)
        if view is self.current:
            self.root.title(f'{name}{" *" if view.document.dirty else ""} — EmberText')

    def update_status(self):
        view = self.current
        if not view:
            return
        line, col = view.text.index('insert').split('.')
        name = str(view.document.path) if view.document.path else 'Untitled'
        note = ' (highlight off: large file)' if len(view.document.text) > HIGHLIGHT_LIMIT else ''
        self.status.configure(text=f'{name}    Ln {line}, Col {int(col) + 1}    UTF-8{note}')
        self._title(view)

    def _draw_lines(self, view):
        canvas = view.gutter
        canvas.delete('all')
        index = view.text.index('@0,0')
        while True:
            info = view.text.dlineinfo(index)
            if info is None:
                break
            y = info[1]
            canvas.create_text(39, y + 2, text=index.split('.')[0], anchor='ne', fill='#666666',
                               font=('TkFixedFont', 10))
            next_index = view.text.index(f'{index}+1line')
            if next_index == index:
                break
            index = next_index

    def _schedule_highlight(self, view):
        if view.highlight_job:
            self.root.after_cancel(view.highlight_job)
        view.highlight_job = self.root.after(220, lambda: self._highlight(view))

    def _highlight(self, view):
        view.highlight_job = None
        if not view.text.winfo_exists():
            return
        for tag in ('keyword', 'string', 'comment'):
            view.text.tag_remove(tag, '1.0', 'end')
        suffix = view.document.path.suffix if view.document.path else ''
        for tag, start, end in syntax_spans(view.document.text, suffix):
            view.text.tag_add(tag, f'1.0+{start}c', f'1.0+{end}c')

    def open_dialog(self):
        path = filedialog.askopenfilename(parent=self.root, title='Open text file',
                                          filetypes=[('All files', '*')])
        if path:
            self.open_path(path)

    def open_path(self, path):
        path = Path(path)
        for view in self.views.values():
            if view.document.path and view.document.path.resolve() == path.resolve():
                self.tabs.select(view.frame)
                view.text.focus_set()
                return True
        try:
            document = load_document(path)
        except (OSError, UnicodeError, ValueError) as error:
            messagebox.showerror('Could not open file', str(error), parent=self.root)
            return False
        self._add_tab(document)
        return True

    def save_current(self):
        view = self.current
        if not view:
            return False
        return self._save(view)

    def save_as(self):
        view = self.current
        if view:
            return self._save(view, choose=True)
        return False

    def _save(self, view, choose=False):
        # A dialog or window close can happen before Tk delivers <<Modified>>.
        self._changed(view)
        path = view.document.path
        if choose or path is None:
            chosen = filedialog.asksaveasfilename(parent=self.root, title='Save text file',
                                                  initialfile=path.name if path else '',
                                                  filetypes=[('All files', '*')])
            if not chosen:
                return False
            path = Path(chosen)
            if any(other is not view and other.document.path and
                   other.document.path.resolve() == path.resolve()
                   for other in self.views.values()):
                messagebox.showerror('Already open', 'That file is open in another tab.', parent=self.root)
                return False
        try:
            save_document(view.document, path)
        except (OSError, UnicodeError, ValueError) as error:
            messagebox.showerror('Could not save file', str(error), parent=self.root)
            return False
        self._title(view)
        self.update_status()
        self._schedule_highlight(view)
        return True

    def _may_close(self, view):
        self._changed(view)
        if not view.document.dirty:
            return True
        name = view.document.path.name if view.document.path else 'Untitled'
        answer = messagebox.askyesnocancel('Unsaved changes', f'Save changes to {name}?',
                                           parent=self.root)
        if answer is None:
            return False
        return not answer or self._save(view)

    def close_current(self):
        view = self.current
        if not view or not self._may_close(view):
            return False
        if view.highlight_job:
            self.root.after_cancel(view.highlight_job)
        self.views.pop(str(view.frame))
        self.tabs.forget(view.frame)
        view.frame.destroy()
        if not self.views:
            self.new_document()
        self.update_status()
        return True

    def quit(self):
        for view in list(self.views.values()):
            self.tabs.select(view.frame)
            if not self._may_close(view):
                return False
        self.root.destroy()
        return True

    def open_find(self):
        if self.find_window and self.find_window.winfo_exists():
            self.find_window.lift()
            self.find_entry.focus_set()
            return
        window = tk.Toplevel(self.root)
        window.title('Find and Replace')
        window.resizable(False, False)
        self.find_window = window
        def close_find():
            self.find_window = None
            window.destroy()
        window.protocol('WM_DELETE_WINDOW', close_find)
        window.bind('<Escape>', lambda _: close_find())
        ttk.Label(window, text='Find').grid(row=0, column=0, padx=8, pady=5)
        self.find_entry = ttk.Entry(window, width=32)
        self.find_entry.grid(row=0, column=1, padx=8)
        ttk.Label(window, text='Replace').grid(row=1, column=0, padx=8, pady=5)
        self.replace_entry = ttk.Entry(window, width=32)
        self.replace_entry.grid(row=1, column=1, padx=8)
        ttk.Button(window, text='Find Next', command=self.find_match).grid(row=2, column=0, padx=8, pady=8)
        ttk.Button(window, text='Replace', command=self.replace_match).grid(row=2, column=1, sticky='w')
        ttk.Button(window, text='Replace All', command=self.replace_all_matches).grid(row=2, column=1, sticky='e', padx=8)
        self.find_feedback = ttk.Label(window, text='', anchor='w')
        self.find_feedback.grid(row=3, column=0, columnspan=2, sticky='ew', padx=8, pady=5)
        self.find_entry.bind('<Return>', lambda _: self.find_match())
        self.find_entry.focus_set()

    def find_match(self):
        view = self.current
        if not view:
            return False
        self._changed(view)
        needle = self.find_entry.get()
        start = int(view.text.count('1.0', 'insert', 'chars')[0])
        selection = view.text.tag_ranges('sel')
        if selection:
            start = int(view.text.count('1.0', selection[1], 'chars')[0])
        found = find_next(view.document.text, needle, start)
        if not found:
            self.find_feedback.configure(text='No matches' if needle else 'Enter text to find')
            return False
        first, last = (f'1.0+{pos}c' for pos in found)
        view.text.tag_remove('sel', '1.0', 'end')
        view.text.tag_add('sel', first, last)
        view.text.mark_set('insert', first)
        view.text.see(first)
        self.find_feedback.configure(text='Match found')
        self.update_status()
        return True

    def replace_match(self):
        view = self.current
        needle = self.find_entry.get()
        if not view or not needle:
            return
        selection = view.text.tag_ranges('sel')
        if not selection or view.text.get(*selection).casefold() != needle.casefold():
            self.find_match()
            return
        view.text.edit_separator()
        view.text.replace(selection[0], selection[1], self.replace_entry.get())
        view.text.edit_separator()
        self.find_feedback.configure(text='Replaced 1 match')

    def replace_all_matches(self):
        view = self.current
        if not view:
            return
        self._changed(view)
        result, count = replace_all(view.document.text, self.find_entry.get(), self.replace_entry.get())
        if count:
            view.text.edit_separator()
            view.text.replace('1.0', 'end-1c', result)
            view.text.edit_separator()
            # Keep the model synchronized without waiting for the event loop.
            self._changed(view)
        self.find_feedback.configure(text=f'Replaced {count} match(es)' if count else 'No matches')


class TabView:
    def __init__(self, document, frame, text, gutter):
        self.document = document
        self.frame = frame
        self.text = text
        self.gutter = gutter
        self.highlight_job = None


if __name__ == '__main__':
    Editor(tk.Tk()).root.mainloop()
