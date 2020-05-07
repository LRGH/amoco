# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2015 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license

"""
cas/smt.py
==========

The smt module defines the amoco interface to the SMT solver.
Currently, only z3 is supported. This module allows to translate
any amoco expression into its z3 equivalent formula, as well as
getting the z3 solver results back as :class:`cas.mapper.mapper`
instances.
"""

from amoco.logger import Log

logger = Log(__name__)
logger.debug("loading module")

from .expressions import *
from amoco.cas.mapper import mapper

try:
    import z3
except ImportError:
    logger.info("z3 package not found => solve() method is not implemented")

    class solver(object):
        def __init__(self, eqns=None, tactics=None, timeout=None):
            raise NotImplementedError

    has_solver = False
else:
    logger.info("z3 package imported")

    class solver(object):
        """
        Wrapper of z3.Solver which allows to convert boolean expressions
        to their z3 bitvector-based forms and ultimately convert back a z3
        *model* into an amoco :class:`mapper` instance.

        Arguments:
            eqns (list, []): optional list of 'op' expressions or expressions
                             with a size of 1 bit.
            tactics (list, None): optional list of z3 tactics.
            timeout (int, None): optional timeout value for the z3 solver.
        """
        def __init__(self, eqns=None, tactics=None, timeout=None):
            self.eqns = []
            self.locs = []
            if tactics:
                s = z3.TryFor(z3.Then(*tactics), 1000).solver()
            else:
                s = z3.Solver()
            if timeout:
                s.set(timeout=1000)
            self.solver = s
            if eqns:
                self.add(eqns)
            self._ctr = 0

        def add(self, eqns):
            "add input list of 'op' expressions to the solver"
            for e in eqns:
                self.eqns.append(e)
                self.solver.add(cast_z3_bool(e, self))
                self.locs.extend(locations_of(e))

        def check(self):
            "check for satisfiability of current formulas"
            logger.verbose("z3 check...")
            return self.solver.check()

        def get_model(self, eqns=None):
            "If satisfiable, returns a z3 *model* for the solver (with added eqns)"
            if eqns is not None:
                self.add(eqns)
            if self.check() == z3.sat:
                r = self.solver.model()
                return r

        def get_mapper(self, eqns=None):
            """
            If satisfiable,
            returns an amoco mapper for the current solver (with added eqns)
            """
            r = self.get_model(eqns)
            if r is not None:
                return model_to_mapper(r, self.locs)

        @property
        def ctr(self):
            "internal counter for variables associated to 'top' or 'vec' expressions"
            ctr = self._ctr
            self._ctr += 1
            return ctr

    has_solver = True


def newvar(pfx, e, slv):
    "return a new z3 BitVec of size e.size, with name prefixed by slv argument"
    s = "" if slv is None else "%d" % slv.ctr
    return z3.BitVec("%s%s" % (pfx, s), e.size)


def top_to_z3(e, slv=None):
    "translate top expression into a new _topN BitVec variable"
    return newvar("_top", e, slv)


def cst_to_z3(e, slv=None):
    "translate cst expression into its z3 BitVecVal form"
    return z3.BitVecVal(e.v, e.size)


def cfp_to_z3(e, slv=None):
    "translate cfp expression into its z3 RealVal form"
    return z3.RealVal(e.v)


def reg_to_z3(e, slv=None):
    "translate reg expression into its z3 BitVec form"
    return z3.BitVec(e.ref, e.size)


def comp_to_z3(e, slv=None):
    "translate comp expression into its z3 Concat form"
    e.simplify()
    parts = [x.to_smtlib(slv) for x in e]
    parts.reverse()
    if len(parts) > 1:
        return z3.Concat(*parts)
    else:
        return parts[0]


def slc_to_z3(e, slv=None):
    "translate slc expression into its z3 Extract form"
    x = e.x.to_smtlib(slv)
    return z3.Extract(int(e.pos + e.size - 1), int(e.pos), x)


def ptr_to_z3(e, slv=None):
    "translate ptr expression into its z3 form"
    return e.base.to_smtlib(slv) + e.disp


def mem_to_z3(e, slv=None):
    "translate mem expression into z3 a Concat of BitVec bytes"
    e.simplify()
    M = z3.Array("M", z3.BitVecSort(e.a.size), z3.BitVecSort(8))
    p = e.a.to_smtlib(slv)
    b = []
    for i in range(0, e.length):
        b.insert(0, M[p + i])
    if e.endian == -1:
        b.reverse()  # big-endian case
    if len(b) > 1:
        return z3.Concat(*b)
    return b[0]


def cast_z3_bool(x, slv=None):
    "translate boolean expression into its z3 bool form"
    b = x.to_smtlib(slv)
    if not z3.is_bool(b):
        assert b.size() == 1
        b = b == z3.BitVecVal(1, 1)
    return b


def cast_z3_bv(x, slv=None):
    """
    translate expression x to its z3 form, if x.size==1 the
    returned formula is (If x ? 1 : 0).
    """
    b = x.to_smtlib(slv)
    if z3.is_bool(b):
        b = z3.If(b, z3.BitVecVal(1, 1), z3.BitVecVal(0, 1))
    return b


