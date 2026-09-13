import argparse
import base64
import os
import re
from urllib.parse import quote


def extract_base64_images(md_file_path):
    output_folder = os.path.dirname(md_file_path) or "."
    document_name = os.path.splitext(os.path.basename(md_file_path))[0]
    images_folder = os.path.join(output_folder, document_name)

    # Read the dirty markdown content
    with open(md_file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Regex pattern to locate Markdown image syntax wrapping base64 URIs
    # Handles png, jpeg, jpg, webp, and gif formats
    pattern = (
        r"!\[(.*?)\]\(data:image/(png|jpeg|jpg|webp|gif);base64,([A-Za-z0-9+/=]+)\)"
    )

    matches = re.findall(pattern, content)
    if not matches:
        print("No Base64 embedded images found in this file.")
        return None

    print(f"Found {len(matches)} embedded images. Processing...")

    os.makedirs(images_folder, exist_ok=True)

    # Loop through each image match, decode, save, and replace references
    img_counter = 1

    # We use re.sub with a callback function to replace each match step-by-step
    def replacer(match):
        nonlocal img_counter
        alt_text = match.group(1) or f"extracted_img_{img_counter}"
        base64_str = match.group(3)

        # Force everything to PNG format
        filename = f"image_{img_counter}.png"
        filepath = os.path.join(images_folder, filename)

        # Decode base64 bytes and write to binary image file
        try:
            img_data = base64.b64decode(base64_str)
            with open(filepath, "wb") as img_file:
                img_file.write(img_data)
        # binascii.Error (a ValueError) for malformed base64, OSError if the
        # sibling folder is unwritable. Anything else is a real bug worth raising.
        except (ValueError, OSError) as e:
            print(f"Error decoding image {img_counter}: {e}")
            return match.group(0)  # Keep original text if fail

        print(f"Saved: {filepath}")

        # Construct the new clean Markdown reference path, relative to the source file
        # URL-encode each segment so link destinations with spaces stay valid CommonMark
        relative_path = f"{quote(document_name)}/{quote(filename)}"
        new_md_link = f"![{alt_text}]({relative_path})"
        img_counter += 1
        return new_md_link

    # Replace all matches in-memory
    new_content = re.sub(pattern, replacer, content)

    # Write the streamlined markdown to a NEW file alongside the source, never over
    # it. INGESTION_GUIDE.md §4 tells the reader to check the result before replacing
    # the original, which is only possible if the original survives this run.
    output_md_path = os.path.join(output_folder, f"{document_name}-no-base64.md")
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Success! Wrote streamlined Markdown to {output_md_path}")
    return output_md_path


def main():
    parser = argparse.ArgumentParser(
        description="Extract base64-encoded images embedded in a Markdown file into PNG files."
    )
    parser.add_argument("md_file_path", help="Path to the Markdown file to clean")
    args = parser.parse_args()

    extract_base64_images(args.md_file_path)


if __name__ == "__main__":
    main()
