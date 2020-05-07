# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2012 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license

import struct
from amoco.system.memory import MemoryMap
from amoco.arch.z80 import cpu_gb as cpu

# define gameboy system:
card_type = {
    0x00: "ROM ONLY",
    0x01: "ROM+MBC1",
    0x02: "ROM+MBC1+RAM",
    0x03: "ROM+MBC1+RAM+BATT",
    0x05: "ROM+MBC2",
    0x06: "ROM+MBC2+BATTERY",
    0x08: "ROM+RAM",
    0x09: "ROM+RAM+BATTERY",
    0x0B: "ROM+MMM01",
    0x0C: "ROM+MMM01+SRAM",
    0x0D: "ROM+MMM01+SRAM+BATT",
    0x0F: "ROM+MBC3+TIMER+BATT",
    0x10: "ROM+MBC3+TIMER+RAM+BATT",
    0x11: "ROM+MBC3",
    0x12: "ROM+MBC3+RAM",
    0x13: "ROM+MBC3+RAM+BATT",
    0x19: "ROM+MBC5",
    0x1A: "ROM+MBC5+RAM",
    0x1B: "ROM+MBC5+RAM+BATT",
    0x1C: "ROM+MBC5+RUMBLE",
    0x1D: "ROM+MBC5+RUMBLE+SRAM",
    0x1E: "ROM+MBC5+RUMBLE+SRAM+BATT",
    0x1F: "Pocket Camera",
    0xFD: "Bandai TAMA5",
    0xFE: "Hudson HuC-3",
    0xFF: "Hudson HuC-1",
}

# ----------------------------------------------------------------------------


class Cardridge(object):
    def __init__(self, path):
        self.__file = open(path, "rb")
        self.data = self.__file.read()

    @property
    def entrypoints(self):
        return [0x100]

    def nintendo_graphics(self):
        s = self.data[0x104:0x134]
        return s

    def title(self):
        s = self.data[0x134:0x142]
        return s.strip(b"\0")

    def colorgb(self):
        return ord(self.data[0x143:0x144]) == 0x80

    def licensee(self):
        x = ord(self.data[0x14B:0x14C])
        if x == 0x33:
            return struct.unpack(">H", self.data[0x144:0x146])
        if x == 0x79:
            return "Accolade"
        if x == 0xA4:
            return "Konami"

    def supergb(self):
        return ord(self.data[0x146:0x147]) == 3

    def type(self):
        return card_type.get(ord(self.data[0x147:0x148]), "Unknown")

    def romsize(self):
        D = {
            0: 2,
            1: 4,
            2: 8,
            3: 16,
            4: 32,
            5: 64,
            6: 128,
            0x52: 72,
            0x53: 80,
            0x54: 96,
        }
        return D.get(ord(self.data[0x148:0x149]), None)

    def ramsize(self):
        D = {0: None, 1: 1, 2: 1, 3: 4, 4: 16}
        return D.get(ord(self.data[0x149:0x14A]), None)

    def destination(self):
        if ord(self.data[0x14A:0x14B]) == 0:
            return "Japanese"
        else:
            return "Non-Japanese"

    def complement_check(self):
        return ord(self.data[0x14D:0x14E])

    def checksum(self):
        return struct.unpack(">H", self.data[0x14E:0x15])


# ----------------------------------------------------------------------------


class z80GB(object):
    __slots__ = ["card", "cpu", "mmap"]

    def __init__(self, path):
        self.card = Cardridge(path)
        self.cpu = cpu
        self.mmap = MemoryMap()
        self.load_binary()

    # load the program into virtual memory (populate the mmap dict)
    def load_binary(self):
        self.mmap.write(0, self.card.data[:0x8000].ljust(0x8000, b"\0"))
        # 8k video RAM:
        self.mmap.write(0x8000, b"".ljust(8192, b"\0"))
        # 8k switchable RAM:
        self.mmap.write(0xA000, b"".ljust(8192, b"\0"))
        # internal RAM:
        self.mmap.write(0xC000, b"".ljust(16382, b"\0"))

    def read_data(self, vaddr, size):
        return self.mmap.read(vaddr, size)

    def read_instruction(self, vaddr, **kargs):
        maxlen = self.cpu.disassemble.maxlen
        try:
            istr = self.mmap.read(vaddr, maxlen)
        except MemoryError as e:
            logger.warning("vaddr %s is not mapped" % vaddr)
            raise MemoryError(e)
        i = self.cpu.disassemble(istr[0], **kargs)
        if i is None:
            logger.warning("disassemble failed at vaddr %s" % vaddr)
            if len(istr) > 1 and istr[1]._is_def:
                logger.warning("symbol found in instruction buffer" % vaddr)
                raise MemoryError(vaddr)
            return None
        else:
            i.address = vaddr
            return i

    def initenv(self):
        from amoco.cas.mapper import mapper

        m = mapper()
        for k, v in (
            (cpu.pc, cpu.cst(self.card.entrypoints[0], 16)),
            (cpu.sp, cpu.cst(0xFFFE, 16)),
            (cpu.a, cpu.cst(0x11 if self.card.colorgb() else 0x01, 8)),
            (cpu.f, cpu.cst(0xB0, 8)),
            (cpu.bc, cpu.cst(0x0013, 16)),
            (cpu.de, cpu.cst(0x00D8, 16)),
            (cpu.hl, cpu.cst(0x014D, 16)),
        ):
            m[k] = v
        return m

    # optional codehelper method allows platform-specific analysis of
    # either a (raw) list of instruction, a block/func object (see amoco.code)
    # the default helper is a no-op:
    def codehelper(self, seq=None, block=None, func=None):
        if seq is not None:
            return seq
        if block is not None:
            return block
        if func is not None:
            return func
