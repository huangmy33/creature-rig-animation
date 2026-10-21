# Agent development guide

This is a local Python/Blender/Node.js toolkit, not a hosted service.

- Read README.md and the relevant reference before changing the asset pipeline.
- Keep user models, private paths, credentials and runtime outputs out of commits.
- Use a fresh directory under temp_data for generated assets; do not delete or overwrite a user's model to make a test pass.
- Python utilities run in a virtual environment; `*_blender.py` runs through Blender.
- Include `--disable-autoexec --python-exit-code 1` for Blender jobs.
- Run `python -m unittest discover -s tests -v` for every code change.
- For rigging, motion, export or validation changes run `python examples/run_demo.py --output-dir temp_data/check-N --render` with a new directory.
- Read every stage's logs. Validator errors/warnings must not be hidden or waived silently.
- Visual inspection and numerical checks are separate gates. Procedural fixtures do not prove quality on arbitrary creatures.
- Never invent compatibility, performance, adoption, test results or sponsorship claims.
- Review changes and test outputs before proposing a commit. No automatic merges or releases.
