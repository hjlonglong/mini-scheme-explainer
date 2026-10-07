"""mini-Scheme 运行时值的数据表示。

语法树与求值结果共用本模块定义的类型：
- Symbol      ：符号（变量名、操作符名、quote 的数据）
- Pair        ：点对，列表是由点对组成的链（spec §6）
- NIL         ：空表，全语言唯一的空表对象
- Closure     ：用户函数（lambda 产生的闭包，记住定义时环境）
- BuiltinProc ：内置过程（spec §5 的标准函数库）
- SchemeError ：解释器所有可预期错误的统一异常
"""


class SchemeError(Exception):
    """解释器的可预期错误：语法错、类型错、未绑定符号等。"""


class Symbol:
    """符号：一个名字。eq? 对符号按名字比较（spec §5）。"""

    __slots__ = ("name",)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        return isinstance(other, Symbol) and self.name == other.name

    def __hash__(self):
        return hash(self.name)


class Pair:
    """点对：car 与 cdr 两项的组合；列表是点对组成的链（spec §6）。"""

    __slots__ = ("car", "cdr")

    def __init__(self, car, cdr):
        self.car = car
        self.cdr = cdr

    def __repr__(self):
        # 延迟导入，避免与 printer 形成循环依赖
        from printer import to_string
        return to_string(self)


class _NilType:
    """空表类型，全语言只有一个实例 NIL（保证 (eq? '() '()) 为 #t）。"""

    __slots__ = ()

    def __repr__(self):
        return "()"


NIL = _NilType()


class Closure:
    """用户函数（闭包）：参数表 + 函数体 + 定义时所在的环境（词法作用域的关键）。"""

    __slots__ = ("params", "body", "env")

    def __init__(self, params, body, env):
        self.params = params
        self.body = body
        self.env = env

    def __repr__(self):
        return "#<procedure>"


class BuiltinProc:
    """内置过程：名字 + 一个接收实参的 Python 函数。"""

    __slots__ = ("name", "fn")

    def __init__(self, name, fn):
        self.name = name
        self.fn = fn

    def __repr__(self):
        return "#<procedure>"
