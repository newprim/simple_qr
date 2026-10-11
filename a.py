#!/usr/bin/env python3
"""Offline QR text extractor and generator for Google Authenticator exports."""
import argparse
from pathlib import Path
import sys
"""
https://github.com/meld-cp/obsidian-encrypt/blob/main/tools/offline-decrypt.js
python3 -m venv .venv
source .venv/bin/activate
pip install opencv-python-headless "qrcode[pil]"
python a.py decode png txt
python a.py encode txt png
"""

def decode(image_path: Path, output_path: Path) -> None:
    import cv2

    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")
    detector = cv2.QRCodeDetector()
    text, _, _ = detector.detectAndDecode(image)
    if not text:
        # Multi-code images are uncommon, but report rather than silently dropping codes.
        ok, texts, _, _ = detector.detectAndDecodeMulti(image)
        if ok and len([t for t in texts if t]) > 1:
            raise ValueError("Multiple QR codes in one image: crop and decode them separately")
        text = next((t for t in texts if t), "") if ok else ""
    if not text:
        raise ValueError("QR not found or cannot be decoded; try a sharper, uncropped PNG")
    if not text.startswith("otpauth-migration://"):
        print("Warning: QR does not start with otpauth-migration://", file=sys.stderr)
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {output_path}")
    # 0600 ensures only the current user can read this plaintext secret on Unix/macOS.
    import os
    fd = os.open(output_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Saved QR contents to {output_path} (keep it secret)")


def encode(input_path: Path, image_path: Path) -> None:
    import qrcode

    if image_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {image_path}")
    text = input_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("Input file is empty")
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4, box_size=12)
    qr.add_data(text)
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").save(image_path)
    print(f"Saved QR image to {image_path} (keep it secret)")


def main():
    parser = argparse.ArgumentParser(description="Decode and re-create Google Authenticator export QR, offline")
    sub = parser.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("decode", help="Extract QR content from a PNG/JPG")
    d.add_argument("image", type=Path)
    d.add_argument("output", type=Path)
    e = sub.add_parser("encode", help="Generate QR PNG from a text file")
    e.add_argument("input", type=Path)
    e.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        if args.cmd == "decode":
            decode(args.image, args.output)
        else:
            encode(args.input, args.output)
    except (ValueError, OSError) as err:
        parser.exit(1, f"Error: {err}\n")


if __name__ == "__main__":
    main()
