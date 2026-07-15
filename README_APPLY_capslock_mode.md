# Applying the capslock_mode changes

Extract the TGZ from the repo root and every file lands at its
repo-relative path directly:
    tar xzf toshy_capslock_mode.tgz

MODIFIED (replaces existing files - review diffs in VSCode Source
Control before committing):

    default-toshy-config/toshy_config.py
    toshy_common/settings_class.py
    toshy_gui/gui/settings_panel_gtk4.py
    toshy_gui/main_tkinter.py
    toshy_tray.py
    scripts/toshy_versions.py     (new module added to version inventory)
    setup_toshy.py                ('tests' added to install ignore patterns)

NEW (no existing counterparts):

    toshy_common/modifier_modes.py
    tests/__init__.py
    tests/modmap_verifier_rgx.py
    tests/modmap_verifier_harness.py
    tests/test_modmap_integrity.py
    tests/test_modmap_hygiene.py
    tests/modmap_matrix_report.py

CAUTION: these were built against dev_beta HEAD (c6ad246). If you have
uncommitted local edits in any of the five modified files - e.g. your
own CapsLock addition to the Trigger Modmap - copying will overwrite
them. The trigger-modmap Caps entry is already included here, so that
particular local edit is safe to lose. Anything else: check the VSCode
diff before replacing, or set the file aside and reconcile by hand.

Run the verifier (repo root):

    python3 tests/test_modmap_integrity.py
    python3 tests/test_modmap_hygiene.py
    python3 tests/modmap_matrix_report.py      # prints the behavior matrix

Requires xwaykeyz importable (e.g. run with the Toshy venv's python).