def tst_to_z3(e, slv=None):
    "translate tst expression into a z3 If form"
    e.simplify()
    z3t = cast_z3_bool(e.tst, slv)
    l = cast_z3_bv(e.l, slv)
    r = cast_z3_bv(e.r, slv)
    return z3.If(z3t, l, r)


def tst_verify(e, env):
    t = e.tst.eval(env).simplify()
    s = solver(tactics=["simplify", "elim-term-ite", "solve-eqs", "smt"])
    zt = cast_z3_bool(t, s)
    for c in env.conds:
        s.solver.add(cast_z3_bool(c, s))
    s.solver.push()
    s.solver.add(zt)
    rtrue = s.solver.check()
    s.solver.pop()
    s.solver.add(z3.Not(zt))
    rfalse = s.solver.check()
    if rtrue == z3.sat and rfalse == z3.unsat:
        return bit1
    if rtrue == z3.unsat and rfalse == z3.sat:
        return bit0
    if rtrue == z3.sat and rfalse == z3.sat:
        return t
    logger.verbose("undecidable tst expression")
    return t


def op_to_z3(e, slv=None):
    "translate op expression into its z3 form"
    e.simplify()
    l, r = e.l, e.r
    op = e.op
    if op.symbol == ">>":
        op = z3.LShR
    elif op.symbol == "//":
        op = operator.rshift
    elif op.symbol == ">>>":
        op = z3.RotateRight
    elif op.symbol == "<<<":
        op = z3.RotateLeft
    elif op.symbol == "**":
        l = l.zeroextend(2 * l.size)
        r = r.zeroextend(2 * r.size)
        op = (l * r).op
    z3l = l.to_smtlib(slv)
    z3r = r.to_smtlib(slv)
    if z3.is_bool(z3l):
        z3l = _bool2bv1(z3l)
    if z3.is_bool(z3r):
        z3r = _bool2bv1(z3r)
    if z3l.size() != z3r.size():
        greatest = max(z3l.size(), z3r.size())
        z3l = z3.ZeroExt(greatest - z3l.size(), z3l)
        z3r = z3.ZeroExt(greatest - z3r.size(), z3r)
    res = op(z3l, z3r)
    if z3.is_bool(res):
        res = _bool2bv1(res)
    return res


def uop_to_z3(e, slv=None):
    "translate uop expression into its z3 form"
    e.simplify()
    r = e.r
    op = e.op
    z3r = r.to_smtlib(slv)
    if z3.is_bool(z3r):
        z3r = _bool2bv1(z3r)
    return op(z3r)


def vec_to_z3(e, slv=None):
    "translate vec expression into z3 Or form"
    # flatten vec:
    e.simplify()
    # translate vec list to z3:
    beqs = []
    for x in e.l:
        zx = x.to_smtlib()
        beqs.append(zx)
    if len(beqs) == 0:
        return exp(e.size)
    if slv is None:
        # if no solver is provided, it needs to be
        # a list of boolean equations
        if all([z3.is_bool(x) for x in beqs]):
            if len(beqs) == 1:
                return beqs[0]
            return z3.Or(*beqs)
        else:
            return top_to_z3(top(e.size))
    else:
        # if the solver is provided (default)
        # then a new local variable is added which
        # should equal one of the z3 expression.
        var = newvar("_var", e, slv)
        slv.solver.add(z3.Or([var == x for x in beqs]))
    return var


def _bool2bv1(z):
    return z3.If(z, z3.BitVecVal(1, 1), z3.BitVecVal(0, 1))


if has_solver:
    top.to_smtlib = top_to_z3
    cst.to_smtlib = cst_to_z3
    cfp.to_smtlib = cfp_to_z3
    reg.to_smtlib = reg_to_z3
    comp.to_smtlib = comp_to_z3
    slc.to_smtlib = slc_to_z3
    ptr.to_smtlib = ptr_to_z3
    mem.to_smtlib = mem_to_z3
    tst.to_smtlib = tst_to_z3
    tst.verify = tst_verify
    op.to_smtlib = op_to_z3
    uop.to_smtlib = uop_to_z3
    vec.to_smtlib = vec_to_z3
    vecw.to_smtlib = top_to_z3


def to_smtlib(e, slv=None):
    "return the z3 smt form of expression e"
    return e.to_smtlib(slv)


def model_to_mapper(r, locs):
    "return an amoco mapper based on given locs for the z3 model r"
    m = mapper()
    mlocs = []
    for l in set(locs):
        if l._is_mem:
            mlocs.append(l)
        else:
            x = r.eval(l.to_smtlib())
            try:
                m[l] = cst(x.as_long(), l.size)
            except AttributeError:
                pass
    for l in mlocs:
        x = r.eval(l.to_smtlib())
        try:
            m[l] = cst(x.as_long(), l.size)
        except AttributeError:
            pass
    return m
