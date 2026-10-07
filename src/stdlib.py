"""内置库：spec §5 的全部内置过程，安装进初始环境。

内置过程与特殊形式不同：实参先全部求值，再交给这里的 Python 函数。
display / newline 直接写入解释器的输出流（由 install_builtins 传入）。
"""

from printer import display_text, to_string
from values import BuiltinProc, Closure, NIL, Pair, SchemeError, Symbol


def install_builtins(env, out):
    """把全部内置过程绑定到环境 env，输出过程写 out 流。"""

    def register(name, fn):
        env.define(name, BuiltinProc(name, fn))

    # ---------- 算术（可变参数，spec §5） ----------

    def add(*args):
        _ensure_all_numbers("+", args)
        return sum(args) if args else 0

    def sub(*args):
        _ensure_all_numbers("-", args)
        if not args:
            raise SchemeError("- needs at least 1 argument")
        if len(args) == 1:
            return -args[0]  # 单参数取反
        result = args[0]
        for a in args[1:]:
            result -= a
        return result

    def mul(*args):
        _ensure_all_numbers("*", args)
        result = 1
        for a in args:
            result *= a
        return result

    def div(*args):
        _ensure_all_numbers("/", args)
        if not args:
            raise SchemeError("/ needs at least 1 argument")
        if len(args) == 1:
            return 1.0 / args[0]  # 单参数：倒数（浮点，spec §5）
        result = args[0]
        for b in args[1:]:
            if isinstance(result, int) and isinstance(b, int):
                result = _div_trunc(result, b)  # 整数相除得整数商，负数向零截断
            else:
                result = result / b
        return result

    def modulo(a, b):
        _ensure_all_numbers("modulo", (a, b))
        return a % b  # Python 取模结果的符号跟随除数，与 Scheme 一致

    def quotient(a, b):
        _ensure_all_numbers("quotient", (a, b))
        return _div_trunc(a, b)

    def expt(a, b):
        _ensure_all_numbers("expt", (a, b))
        return a ** b

    def abs_proc(a):
        _ensure_all_numbers("abs", (a,))
        return abs(a)

    # ---------- 比较（链式，支持数字与符号，spec §5） ----------

    def make_chain(name, op):
        """相邻两两比较都成立才为真。"""
        def chain(*args):
            for a, b in zip(args, args[1:]):
                if not op(_cmp_values(a, b)):
                    return False
            return True
        chain.__name__ = name
        return chain

    def not_proc(x):
        return x is False  # 只有 #f 是假（spec §9）

    # ---------- 列表（点对链，spec §6） ----------

    def cons(a, b):
        return Pair(a, b)

    def car(p):
        _require_pair("car", p)
        return p.car

    def cdr(p):
        _require_pair("cdr", p)
        return p.cdr

    def list_proc(*args):
        result = NIL
        for a in reversed(args):
            result = Pair(a, result)
        return result

    def length(xs):
        return len(_proper_list_items("length", xs))

    def append_proc(*lists):
        result = NIL
        for xs in reversed(lists):
            for a in reversed(_proper_list_items("append", xs)):
                result = Pair(a, result)
        return result

    def null_proc(x):
        return x is NIL

    def pair_proc(x):
        return isinstance(x, Pair)

    def list_pred(x):
        """是否真列表：空表是；点对链须以空表结尾（spec §5）。"""
        if x is NIL:
            return True
        if not isinstance(x, Pair):
            return False
        seen = set()
        cur = x
        while isinstance(cur, Pair):
            if id(cur) in seen:
                return False
            seen.add(id(cur))
            cur = cur.cdr
        return cur is NIL

    # ---------- 谓词（spec §5） ----------

    def number_pred(x):
        return isinstance(x, (int, float)) and not isinstance(x, bool)

    def boolean_pred(x):
        return isinstance(x, bool)

    def symbol_pred(x):
        return isinstance(x, Symbol)

    def string_pred(x):
        return isinstance(x, str)

    def procedure_pred(x):
        return isinstance(x, (Closure, BuiltinProc))

    def zero_pred(x):
        _ensure_all_numbers("zero?", (x,))
        return x == 0

    def even_pred(x):
        _ensure_all_numbers("even?", (x,))
        return x % 2 == 0

    def odd_pred(x):
        _ensure_all_numbers("odd?", (x,))
        return x % 2 != 0

    def eq_pred(a, b):
        """符号/数字/布尔/字符串按值比较；复合数据按同一性（spec §5）。"""
        if a is NIL or b is NIL:
            return a is b  # 空表是唯一对象
        if type(a) is not type(b):
            return False  # 先比类型，防止 True == 1 之类（spec §11）
        if isinstance(a, (Symbol, str, int, float, bool)):
            return a == b
        return a is b  # 点对、过程等复合数据：是否同一对象

    def equal_pred(a, b, _seen=None):
        """结构相等：逐层比较（spec §5）。"""
        if type(a) is not type(b):
            return False
        if isinstance(a, (int, float, bool, Symbol, str)):
            return a == b
        if a is NIL:
            return b is NIL
        if isinstance(a, Pair):
            if _seen is None:
                _seen = set()
            if id(a) in _seen:
                return True  # 环（防御，本语言构造不出）
            _seen.add(id(a))
            return equal_pred(a.car, b.car, _seen) and equal_pred(a.cdr, b.cdr, _seen)
        return a is b  # 过程按同一性兜底

    # ---------- 输出（spec §5） ----------

    def display_proc(value):
        out.write(display_text(value))
        out.flush()
        return None  # 无值 → 顶层不打印（spec §2）

    def newline_proc():
        out.write("\n")
        out.flush()
        return None

    register("+", add)
    register("-", sub)
    register("*", mul)
    register("/", div)
    register("modulo", modulo)
    register("quotient", quotient)
    register("expt", expt)
    register("abs", abs_proc)
    register("=", make_chain("=", lambda c: c == 0))
    register("<", make_chain("<", lambda c: c < 0))
    register(">", make_chain(">", lambda c: c > 0))
    register("<=", make_chain("<=", lambda c: c <= 0))
    register(">=", make_chain(">=", lambda c: c >= 0))
    register("not", not_proc)
    register("cons", cons)
    register("car", car)
    register("cdr", cdr)
    register("list", list_proc)
    register("length", length)
    register("append", append_proc)
    register("null?", null_proc)
    register("pair?", pair_proc)
    register("list?", list_pred)
    register("number?", number_pred)
    register("boolean?", boolean_pred)
    register("symbol?", symbol_pred)
    register("string?", string_pred)
    register("procedure?", procedure_pred)
    register("zero?", zero_pred)
    register("even?", even_pred)
    register("odd?", odd_pred)
    register("eq?", eq_pred)
    register("equal?", equal_pred)
    register("display", display_proc)
    register("newline", newline_proc)


