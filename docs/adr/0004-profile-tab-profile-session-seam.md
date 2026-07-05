# ProfileSession fronts profile persistence for the profile editor

`profile_tab.py` and `profile_editor.py` both talked directly to `ProfileDocumentStore`
and `IniConfigLoader`, and `ProfileEditor.save_all()` also owned validation, the
"model differs after validation" warning dialog, and success/error dialogs. We
introduced a `ProfileSession` module that owns discovery, load, save (validate +
persist), and dirty-checking behind one interface, returning result types
(`Loaded`/`YamlError`/`EmptyError`/`ValidationError`, `Saved`/`ValidationDiffers`/`Failed`)
instead of raising. `ProfileEditor` no longer touches `ProfileDocumentStore` or shows
any dialogs — it only exposes `get_current_model()`. `ProfileTab` owns every dialog
(warning, info, error, close-confirmation) and decides whether to retry a save with
`force=True` after the user confirms. Last-opened-profile persistence goes through an
injected `ProfileLastOpenedStore` protocol instead of `QSettings` directly, so
`ProfileSession` has no PyQt imports and is testable without Qt widgets.

We considered leaving `ProfileEditor.save_all()` in place and only wrapping
`profile_tab.py`'s existing calls, but that would have left the real persistence
duplicated across two files and the "differs after validation" dialog stuck inside
the editor rather than under one narrow seam.
