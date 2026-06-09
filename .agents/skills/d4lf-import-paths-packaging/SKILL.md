______________________________________________________________________

## name: d4lf-import-paths-packaging description: Fix d4lf import-path, module-resolution, and packaging issues. Use for ModuleNotFoundError, wrong package-relative imports, `python -m` versus file execution differences, uv/venv path issues, and startup path regressions.

1. Identify how the app is being launched and whether the import model expects package execution.
1. Inspect absolute imports, relative imports, top-level package names, and current working directory assumptions.
1. Prefer one consistent import style that matches the repository's startup method.
1. Avoid local path hacks unless absolutely necessary.
1. When changing imports, inspect downstream imports and startup commands together.
1. In the summary, state which invocation style the fix supports and whether alternative launch styles remain unsupported.
