#!/usr/bin/python

import argparse
import os
import pathlib
import PIL
from array import array
from palette_conv import pack_rgb565, unpack_rgb565
from PIL import Image

# TODO:
# Generate atlases
# Generate palette from source images if possible

# Current header format:
# original width (u16)
# original height (u16)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", type=pathlib.Path, nargs="+")
    args = parser.parse_args()
    for path in args.files:
        if not path.exists():
            print(f"Skipping missing file: {path}")
            continue

        if path.suffix == ".d16":
            convert_d16_png(path)
            continue

        try:
            converted = convert_image_d16(path)
            output_suffix = ".d16"
        except PIL.UnidentifiedImageError as e:
            print(e)
            continue

        with open(path.with_suffix(output_suffix), "wb") as output:
            converted.tofile(output)
    return 0


def convert_image_d16(filename: str) -> array:
    im = Image.open(filename)
    if im.mode != "RGB":
        im.convert("RGB")
    w, h = im.size
    result = array("H", [0] * (w * h + 2))
    result[0] = w
    result[1] = h
    idx = 2
    pixels = im.load()
    assert pixels is not None
    for x in range(w):
        for y in range(h):
            pixel = pixels[x, y]
            assert isinstance(pixel, tuple)
            result[idx] = pack_rgb565(*pixel)
            idx += 1
    return result


def convert_d16_png(filename: pathlib.Path):
    with open(filename, "rb") as f:
        tmp = array("H", [0, 0])
        f.readinto(tmp)
        header_len = f.tell()
        w, h = tmp[0], tmp[1]

        f.seek(0, os.SEEK_END)
        filesize = f.tell() - header_len
        f.seek(header_len, os.SEEK_SET)

        tmp = array("H", [])
        tmp.fromfile(f, filesize // 2)

    im = Image.new("RGB", (w, h))
    pixels = im.load()
    assert pixels is not None
    idx = 0
    for x in range(w):
        for y in range(h):
            pixels[x, y] = unpack_rgb565(tmp[idx])
            idx += 1
    im.save(filename.with_suffix(".d16.png"))


if __name__ == "__main__":
    main()
