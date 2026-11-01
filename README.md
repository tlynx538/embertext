# EmberText

A small, graphical, tabbed text editor built with Python's standard-library Tkinter. No packages or account required.

## Built by OpenCode agents

EmberText was created from an empty repository by the
[OpenCode Programming Workflow](https://github.com/tlynx538/OpenCode-Programming-Workflow).
The human supplied the idea and answered clarification questions; OpenCode agents
wrote the application, file-handling model, editing helpers, tests and initial
README. This later Codex publishing pass added provenance documentation and Git
ignore rules; it did not change the application implementation.

The build used the workflow's **Poseidon-led native configuration**:

| Agent | Contribution |
| --- | --- |
| Poseidon | Clarified graphical desktop delivery, filename extensions and lightweight scope; carried the answers into implementation and challenged unsupported review findings. |
| Researcher | Investigated scope ambiguities and surfaced cancellation and file-failure paths. |
| Team Lead | Planned the primary open/create → edit → save journey and acceptance checks. |
| Maintainer | Assessed Tk feasibility, file formats and failure-safe local writes. |
| Coder | Implemented the editor and tests, then revised symlink handling, highlighting and Find-dialog behavior. |
| Reviewer | Inspected implementation and revisions; its disputed claims prompted targeted fact checks. |

The user selected a desktop GUI, accepted cross-platform intent with a lightweight
preference, and confirmed that extensions meant filename suffixes rather than
plugins. The result uses standard-library Tkinter instead of a browser framework.
The user reported a positive result. The newer Team Lead-led contract bundle and
later evidence-v3 prompts are separate iterations; they did not produce this build.

The agent's final run recorded 20 passing tests, including real Tk widget flows
with mocked dialog choices. Those cover saving arbitrary suffixes, cancellation,
failed reads/writes, find/replace and undo. Visual inspection, a complete manual
keyboard walkthrough, and Windows/Linux validation were not performed. See the
[session assessment](https://github.com/tlynx538/OpenCode-Programming-Workflow/blob/main/docs/usage-reviews/2026-11-01-embertext-session-reflection.md)
for evidence and the limitations of the review.

## Run

Install Python 3.10 or newer with Tk support, then run from this directory:

```sh
python3 editor.py
```

On Linux, your Python installation may require a separate `python3-tk` system package. A desktop display is required. Tested on macOS with Python 3.13 and Tk 8.6; other platforms have not been verified.

## Use

File → New/Open/Save/Save As/Close Tab/Quit; Edit → Undo/Redo/Cut/Copy/Paste/Find and Replace. Shortcuts use **⌘** on macOS and **Ctrl** elsewhere: N, O, S, Shift+S, W, Q, F; Undo is Z and Redo is Shift+Z. In Find and Replace, Find Next wraps around; searches and replacements are literal and case-insensitive. An empty search does not replace anything. Unsaved tabs display an asterisk. Closing or quitting prompts **Save / Discard / Cancel** for every dirty tab; cancelling a dialog or failing to save leaves the tab and edits intact.

Files with any extension can be opened and saved. `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, and `.json` get simple syntax colors; other extensions remain plain text. Coloring is disabled for text longer than 200,000 characters to keep editing responsive. Files over 8,000,000 bytes are refused with an error rather than freezing the editor. Text is strictly UTF-8: invalid UTF-8 is reported, not silently replaced. The original UTF-8 BOM and first newline style (LF, CRLF, or CR) are preserved on save; **mixed newline styles are normalized to the first style**. File writes use a temporary sibling followed by atomic replacement where supported by the filesystem. The original file is left in place if writing fails before replacement. Saving through a symbolic link is refused rather than replacing the link; open and save its target path instead. External changes to an open file are not detected; reopening an already-open path selects the existing tab. Windows file-attribute and permission behavior has not been validated.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

The UI tests create hidden Tk windows and require a working graphical desktop session.

## Known issue

Find Next can raise a `TypeError` when the insertion cursor is at the beginning
of a document, including an empty tab. A post-session check reproduced this zero-offset
case, which the existing tests do not cover. The publication preserves the original
agent-built implementation; this issue is documented rather than claimed fixed.
