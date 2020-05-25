import pytest
from amoco.cas.mapper import mapper
from amoco.arch.x64 import cpu_x64 as cpu
from amoco.arch.x64.env import *
from amoco.cas import expressions


def test_mapper_000():
  # create two instructions
  # movq    %rcx, (%rip)
  # movq    (%rip), %rcx
  i0 = cpu.disassemble(b"\x48\x89\x0d\x00\x00\x00\x00")
  i1 = cpu.disassemble(b"\x48\x8b\x0d\x00\x00\x00\x00")
  # modify the first instruction to insert a label, e.g. because
  # there is a relocation
  # movq    %rcx, foo(%rip)
  i0.operands[0].a.disp = expressions.lab('foo', size=64)
  # evaluate those two instructions
  m=mapper()
  i0(m)
  i1(m)
  assert str(m[rcx]) == 'M64(rip+14)'

def test_mapper_001():
  # create three instructions
  # movq    %rax, (%rip)
  # movl    %eax, (%rip)
  # movq    -16(%rbp), %rcx
  i0 = cpu.disassemble(b"\x48\x89\x05\x00\x00\x00\x00")
  i1 = cpu.disassemble(b"\x89\x05\x00\x00\x00\x00")
  i2 = cpu.disassemble(b"\x48\x8b\x4d\xf0")
  # modify the first two instructions to insert a label
  # movq    %rax, foo(%rip)
  i0.operands[0].a.disp = expressions.lab('foo', size=64)
  # movb    %eax, bar(%rip)
  i1.operands[0].a.disp = expressions.lab('bar', size=64)
  # evaluate those three instructions
  m=mapper()
  i0(m)
  i1(m)
  i2(m)
  assert str(m[rcx]) == 'M64(rbp-16)'
