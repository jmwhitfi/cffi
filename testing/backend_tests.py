import py
import sys, ctypes
from ffi import FFI

SIZE_OF_INT   = ctypes.sizeof(ctypes.c_int)
SIZE_OF_LONG  = ctypes.sizeof(ctypes.c_long)
SIZE_OF_SHORT = ctypes.sizeof(ctypes.c_short)
SIZE_OF_PTR   = ctypes.sizeof(ctypes.c_void_p)
SIZE_OF_WCHAR = ctypes.sizeof(ctypes.c_wchar)


class BackendTests:

    def test_integer_ranges(self):
        ffi = FFI(backend=self.Backend())
        for (c_type, size) in [('char', 1),
                               ('short', 2),
                               ('short int', 2),
                               ('', 4),
                               ('int', 4),
                               ('long', SIZE_OF_LONG),
                               ('long int', SIZE_OF_LONG),
                               ('long long', 8),
                               ('long long int', 8),
                               ]:
            for unsigned in [None, False, True]:
                c_decl = {None: '',
                          False: 'signed ',
                          True: 'unsigned '}[unsigned] + c_type
                if c_decl == 'char' or c_decl == '':
                    continue
                self._test_int_type(ffi, c_decl, size, unsigned)

    def test_fixedsize_int(self):
        ffi = FFI(backend=self.Backend())
        for size in [1, 2, 4, 8]:
            self._test_int_type(ffi, 'int%d_t' % (8*size), size, False)
            self._test_int_type(ffi, 'uint%d_t' % (8*size), size, True)
        self._test_int_type(ffi, 'intptr_t', SIZE_OF_PTR, False)
        self._test_int_type(ffi, 'uintptr_t', SIZE_OF_PTR, True)
        self._test_int_type(ffi, 'ptrdiff_t', SIZE_OF_PTR, False)
        self._test_int_type(ffi, 'size_t', SIZE_OF_PTR, True)
        self._test_int_type(ffi, 'ssize_t', SIZE_OF_PTR, False)
        self._test_int_type(ffi, 'wchar_t', SIZE_OF_WCHAR, True)

    def _test_int_type(self, ffi, c_decl, size, unsigned):
        if unsigned:
            min = 0
            max = (1 << (8*size)) - 1
        else:
            min = -(1 << (8*size-1))
            max = (1 << (8*size-1)) - 1
        p = ffi.cast(c_decl, min)
        assert p != min       # no __eq__(int)
        assert bool(p) is bool(min)
        assert int(p) == min
        p = ffi.cast(c_decl, max)
        assert int(p) == max
        q = ffi.cast(c_decl, min - 1)
        assert type(q) is type(p) and int(q) == max
        assert q == p         # __eq__(same-type)
        assert hash(q) == hash(p)
        if 'long long' not in c_decl:
            assert q != ffi.cast("long long", min)  # __eq__(other-type)
        py.test.raises(OverflowError, ffi.malloc, c_decl, min - 1)
        py.test.raises(OverflowError, ffi.malloc, c_decl, max + 1)

    def test_new_single_integer(self):
        ffi = FFI(backend=self.Backend())
        p = ffi.malloc("int")     # similar to ffi.malloc("int[1]")
        assert p[0] == 0
        p[0] = -123
        assert p[0] == -123
        p = ffi.malloc("int", -42)
        assert p[0] == -42
        assert repr(p) == "<malloc('int')>"

    def test_new_array_no_arg(self):
        ffi = FFI(backend=self.Backend())
        p = ffi.malloc("int[10]")
        # the object was zero-initialized:
        for i in range(10):
            assert p[i] == 0

    def test_array_indexing(self):
        ffi = FFI(backend=self.Backend())
        p = ffi.malloc("int[10]")
        p[0] = 42
        p[9] = 43
        assert p[0] == 42
        assert p[9] == 43
        py.test.raises(IndexError, "p[10]")
        py.test.raises(IndexError, "p[10] = 44")
        py.test.raises(IndexError, "p[-1]")
        py.test.raises(IndexError, "p[-1] = 44")

    def test_new_array_args(self):
        ffi = FFI(backend=self.Backend())
        # this tries to be closer to C: where we say "int x[5] = {10, 20, ..}"
        # then here we must enclose the items in a list
        p = ffi.malloc("int[5]", [10, 20, 30, 40, 50])
        assert p[0] == 10
        assert p[1] == 20
        assert p[2] == 30
        assert p[3] == 40
        assert p[4] == 50
        p = ffi.malloc("int[4]", [25])
        assert p[0] == 25
        assert p[1] == 0     # follow C convention rather than LuaJIT's
        assert p[2] == 0
        assert p[3] == 0
        p = ffi.malloc("int[4]", [ffi.cast("int", -5)])
        assert p[0] == -5
        assert repr(p) == "<malloc('int[4]')>"

    def test_new_array_varsize(self):
        ffi = FFI(backend=self.Backend())
        p = ffi.malloc("int[]", 10)     # a single integer is the length
        assert p[9] == 0
        py.test.raises(IndexError, "p[10]")
        #
        py.test.raises(TypeError, ffi.malloc, "int[]")
        #
        p = ffi.malloc("int[]", [-6, -7])    # a list is all the items, like C
        assert p[0] == -6
        assert p[1] == -7
        py.test.raises(IndexError, "p[2]")
        assert repr(p) == "<malloc('int[]' length 2)>"
        #
        p = ffi.malloc("int[]", 0)
        py.test.raises(IndexError, "p[0]")
        py.test.raises(ValueError, ffi.malloc, "int[]", -1)
        assert repr(p) == "<malloc('int[]' length 0)>"

    def test_cannot_cast(self):
        ffi = FFI(backend=self.Backend())
        a = ffi.malloc("short int[10]")
        e = py.test.raises(TypeError, ffi.malloc, "long int *", a)
        assert str(e.value) == "cannot convert 'short[10]' to 'long *'"

    def test_new_pointer_to_array(self):
        ffi = FFI(backend=self.Backend())
        a = ffi.malloc("int[4]", [100, 102, 104, 106])
        p = ffi.malloc("int *", a)
        assert p[0] == a
        assert p[0][2] == 104
        p = ffi.cast("int *", a)
        assert p[0] == 100
        assert p[1] == 102
        assert p[2] == 104
        assert p[3] == 106
        # keepalive: a

    def test_pointer_direct(self):
        ffi = FFI(backend=self.Backend())
        p = ffi.cast("int*", 0)
        assert bool(p) is False
        assert p == ffi.cast("int*", 0)
        a = ffi.malloc("int[]", [123, 456])
        p = ffi.cast("int*", a)
        assert bool(p) is True
        assert p == ffi.cast("int*", a)
        assert p != ffi.cast("int*", 0)
        assert p[0] == 123
        assert p[1] == 456

    def test_repr(self):
        ffi = FFI(backend=self.Backend())
        ffi.cdef("struct foo { int a; };")
        p = ffi.cast("unsigned short int", 0)
        assert repr(p) == "<cdata 'unsigned short'>"
        assert repr(type(p)) == "<class 'ffi.CData<unsigned short>'>"
        p = ffi.cast("int*", 0)
        assert repr(p) == "<cdata 'int *'>"
        assert repr(type(p)) == "<class 'ffi.CData<int *>'>"
        #
        p = ffi.malloc("int")
        assert repr(p) == "<malloc('int')>"
        assert repr(type(p)) == "<class 'ffi.MAlloc<int>'>"
        p = ffi.malloc("int*")
        assert repr(p) == "<malloc('int *')>"
        assert repr(type(p)) == "<class 'ffi.MAlloc<int *>'>"
        p = ffi.malloc("int [2]")
        assert repr(p) == "<malloc('int[2]')>"
        assert repr(type(p)) == "<class 'ffi.MAlloc<int[2]>'>"
        p = ffi.malloc("int*[2][3]")
        assert repr(p) == "<malloc('int *[2][3]')>"
        assert repr(type(p)) == "<class 'ffi.MAlloc<int *[2][3]>'>"
        p = ffi.malloc("struct foo")
        assert repr(p) == "<malloc('struct foo')>"
        assert repr(type(p)) == "<class 'ffi.MAlloc<struct foo>'>"
        #
        p = ffi.malloc("int")
        q = ffi.cast("short", p)
        assert repr(q) == "<cdata 'short'>"
        assert repr(type(q)) == "<class 'ffi.CData<short>'>"
        p = ffi.malloc("int*")
        q = ffi.cast("short*", p)
        assert repr(q) == "<cdata 'short *'>"
        assert repr(type(q)) == "<class 'ffi.CData<short *>'>"
        p = ffi.malloc("int [2]")
        q = ffi.cast("int*", p)
        assert repr(q) == "<cdata 'int *'>"
        assert repr(type(q)) == "<class 'ffi.CData<int *>'>"
        p = ffi.malloc("struct foo")
        q = ffi.cast("struct foo *", p)
        assert repr(q) == "<cdata 'struct foo *'>"
        assert repr(type(q)) == "<class 'ffi.CData<struct foo *>'>"
        q = q[0]
        assert repr(q) == "<cdata 'struct foo'>"
        assert repr(type(q)) == "<class 'ffi.CData<struct foo>'>"

    def test_new_array_of_array(self):
        ffi = FFI(backend=self.Backend())
        p = ffi.malloc("int[3][4]")
        p[0][0] = 10
        p[2][3] = 33
        assert p[0][0] == 10
        assert p[2][3] == 33
        py.test.raises(IndexError, "p[1][-1]")

    def test_constructor_array_of_array(self):
        py.test.skip("not supported with the ctypes backend")
        p = ffi.malloc("int[2][3]", [[10, 11], [12, 13], [14, 15]])
        assert p[1][2] == 15

    def test_new_array_of_pointer_1(self):
        ffi = FFI(backend=self.Backend())
        n = ffi.malloc("int", 99)
        p = ffi.malloc("int*[4]")
        p[3] = n
        a = p[3]
        assert repr(a) == "<cdata 'int *'>"
        assert a[0] == 99

    def test_new_array_of_pointer_2(self):
        ffi = FFI(backend=self.Backend())
        n = ffi.malloc("int[1]", [99])
        p = ffi.malloc("int*[4]")
        p[3] = n
        a = p[3]
        assert repr(a) == "<cdata 'int *'>"
        assert a[0] == 99

    def test_char(self):
        ffi = FFI(backend=self.Backend())
        assert ffi.malloc("char", "\xff")[0] == '\xff'
        assert ffi.malloc("char")[0] == '\x00'
        assert int(ffi.cast("char", 300)) == 300 - 256
        assert bool(ffi.malloc("char"))
        py.test.raises(TypeError, ffi.malloc, "char", 32)
        p = ffi.malloc("char[]", ['a', 'b', '\x9c'])
        assert len(p) == 3
        assert p[0] == 'a'
        assert p[1] == 'b'
        assert p[2] == '\x9c'
        p[0] = '\xff'
        assert p[0] == '\xff'
        p = ffi.malloc("char[]", "abcd")
        assert len(p) == 5
        assert p[4] == '\x00'    # like in C, with:  char[] p = "abcd";

    def test_none_as_null(self):
        ffi = FFI(backend=self.Backend())
        p = ffi.malloc("int*[1]")
        assert p[0] is None
        #
        n = ffi.malloc("int", 99)
        p = ffi.malloc("int*[]", [n])
        assert p[0][0] == 99
        p[0] = None
        assert p[0] is None

    def test_float(self):
        ffi = FFI(backend=self.Backend())
        p = ffi.malloc("float[]", [-2, -2.5])
        assert p[0] == -2.0
        assert p[1] == -2.5
        p[1] += 17.75
        assert p[1] == 15.25
        #
        p = ffi.malloc("float", 15.75)
        assert p[0] == 15.75
        py.test.raises(TypeError, int, p)
        py.test.raises(TypeError, float, p)
        p[0] = 0.0
        assert bool(p) is True
        #
        p = ffi.malloc("float", 1.1)
        f = p[0]
        assert f != 1.1      # because of rounding effect
        assert abs(f - 1.1) < 1E-7
        #
        INF = 1E200 * 1E200
        assert 1E200 != INF
        p[0] = 1E200
        assert p[0] == INF     # infinite, not enough precision

    def test_struct_simple(self):
        ffi = FFI(backend=self.Backend())
        ffi.cdef("struct foo { int a; short b, c; };")
        s = ffi.malloc("struct foo")
        assert s.a == s.b == s.c == 0
        s.b = -23
        assert s.b == -23
        py.test.raises(OverflowError, "s.b = 32768")
        #
        s = ffi.malloc("struct foo", [-2, -3])
        assert s.a == -2
        assert s.b == -3
        assert s.c == 0
        py.test.raises((AttributeError, TypeError), "del s.a")
        assert repr(s) == "<malloc('struct foo')>"
        #
        py.test.raises(ValueError, ffi.malloc, "struct foo", [1, 2, 3, 4])

    def test_constructor_struct_from_dict(self):
        py.test.skip("in-progress?")
        ffi = FFI(backend=self.Backend())
        ffi.cdef("struct foo { int a; short b, c; };")
        s = ffi.malloc("struct foo", {'b': 123, 'c': 456})
        assert s.a == 0
        assert s.b == 123
        assert s.c == 456

    def test_struct_opaque(self):
        ffi = FFI(backend=self.Backend())
        py.test.raises(TypeError, ffi.malloc, "struct baz")
        p = ffi.malloc("struct baz *")    # this works
        assert p[0] is None

    def test_pointer_to_struct(self):
        ffi = FFI(backend=self.Backend())
        ffi.cdef("struct foo { int a; short b, c; };")
        s = ffi.malloc("struct foo")
        s.a = -42
        assert s[0].a == -42
        p = ffi.malloc("struct foo *", s)
        assert p[0].a == -42
        assert p[0][0].a == -42
        p.a = -43
        assert s.a == -43
        assert s[0].a == -43
        p[0].a = -44
        assert s.a == -44
        assert s[0].a == -44
        s.a = -45
        assert p[0].a == -45
        assert p[0][0].a == -45
        s[0].a = -46
        assert p[0].a == -46
        assert p[0][0].a == -46

    def test_constructor_struct_of_array(self):
        py.test.skip("not supported with the ctypes backend")
        ffi = FFI(backend=self.Backend())
        ffi.cdef("struct foo { int a[2]; char b[3]; };")
        s = ffi.malloc("struct foo", [[10, 11], ['a', 'b', 'c']])
        assert s.a[1] == 11
        assert s.b[2] == 'c'
        s.b[1] = 'X'
        assert s.b[0] == 'a'
        assert s.b[1] == 'X'
        assert s.b[2] == 'c'

    def test_union_simple(self):
        ffi = FFI(backend=self.Backend())
        ffi.cdef("union foo { int a; short b, c; };")
        u = ffi.malloc("union foo")
        assert u.a == u.b == u.c == 0
        u.b = -23
        assert u.b == -23
        assert u.a != 0
        py.test.raises(OverflowError, "u.b = 32768")
        #
        u = ffi.malloc("union foo", -2)
        assert u.a == -2
        py.test.raises((AttributeError, TypeError), "del u.a")
        assert repr(u) == "<malloc('union foo')>"

    def test_union_opaque(self):
        ffi = FFI(backend=self.Backend())
        py.test.raises(TypeError, ffi.malloc, "union baz")
        u = ffi.malloc("union baz *")   # this works
        assert u[0] is None

    def test_sizeof_type(self):
        ffi = FFI(backend=self.Backend())
        ffi.cdef("""
            struct foo { int a; short b, c, d; };
            union foo { int a; short b, c, d; };
        """)
        for c_type, expected_size in [
            ('char', 1),
            ('unsigned int', 4),
            ('char *', SIZE_OF_LONG),
            ('int[5]', 20),
            ('struct foo', 12),
            ('union foo', 4),
            ]:
            size = ffi.sizeof(c_type)
            assert size == expected_size

    def test_sizeof_cdata(self):
        ffi = FFI(backend=self.Backend())
        assert ffi.sizeof(ffi.malloc("short")) == SIZE_OF_PTR
        assert ffi.sizeof(ffi.cast("short", 123)) == SIZE_OF_SHORT
        #
        a = ffi.malloc("int[]", [10, 11, 12, 13, 14])
        assert len(a) == 5
        assert ffi.sizeof(a) == 5 * SIZE_OF_INT

    def test_string_from_char_array(self):
        ffi = FFI(backend=self.Backend())
        assert str(ffi.cast("char", "x")) == "x"
        p = ffi.malloc("char[]", "hello.")
        p[5] = '!'
        assert str(p) == "hello!"
        p[6] = '?'
        assert str(p) == "hello!?"
        p[3] = '\x00'
        assert str(p) == "hel"
        py.test.raises(IndexError, "p[7] = 'X'")
        #
        a = ffi.malloc("char[]", "hello\x00world")
        assert len(a) == 12
        p = ffi.cast("char *", a)
        assert str(p) == 'hello'

    def test_fetch_const_char_p_field(self):
        # 'const' is ignored so far
        ffi = FFI(backend=self.Backend())
        ffi.cdef("struct foo { const char *name; };")
        t = ffi.malloc("const char[]", "testing")
        s = ffi.malloc("struct foo", [t])
        assert type(s.name) is not str
        assert str(s.name) == "testing"
        s.name = None
        assert s.name is None

    def test_voidp(self):
        ffi = FFI(backend=self.Backend())
        py.test.raises(TypeError, ffi.malloc, "void")
        p = ffi.malloc("void *")
        assert p[0] is None
        a = ffi.malloc("int[]", [10, 11, 12])
        p = ffi.malloc("void *", a)
        vp = p[0]
        py.test.raises(TypeError, "vp[0]")
        py.test.raises(TypeError, ffi.malloc, "short *", a)
        #
        ffi.cdef("struct foo { void *p; int *q; short *r; };")
        s = ffi.malloc("struct foo")
        s.p = a    # works
        s.q = a    # works
        py.test.raises(TypeError, "s.r = a")    # fails
        b = ffi.cast("int *", a)
        s.p = b    # works
        s.q = b    # works
        py.test.raises(TypeError, "s.r = b")    # fails

    def test_functionptr_simple(self):
        ffi = FFI(backend=self.Backend())
        py.test.raises(TypeError, ffi.malloc, "int()(int)")
        py.test.raises(TypeError, ffi.malloc, "int()(int)", 0)
        def cb(n):
            return n + 1
        p = ffi.malloc("int()(int)", cb)
        res = p(41)     # calling an 'int(*)(int)', i.e. a function pointer
        assert res == 42 and type(res) is int
        res = p(ffi.cast("int", -41))
        assert res == -40 and type(res) is int
        assert repr(p).startswith(
            "<malloc('int()(int)' calling <function cb at 0x")
        assert ffi.typeof(p) is ffi.typeof("int(*)(int)")
        q = ffi.malloc("int(*)(int)", p)
        assert repr(q) == "<malloc('int(*)(int)')>"
        py.test.raises(TypeError, "q(43)")
        res = q[0](43)
        assert res == 44
        q = ffi.cast("int(*)(int)", p)
        assert repr(q) == "<cdata 'int(*)(int)'>"
        res = q(45)
        assert res == 46

    def test_char_cast(self):
        ffi = FFI(backend=self.Backend())
        p = ffi.cast("int", '\x01')
        assert type(p) is ffi.typeof("int")
        assert int(p) == 1
        p = ffi.cast("int", ffi.cast("char", "a"))
        assert int(p) == ord("a")
        p = ffi.cast("int", ffi.cast("char", "\x80"))
        assert int(p) == 0x80     # "char" is considered unsigned in this case
        p = ffi.cast("int", "\x81")
        assert int(p) == 0x81

    def test_cast_array_to_charp(self):
        ffi = FFI(backend=self.Backend())
        a = ffi.malloc("short int[]", [0x1234, 0x5678])
        p = ffi.cast("char*", a)
        data = ''.join([p[i] for i in range(4)])
        if sys.byteorder == 'little':
            assert data == '\x34\x12\x78\x56'
        else:
            assert data == '\x12\x34\x56\x78'

    def test_cast_between_pointers(self):
        ffi = FFI(backend=self.Backend())
        a = ffi.malloc("short int[]", [0x1234, 0x5678])
        p = ffi.cast("short*", a)
        q = ffi.cast("char*", p)
        data = ''.join([q[i] for i in range(4)])
        if sys.byteorder == 'little':
            assert data == '\x34\x12\x78\x56'
        else:
            assert data == '\x12\x34\x56\x78'

    def test_cast_pointer_and_int(self):
        ffi = FFI(backend=self.Backend())
        a = ffi.malloc("short int[]", [0x1234, 0x5678])
        l1 = ffi.cast("intptr_t", a)
        p = ffi.cast("short*", a)
        l2 = ffi.cast("intptr_t", p)
        assert l1 == l2
        assert int(l1) == int(l2) != 0
        q = ffi.cast("short*", l1)
        assert q == ffi.cast("short*", int(l1))
        assert q[0] == 0x1234

    def test_cast_functionptr_and_int(self):
        ffi = FFI(backend=self.Backend())
        def cb(n):
            return n + 1
        a = ffi.malloc("int()(int)", cb)
        p = ffi.cast("void *", a)
        assert p
        b = ffi.cast("int(*)(int)", p)
        assert b(41) == 42
        assert a == b
        assert hash(a) == hash(b)

    def test_enum(self):
        ffi = FFI(backend=self.Backend())
        ffi.cdef("enum foo { A, B, C, D };")
        assert int(ffi.cast("enum foo", "A")) == 0
        assert int(ffi.cast("enum foo", "B")) == 1
        assert int(ffi.cast("enum foo", "C")) == 2
        assert int(ffi.cast("enum foo", "D")) == 3
        ffi.cdef("enum bar { A, B=-2, C, D };")
        assert int(ffi.cast("enum bar", "A")) == 0
        assert int(ffi.cast("enum bar", "B")) == -2
        assert int(ffi.cast("enum bar", "C")) == -1
        assert int(ffi.cast("enum bar", "D")) == 0
        assert ffi.cast("enum bar", "B") == ffi.cast("enum bar", "B")
        assert ffi.cast("enum bar", "B") != ffi.cast("enum bar", "C")
        assert ffi.cast("enum bar", "A") == ffi.cast("enum bar", "D")
        assert ffi.cast("enum foo", "A") != ffi.cast("enum bar", "A")
        assert ffi.cast("enum bar", "A") != ffi.cast("int", 0)
        assert repr(ffi.cast("enum bar", "C")) == "<cdata 'enum bar'>"

    def test_enum_in_struct(self):
        ffi = FFI(backend=self.Backend())
        ffi.cdef("enum foo { A, B, C, D }; struct bar { enum foo e; };")
        s = ffi.malloc("struct bar")
        s.e = "D"
        assert s.e == "D"
        assert s[0].e == "D"
        s[0].e = "C"
        assert s.e == "C"
        assert s[0].e == "C"

    def test_offsetof(self):
        ffi = FFI(backend=self.Backend())
        ffi.cdef("struct foo { int a, b, c; };")
        assert ffi.offsetof("struct foo", "a") == 0
        assert ffi.offsetof("struct foo", "b") == 4
        assert ffi.offsetof("struct foo", "c") == 8

    def test_alignof(self):
        ffi = FFI(backend=self.Backend())
        ffi.cdef("struct foo { char a; short b; char c; };")
        assert ffi.alignof("int") == 4
        assert ffi.alignof("double") in (4, 8)
        assert ffi.alignof("struct foo") == 2

    def test_bitfield(self):
        ffi = FFI(backend=self.Backend())
        ffi.cdef("struct foo { int a:10, b:20, c:3; };")
        assert ffi.sizeof("struct foo") == 8
        s = ffi.malloc("struct foo")
        s.a = 511
        py.test.raises(OverflowError, "s.a = 512")
        py.test.raises(OverflowError, "s[0].a = 512")
        assert s.a == 511
        s.a = -512
        py.test.raises(OverflowError, "s.a = -513")
        py.test.raises(OverflowError, "s[0].a = -513")
        assert s.a == -512
        s.c = 3
        assert s.c == 3
        py.test.raises(OverflowError, "s.c = 4")
        py.test.raises(OverflowError, "s[0].c = 4")
        s.c = -4
        assert s.c == -4

    def test_pointer_arithmetic(self):
        ffi = FFI(backend=self.Backend())
        s = ffi.malloc("short[]", range(100, 110))
        p = ffi.cast("short *", s)
        assert p[2] == 102
        assert p+1 == p+1
        assert p+1 != p+0
        assert p == p+0 == p-0
        assert (p+1)[0] == 101
        assert (p+19)[-10] == 109
        assert (p+5) - (p+1) == 4
        assert p == s+0
        assert p+1 == s+1

    def test_ffi_string(self):
        ffi = FFI(backend=self.Backend())
        a = ffi.malloc("int[]", range(100, 110))
        s = ffi.string(ffi.cast("void *", a), 8)
        assert type(s) is str
        if sys.byteorder == 'little':
            assert s == '\x64\x00\x00\x00\x65\x00\x00\x00'
        else:
            assert s == '\x00\x00\x00\x64\x00\x00\x00\x65'
