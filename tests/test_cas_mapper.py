import pytest

from amoco.cas.mapper import *

def test_slicing(m,x,y):
    m.clear()
    m[x] = cst(0xabcdef89,32)
    xl = slc(x,0,8,ref='xl')
    xh = slc(x,8,8,ref='xh')
    assert m(xl)==0x89
    assert m(xh)==0xef
    m[xl] = y[8:16]
    assert m(xl)==y[8:16]
    assert m(xh)==0xef
    assert m(x[16:32])==0xabcd
    m[xh] = y[0:8]
    assert m(xl)==y[8:16]
    assert m(xh)==y[0:8]
    assert m(x[16:32])==0xabcd

def test_aliasing1(m,x,y):
    al = conf.Cas.noaliasing
    conf.Cas.noaliasing = False
    m.clear()
    mx = mem(x,32)
    my = mem(y,32)
    mxx = mem(x+2,32)
    m[mx] = cst(0xdeadbeef,32)
    m[my] = cst(0xbabebabe,32)
    m[mxx] = cst(0x01234567,32)
    assert m(my)._is_mem
    assert m(mxx) == 0x01234567
    rx = m(mx)
    assert str(rx)=='M32$3(x)'
    assert rx.mods[0][1]==0xdeadbeef
    assert rx.mods[1][0]==my.a
    conf.Cas.noaliasing = al

def test_aliasing2(m,x,y,z,w,r,a,b):
    al = conf.Cas.noaliasing
    conf.Cas.noaliasing = False
    m.clear()
    mx = mem(x,32)
    my = mem(y,32)
    m[r] = m(mx)                      # mov  r  , [x]
    m[mx] = cst(0,32)                 # mov [x] , 0
    assert m(r)==mx
    assert m(mx)==0
    m[my] = cst(1,32)                 # mov [y] , 1
    assert m(my)==1
    assert (m(mx)==0) is not True
    assert len(m(mx).mods)==2
    m[z]  = m(r)                      # mov  z  , r
    assert m(z)==mx
    m[w]  = m(my)                     # mov  w  , [y]
    assert m(w)==1
    m[a]  = m(a+mx)                   # add  a  , [x]
    assert m(a).r.mods[1][0]==my.a
    m[mx] = cst(2,32)                 # mov [x] , 2
    m[my] = m(z)                      # mov [y] , z
    m[b]  = m(b+mx)                   # add  b  , [x]
    assert len(m(b).r.mods)==2
    m[mem(a,32)] = cst(0,32)          # mov [a] , 0
    conf.Cas.noaliasing = al

def test_aliasing3(m,x,y,a):
    al = conf.Cas.noaliasing
    conf.Cas.noaliasing = False
    m.clear()
    m[mem(x-4,32)] = cst(0x44434241,32)
    m[mem(x-8,32)] = y
    m[x] = x-8
    res = m(mem(x+2,32))
    assert res._is_cmp
    assert res[16:32] == 0x4241
    assert res[0:16] == y[16:32]
    m[mem(a,8)] = cst(0xCC,8)
    res = m(mem(x+2,32))
    assert res._is_mem and len(res.mods)==3
    mprev = mapper()
    mprev[a] = x-4
    res = mprev(res)
    assert res[16:24] == 0xcc
    conf.Cas.noaliasing = al

def test_compose1(m,x,y,z,w):
    al = conf.Cas.noaliasing
    conf.Cas.noaliasing = True
    mx = mem(x,32)
    my = mem(y,32)
    mxx = mem(x+2,32)
    m[mx] = cst(0xdeadbeef,32)
    m[my] = cst(0xbabebabe,32)
    m[mxx] = cst(0x01234567,32)
    m[z] = m(mem(w,32))
    mprev = mapper()
    mprev[x] = z
    mprev[y] = z
    mprev[w] = z
    cm = m<<mprev
    # x == y in prev so mx==my:
    assert cm(mx) == 0x4567babe
    assert cm(my) == 0x4567babe
    # no aliasing is assumed so z
    # receives mem(w) BEFORE m,
    # i.e mem(z):
    assert cm(z) == mem(z,32)
    conf.Cas.noaliasing = al

