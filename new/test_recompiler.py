from recompiler import Recompiler, make_c_source
from cffi1 import FFI
from udir import udir


def check_type_table(input, expected_output):
    ffi = FFI()
    ffi.cdef(input)
    recompiler = Recompiler(ffi, 'testmod')
    recompiler.collect_type_table()
    assert ''.join(map(str, recompiler.cffi_types)) == expected_output

def test_type_table_func():
    check_type_table("double sin(double);",
                     "(FUNCTION 1)(PRIMITIVE 14)(FUNCTION_END 0)")
    check_type_table("float sin(double);",
                     "(FUNCTION 3)(PRIMITIVE 14)(FUNCTION_END 0)(PRIMITIVE 13)")
    check_type_table("float sin(void);",
                     "(FUNCTION 2)(FUNCTION_END 0)(PRIMITIVE 13)")
    check_type_table("double sin(float); double cos(float);",
                     "(FUNCTION 3)(PRIMITIVE 13)(FUNCTION_END 0)(PRIMITIVE 14)")
    check_type_table("double sin(float); double cos(double);",
                     "(FUNCTION 1)(PRIMITIVE 14)(FUNCTION_END 0)"   # cos
                     "(FUNCTION 1)(PRIMITIVE 13)(FUNCTION_END 0)")  # sin
    check_type_table("float sin(double); float cos(float);",
                     "(FUNCTION 4)(PRIMITIVE 14)(FUNCTION_END 0)"   # sin
                     "(FUNCTION 4)(PRIMITIVE 13)(FUNCTION_END 0)")  # cos

def test_use_noop_for_repeated_args():
    check_type_table("double sin(double *, double *);",
                     "(FUNCTION 4)(POINTER 4)(NOOP 1)(FUNCTION_END 0)"
                     "(PRIMITIVE 14)")
    check_type_table("double sin(double *, double *, double);",
                     "(FUNCTION 3)(POINTER 3)(NOOP 1)(PRIMITIVE 14)"
                     "(FUNCTION_END 0)")

def test_dont_use_noop_for_primitives():
    check_type_table("double sin(double, double);",
                     "(FUNCTION 1)(PRIMITIVE 14)(PRIMITIVE 14)(FUNCTION_END 0)")

def test_funcptr_as_argument():
    check_type_table("int sin(double(float));",
                     "(FUNCTION 6)(PRIMITIVE 13)(FUNCTION_END 0)"
                     "(FUNCTION 7)(POINTER 0)(FUNCTION_END 0)"
                     "(PRIMITIVE 14)(PRIMITIVE 7)")

def test_variadic_function():
    check_type_table("int sin(int, ...);",
                     "(FUNCTION 1)(PRIMITIVE 7)(FUNCTION_END 1)")

def test_array():
    check_type_table("int a[100];",
                     "(PRIMITIVE 7)(ARRAY 0)(None 100)")

def test_typedef():
    check_type_table("typedef int foo_t;",
                     "(PRIMITIVE 7)")

def test_prebuilt_type():
    check_type_table("int32_t f(void);",
                     "(FUNCTION 2)(FUNCTION_END 0)(PRIMITIVE 21)")


def test_math_sin():
    ffi = FFI()
    ffi.cdef("float sin(double); double cos(double);")
    make_c_source(ffi, str(udir.join('math_sin.c')), '#include <math.h>')

def test_global_var_array():
    ffi = FFI()
    ffi.cdef("int a[100];")
    make_c_source(ffi, str(udir.join('global_var_array.c')), 'int a[100];')

def test_typedef():
    ffi = FFI()
    ffi.cdef("typedef int **foo_t;")
    make_c_source(ffi, str(udir.join('typedef.c')), 'typedef int **foo_t;')
