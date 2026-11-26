# Vocabulary input format

UTF-8 JSON object (UTF-8 BOM accepted). Explicit input files are validated by content; directory scans find `*.vocabulary.json`.

```json
{
    "filetype": "vocabulary",
    "words": [
        {
            "word": "underpin",
            "family": ["underpinned"],
            "phonetic_uk": "/ˌʌndəˈpɪn/",
            "phonetic_us": "",
            "meanings": [{"pos": "v.", "meaning": "为……提供基础或支持"}]
        }
    ]
}
```

- `filetype`: required, exactly `vocabulary`.
- `words`: required array; empty arrays are valid.
- Each entry: object with nonblank string `word` and array `meanings` (may be empty).
- Each meaning: object with string `pos` and `meaning`; empty strings are accepted.
- `phonetic_uk` and `phonetic_us`: optional strings; UK preferred, US fallback; both empty means omitted. Null is invalid.
- `family` and unknown fields: ignored, not validated or modified.
- Duplicate words and meanings are retained, in input order. No linguistic correction or sorting.
- Default title: filename minus `.vocabulary.json`; for other explicit filenames, remove the final extension.
- Text is escaped for LaTeX; line breaks and tabs become spaces for typesetting. The input file is never rewritten.

Output is a standalone UTF-8 `.tex` document, not JSON. The default output is `latex-vocabulary/<stem>.vocabulary.tex` beside the input.
