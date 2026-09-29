# Validation fixtures

Sample inputs for the conversion checks in [`../macos.md`](../macos.md) and
[`../windows.md`](../windows.md). Each is here because it exercises one route that nothing else does.

| File | Holds | Proves |
|---|---|---|
| `chartex.docx` | 8 `<w:drawing>`: 6 charts (`c:chart`, six `word/charts/chart*.xml` parts) + 2 pictures | each chart becomes its data as a pipe table; conversion adds an `Image not available` comment for 4 of the 6 (measured — see [`../macos.md`](../macos.md) section C), and the 2 pictures become base64 images |
| `shapes-with-text.docx` | 11 `wps:wsp` shapes, including a group | a shape becomes **its text as paragraphs**; the shape itself is not rendered |

Both come from [Apache POI's test data](https://github.com/apache/poi) (`test-data/document/`),
fetched 2026-09-20. POI is Apache-2.0 licensed.

**Counting what a `.docx` should produce**, before converting it:

```sh
X="unzip -p <file>.docx word/document.xml"
$X | grep -o "<pic:pic" | wc -l   # → base64 images
$X | grep -o "<c:chart" | wc -l   # → data tables + placeholders
$X | grep -o "<wps:wsp" | wc -l   # → loose paragraphs of shape text
```

**`grep -c` gives 1 for all three** and looks plausible: `word/document.xml` is one long line, so it
counts lines rather than tags. Found by running section C as written, 2026-09-20.

The `fetch-to-markdown` skill's §2 carries what each of the three becomes and why the figure count
check compares against `<pic:pic` alone.

## Adding a fixture

Add one only for a route no existing fixture covers, and record in the table above what it holds, what
it proves and where it came from. A fixture whose origin is unrecorded cannot be replaced when it
turns out to be wrong.

Keep them small. These two are 133 KB and 27 KB; anything approaching a megabyte belongs somewhere
else, with a note here pointing at it.
