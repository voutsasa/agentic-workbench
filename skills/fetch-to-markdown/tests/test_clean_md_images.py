"""Unit tests for clean_md_images.py — stdlib only, no network, no model calls.

    python3 -m unittest discover -s skills/fetch-to-markdown/tests
"""

from __future__ import annotations

import base64
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

# E402: sys.path has to be extended before this import, so it cannot move to the top.
import clean_md_images

# A one-pixel PNG. Real bytes rather than b"x", so a decode that silently
# corrupts the payload shows up as a byte comparison failure.
PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
PIXEL_B64 = base64.b64encode(PIXEL).decode()


def _doc(*images: str) -> str:
    return "# Title\n\n" + "\n\n".join(images) + "\n\nTrailing prose.\n"


class RewriteTests(unittest.TestCase):
    """The pure half: rewriting links, with the filesystem stubbed out."""

    def _capture(self):
        written: list[tuple[int, bytes]] = []

        def write_image(index: int, data: bytes) -> str:
            written.append((index, data))
            return f"image_{index}.png"

        return written, write_image

    def test_extracts_and_rewrites_each_format(self):
        for fmt in ("png", "jpeg", "jpg", "webp", "gif"):
            with self.subTest(fmt=fmt):
                written, write_image = self._capture()
                out, count = clean_md_images.rewrite(
                    _doc(f"![alt](data:image/{fmt};base64,{PIXEL_B64})"),
                    "Doc",
                    write_image,
                )
                self.assertEqual(count, 1)
                self.assertEqual(written, [(1, PIXEL)])
                self.assertIn("![alt](Doc/image_1.png)", out)
                self.assertNotIn("base64", out)

    def test_numbers_images_sequentially(self):
        written, write_image = self._capture()
        out, count = clean_md_images.rewrite(
            _doc(
                f"![a](data:image/png;base64,{PIXEL_B64})",
                f"![b](data:image/png;base64,{PIXEL_B64})",
                f"![c](data:image/png;base64,{PIXEL_B64})",
            ),
            "Doc",
            write_image,
        )
        self.assertEqual(count, 3)
        self.assertEqual([i for i, _ in written], [1, 2, 3])
        for n, alt in ((1, "a"), (2, "b"), (3, "c")):
            self.assertIn(f"![{alt}](Doc/image_{n}.png)", out)

    def test_document_name_with_spaces_is_url_encoded(self):
        """Most of docs/landing-zone/ has spaces in its filenames, and a raw
        space makes the link destination invalid CommonMark."""
        _, write_image = self._capture()
        out, _ = clean_md_images.rewrite(
            _doc(f"![x](data:image/png;base64,{PIXEL_B64})"),
            "Pydantic AI",
            write_image,
        )
        self.assertIn("![x](Pydantic%20AI/image_1.png)", out)
        self.assertNotIn("Pydantic AI/", out)

    def test_empty_alt_text_gets_a_placeholder(self):
        _, write_image = self._capture()
        out, _ = clean_md_images.rewrite(
            _doc(f"![](data:image/png;base64,{PIXEL_B64})"), "Doc", write_image
        )
        self.assertIn("![extracted_img_1](Doc/image_1.png)", out)

    def test_malformed_base64_keeps_the_original_text(self):
        """Losing the payload would be worse than leaving the file dirty."""
        original = "![bad](data:image/png;base64,!!!notbase64!!!)"
        written, write_image = self._capture()
        out, count = clean_md_images.rewrite(_doc(original), "Doc", write_image)
        # The pattern's character class excludes `!`, so this never matches and
        # never reaches the decoder — the text survives either way.
        self.assertEqual(count, 0)
        self.assertEqual(written, [])
        self.assertIn(original, out)

    def test_truncated_base64_keeps_the_original_text(self):
        """Matches the pattern but is not decodable — this one does reach the
        decoder, and must still not destroy the source text."""
        truncated = "![bad](data:image/png;base64,QUJDR)"
        written, write_image = self._capture()
        out, count = clean_md_images.rewrite(_doc(truncated), "Doc", write_image)
        self.assertEqual(count, 0)
        self.assertEqual(written, [])
        self.assertIn(truncated, out)

    def test_non_base64_images_are_left_alone(self):
        untouched = "![screenshot](images/real-file.png)"
        _, write_image = self._capture()
        out, count = clean_md_images.rewrite(_doc(untouched), "Doc", write_image)
        self.assertEqual(count, 0)
        self.assertIn(untouched, out)


class ExtractBase64ImagesTests(unittest.TestCase):
    """The I/O half, against a real temporary directory."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def _write(self, name: str, content: str) -> Path:
        path = self.tmp / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_writes_pngs_and_a_cleaned_file(self):
        src = self._write(
            "Report.md",
            _doc(
                f"![one](data:image/png;base64,{PIXEL_B64})",
                f"![two](data:image/jpeg;base64,{PIXEL_B64})",
            ),
        )
        out = clean_md_images.extract_base64_images(src)

        assert out is not None  # narrows Path | None for the reader and the checker
        self.assertEqual(out, self.tmp / "Report-no-base64.md")
        self.assertEqual((self.tmp / "Report" / "image_1.png").read_bytes(), PIXEL)
        self.assertEqual((self.tmp / "Report" / "image_2.png").read_bytes(), PIXEL)
        self.assertNotIn("base64", out.read_text(encoding="utf-8"))

    def test_the_original_is_never_overwritten(self):
        """The guide tells the reader to compare the two before replacing the
        original, which only works if the original survives."""
        content = _doc(f"![one](data:image/png;base64,{PIXEL_B64})")
        src = self._write("Report.md", content)
        clean_md_images.extract_base64_images(src)
        self.assertEqual(src.read_text(encoding="utf-8"), content)

    def test_no_images_writes_nothing(self):
        src = self._write("Plain.md", "# Title\n\nJust prose.\n")
        self.assertIsNone(clean_md_images.extract_base64_images(src))
        self.assertEqual(list(self.tmp.iterdir()), [src])

    def test_a_document_name_with_spaces_round_trips(self):
        """The filename, the folder and the link have to agree — the folder is
        created with a literal space and only the link is percent-encoded."""
        src = self._write(
            "Pydantic AI.md", _doc(f"![x](data:image/png;base64,{PIXEL_B64})")
        )
        out = clean_md_images.extract_base64_images(src)

        assert out is not None  # narrows Path | None for the reader and the checker
        self.assertEqual(out, self.tmp / "Pydantic AI-no-base64.md")
        self.assertTrue((self.tmp / "Pydantic AI" / "image_1.png").is_file())
        self.assertIn("(Pydantic%20AI/image_1.png)", out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
