#!/usr/bin/env python3
"""Extract base64 data-URI images out of converted markdown into sibling PNGs.

docling and pandoc both inline figures as `data:image/...;base64,...` URIs when
converting a PDF or a `.docx`. A page of screenshots becomes megabytes of
unreadable markdown that no diff and no reviewer can work with, so this decodes
each one to a file and rewrites the link to point at it.

Usage: python clean_md_images.py <markdown-file>

Writes `<name>-no-base64.md` beside the source and the PNGs into a sibling
`<name>/` folder. **The original is never overwritten** — the ingestion guide's
quality check tells the reader to compare the two before replacing it, which is
only possible if both survive the run.

Standard library only: this runs on a fresh clone before any venv exists.
"""

from __future__ import annotations

import argparse
import base64
import re
import sys
from pathlib import Path
from urllib.parse import quote

# Markdown image syntax wrapping a base64 data URI. The formats listed are the
# ones docling and pandoc actually emit; an unlisted format is left untouched
# rather than mangled, which is the safe failure.
IMAGE_PATTERN = re.compile(
    r"!\[(.*?)\]\(data:image/(png|jpeg|jpg|webp|gif);base64,([A-Za-z0-9+/=]+)\)"
)


def rewrite(content: str, document_name: str, write_image) -> tuple[str, int]:
    """Replace every embedded image with a link to a file `write_image` saved.

    Pure but for the callback, which takes (index, bytes) and returns the
    filename it wrote — so a test can drive the rewriting without a filesystem.
    Returns the new markdown and the number of images extracted.
    """
    counter = 0
    extracted = 0

    def replacer(match: re.Match[str]) -> str:
        nonlocal counter, extracted
        counter += 1
        alt_text = match.group(1) or f"extracted_img_{counter}"
        try:
            # validate=True so a corrupted URI raises here rather than writing a
            # PNG that no viewer can open. b64decode otherwise discards any
            # character outside the alphabet and decodes whatever is left.
            data = base64.b64decode(match.group(3), validate=True)
            filename = write_image(counter, data)
        # binascii.Error (a ValueError) for malformed base64, OSError if the
        # sibling folder is unwritable. Anything else is a real bug worth raising.
        except (ValueError, OSError) as exc:
            print(f"Error decoding image {counter}: {exc}", file=sys.stderr)
            return match.group(0)  # keep the original text so nothing is lost

        extracted += 1
        # URL-encode each segment so a document whose name contains spaces —
        # most of docs/landing-zone/ does — still produces a valid CommonMark
        # link destination.
        return f"![{alt_text}]({quote(document_name)}/{quote(filename)})"

    return IMAGE_PATTERN.sub(replacer, content), extracted


def extract_base64_images(md_file_path: Path) -> Path | None:
    """Clean one markdown file. Returns the path written, or None if there was
    nothing to extract."""
    md_file_path = Path(md_file_path)
    output_folder = md_file_path.parent
    document_name = md_file_path.stem
    images_folder = output_folder / document_name

    content = md_file_path.read_text(encoding="utf-8")

    if not IMAGE_PATTERN.search(content):
        print("No Base64 embedded images found in this file.")
        return None

    images_folder.mkdir(parents=True, exist_ok=True)

    def write_image(index: int, data: bytes) -> str:
        # Everything is written as .png regardless of the source format. The
        # extension is cosmetic here — the bytes are unchanged, and every viewer
        # that matters sniffs the magic number rather than trusting the suffix.
        filename = f"image_{index}.png"
        (images_folder / filename).write_bytes(data)
        print(f"Saved: {images_folder / filename}")
        return filename

    new_content, extracted = rewrite(content, document_name, write_image)
    print(f"Found {extracted} embedded images. Processing...")

    output_md_path = output_folder / f"{document_name}-no-base64.md"
    output_md_path.write_text(new_content, encoding="utf-8")

    print(f"Success! Wrote streamlined Markdown to {output_md_path}")
    return output_md_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract base64-encoded images embedded in a Markdown file into PNG files."
    )
    parser.add_argument(
        "md_file_path", type=Path, help="Path to the Markdown file to clean"
    )
    args = parser.parse_args()

    if not args.md_file_path.is_file():
        print(f"not a file: {args.md_file_path}", file=sys.stderr)
        return 1

    extract_base64_images(args.md_file_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
