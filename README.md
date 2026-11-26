# ExportVocabulary

Convert ReadArticles-compatible vocabulary JSON into standalone LaTeX documents. Python 3.10+; standard library only. See [FORMAT.md](FORMAT.md) for input format.

## Usage (PowerShell)

```powershell
python exportvocabulary.py --info
python exportvocabulary.py --help
python exportvocabulary.py "C:\Library\Example.vocabulary.json"
python exportvocabulary.py "C:\Library\The Economist"
python exportvocabulary.py "C:\Library\The Economist" --merge
python exportvocabulary.py "A.vocabulary.json" "B.vocabulary.json" --merge -o "Vocabulary.tex"
python exportvocabulary.py "vocabulary.json" --title "English Vocabulary" --overwrite
```

Directory scans recurse in natural path order, excluding hidden directories, audio, cache, userdata, __pycache__, latex-vocabulary and links/junctions. Explicit input order is preserved; duplicate physical paths are processed once. Words and meanings are never deduplicated. Default output is beside the source in latex-vocabulary; a single directory merge uses that directory's latex-vocabulary folder and directory name; a multi-input merge uses the working directory's latex-vocabulary/Vocabulary.tex. `--output` requires one resulting document; `--title` requires one article. Existing output is skipped unless `--overwrite` is given. Merge validates all inputs before publication. Exit codes: 0 success (including skips), 1 failure, 2 invalid arguments.

## Settings

The script directory contains `latex-vocabulary-settings.json` and `latex-vocabulary-settings.backup.json`, created automatically on first conversion. Edit the main file to change page, fonts, colors, spacing and sizes. Valid settings are used directly; missing keys use defaults in memory, unknown keys are retained. Backup holds the last verified effective settings. Missing main settings are restored from backup; invalid files are warned about and preserved under timestamped corrupted names before recovery. If neither is usable, defaults are initialized. I/O failures are reported rather than treated as corruption. `--info` and `--help` do not touch settings.

Default fonts: TeX Gyre Termes, Source Han Serif SC, Charis SIL. Install these fonts or explicitly select available alternatives in settings. No automatic font substitution. Default word color #B7394D and IPA #0A7785 match ReadArticles. Other text is black. Colors accept six-digit hex with a leading #. Column count supports 2–4, default 2. Paper options: A4, A5, A3, Letter, Legal (LaTeX names ending in paper); portrait or landscape.

## Compile manually

Install TeX Live or MiKTeX with XeLaTeX, ctex, fontspec, geometry, multicol, xcolor and the selected fonts. From the output directory:

```powershell
xelatex -halt-on-error "Example.vocabulary.tex"
```

The generated file needs no Python, JSON or template at compile time. The title spans the full width; vocabulary uses balanced columns with fixed entry spacing and hanging meaning indentation. Merged articles start on separate pages. Ordinary entries remain together; very tall entries may split. Extremely long unbroken strings may cause overfull lines; review compiler warnings. No automatic PDF generation.

## Test

```powershell
python -m unittest discover -s tests -v
```