def _div_trunc(a, b):
    """整数商，负数商向零截断：7/2=3，-7/2=-3（spec §5）。"""
    if b == 0:
        raise SchemeError("division by zero")
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


def _cmp_values(a, b):
    """比较两个值，返回 -1/0/1：数字按数值，符号按名字，字符串按内容，布尔按序。"""
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) \
            and not isinstance(a, bool) and not isinstance(b, bool):
        return (a > b) - (a < b)
    if isinstance(a, Symbol) and isinstance(b, Symbol):
        return (a.name > b.name) - (a.name < b.name)
    if isinstance(a, str) and isinstance(b, str):
        return (a > b) - (a < b)
    if isinstance(a, bool) and isinstance(b, bool):
        return (a > b) - (a < b)
    raise SchemeError(f"cannot compare: {to_string(a)} and {to_string(b)}")


def _ensure_all_numbers(name, args):
    """参数必须都是数字（布尔不算数，spec §11 的教训）。"""
    for a in args:
        if isinstance(a, bool) or not isinstance(a, (int, float)):
            raise SchemeError(f"{name}: expected number, got {to_string(a)}")


def _require_pair(name, x):
    if not isinstance(x, Pair):
        raise SchemeError(f"{name}: expected pair, got {to_string(x)}")


def _proper_list_items(name, xs):
    """校验 xs 是真列表并返回其元素（Python 列表形式），带环防御。"""
    items = []
    seen = set()
    while xs is not NIL:
        if not isinstance(xs, Pair) or id(xs) in seen:
            raise SchemeError(f"{name}: argument is not a proper list")
        seen.add(id(xs))
        items.append(xs.car)
        xs = xs.cdr
    return items
