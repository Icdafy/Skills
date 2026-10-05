"""License-free binary input for SFNT/OS2 mechanics; no third-party glyphs.

This deliberately small input is not a renderable font and is never distributed
as a .ttf. Word rendering must be checked separately with licensed local fonts.
"""
import os
from pathlib import Path
import struct
import tempfile


def sfnt(fs_type=0, code_page=0x00040000):
    data = bytearray(128)
    struct.pack_into('>4sHHHH', data, 0, b'\x00\x01\x00\x00', 1, 16, 0, 0)
    struct.pack_into('>4sIII', data, 12, b'OS/2', 0, 32, 96)
    struct.pack_into('>H', data, 32, 1)
    struct.pack_into('>H', data, 40, fs_type)
    data[64:74] = bytes(range(1, 11))
    struct.pack_into('>II', data, 110, code_page, 0)
    return bytes(data)


class FontFixture:
    def __enter__(self):
        self.temp = tempfile.TemporaryDirectory(prefix='font-contract-')
        self.directory = Path(self.temp.name)
        self.previous = os.environ.get('ICDAFY_FONT_DIR')
        for name, flag in (('simfang.ttf', 0), ('楷体_GB2312.ttf', 0), ('方正小标宋简体.ttf', 2)):
            (self.directory / name).write_bytes(sfnt(flag))
        os.environ['ICDAFY_FONT_DIR'] = str(self.directory)
        return self.directory

    def __exit__(self, *exc):
        if self.previous is None:
            os.environ.pop('ICDAFY_FONT_DIR', None)
        else:
            os.environ['ICDAFY_FONT_DIR'] = self.previous
        self.temp.cleanup()