def test_compose2(m,x,y,z,w):
    al = conf.Cas.noaliasing
    conf.Cas.noaliasing = False
    mx = mem(x,32)
    my = mem(y,32)
    mxx = mem(x+2,32)
    m[mx] = cst(0xdeadbeef,32)
    m[my] = cst(0xbabebabe,32)
    m[mxx] = cst(0x01234567,32)
    m[z] = m(mem(w,32))
    m[w] = m(my)
    mprev = mapper()
    mprev[x] = z
    mprev[y] = z
    mprev[w] = z
    cm = m<<mprev
    # x==y in prev so mx==my:
    assert cm(mx) == 0x4567babe
    assert cm(my) == 0x4567babe
    # aliasing is possible so z
    # receives mem(z) AFTER the 2
    # memory writes in mx/my,
    # i.e cm(my):
    assert cm(w)==cm(my)
    conf.Cas.noaliasing = al

def test_signpropagate(m,x,y):
    m[x] = cst(0xfffffffe,32)
    assert (x*2).eval(m) == cst(0xfffffffc,32)
    assert (reg('x').signed()*2).eval(m) == cst(-4,32)
    m[y] = cst(-2,32)
    assert m[y]==cst(-2,32)
    assert (y*2).eval(m) == cst(-4,32)
    assert (reg('y').signed()*5).eval(m) == cst(-2*5,32)
    y8 = y[0:8]
    assert m(y8) == cst(0xfe,8)
    assert (y8**2).eval(m) == cst(0x1fc,16)
    y8.sf = True
    assert m(y8) == cst(-2,8)
    z = y8*2
    zz = y8**2
    assert z.sf == zz.sf == True
    assert (z).eval(m) == cst(-4,8)
    assert (zz).eval(m) == cst(-4,16)


def test_vec(m,x,y,z,w,a,b):
    mx = mem(x,32)
    m[z] = vec([mx,y,w,cst(0x1000,32)])
    m[y] = vec([a,b])
    yy = m(y+y).simplify()
    assert len(yy.l)==3
    assert (b+a) in yy
    m[a] = m(z+y)
    mm = m.use(a=1,b=1)
    assert mm(a) == mm(z+1)

def test_use(m,x,y):
    mx = mem(x+12,32)
    m[y] = mx
    mm = m.use(x=0x1000)
    assert mm[y].a.base == 0x1000
    assert mm[y].a.disp == 12

def test_assume(m,r,w,x,y):
    m[r] = w+3
    mm = m.assume([x==3,w==0,y>0])
    assert mm[r]==3
    assert mm.conds[2]==(y>0)

def test_merge(m,r,w,x,y,a,b):
    m[r] = w+3
    mm = m.assume([x==3,w==0,y>0])
    m2 = mapper()
    m2[r] = a+b
    mm2 = m2.assume([w==1,y<0])
    mm3 = merge(mm,mm2)
    assert mm3(r)._is_vec
    assert mm3(r).l[0] == 0x3
    m3 = mapper()
    m3[r] = x
    m3[w] = cst(0x1000,32)
    mm4 = merge(mm3,m3)
    mm4w = mm4(w)
    assert mm4w._is_vec
    assert w in mm4w
    assert 0x1000 in mm4w

def test_pickle_mapper(a,m):
    from pickle import dumps,loads,HIGHEST_PROTOCOL
    pickler = lambda x: dumps(x,HIGHEST_PROTOCOL)
    x = cst(0x1,32)
    m[a] = a+3
    m[mem(a,8)] = x[0:8]
    m.conds.append(a==0)
    p = pickler(m)
    w = loads(p)
    assert w.conds[0]==(a==0)
    assert w(a)==(a+3)
    M = w.mmap
    parts = M.read(ptr(w(a)),1)
    assert len(parts)==1
    assert parts[0]==x[0:8]

