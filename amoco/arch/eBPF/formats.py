# -*- coding: utf-8 -*-

from .env import *
from amoco.cas.expressions import regtype
from amoco.arch.core import Formatter, Token


def mnemo(i):
    mn = i.mnemonic.lower()
    return [(Token.Mnemonic, "{: <12}".format(mn))]


def deref(opd):
    return "[%s+%d]" % (opd.a.base, opd.a.disp)


def opers(i):
    s = []
    for op in i.operands:
        if op._is_mem:
            s.append((Token.Memory, deref(op)))
        elif op._is_cst:
            if i.misc["imm_ref"] is not None:
                s.append((Token.Address, "%s" % (i.misc["imm_ref"])))
            elif op.sf:
                s.append((Token.Constant, "%+d" % op.value))
            else:
                s.append((Token.Constant, op.__str__()))
        elif op._is_reg:
            s.append((Token.Register, op.__str__()))
        s.append((Token.Literal, ", "))
    if len(s) > 0:
        s.pop()
    return s


def opers_adr(i):
    s = opers(i)
    if i.address is None:
        s[-1] = (Token.Address, ".%+d" % i.operands[-1])
    else:
        imm_ref = i.address + i.length + (i.operands[-1] * 8)
        s[-1] = (Token.Address, "#%s" % (imm_ref))
    return s


def opers_adr2(i):
    s = opers(i)
    if i.address is None:
        s[-3] = (Token.Address, ".%+d" % i.operands[-2])
        s[-1] = (Token.Address, ".%+d" % i.operands[-1])
    else:
        imm_ref1 = i.address + i.length * (i.operands[-2] + 1)
        imm_ref2 = i.address + i.length * (i.operands[-1] + 1)
        s[-3] = (Token.Address, "#%s" % (imm_ref1))
        s[-1] = (Token.Address, "#%s" % (imm_ref2))
    return s


format_default = (mnemo, opers)

eBPF_full_formats = {
    "ebpf_jmp_": (mnemo, opers_adr),
    "bpf_jmp_": (mnemo, opers_adr2),
}

eBPF_full = Formatter(eBPF_full_formats)
eBPF_full.default = format_default
