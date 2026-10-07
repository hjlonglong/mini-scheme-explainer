"""环境：变量绑定表 + 指向外层环境的指针（词法作用域的关键）。

define 只作用于当前环境；lookup 沿外层链逐层查找，找不到则报错。
"""

from values import SchemeError, Symbol


class Environment:
    """一层环境：本层绑定表 + 外层环境引用。"""

    def __init__(self, parent=None):
        self.parent = parent
        self.bindings = {}

    def lookup(self, name):
        """沿环境链向外查找符号的值；找不到抛出 SchemeError。"""
        if isinstance(name, Symbol):
            name = name.name
        env = self
        while env is not None:
            if name in env.bindings:
                return env.bindings[name]
            env = env.parent
        raise SchemeError(f"unbound symbol: {name}")

    def define(self, name, value):
        """在当前环境绑定（define 只影响当前层，不修改外层）。"""
        if isinstance(name, Symbol):
            name = name.name
        self.bindings[name] = value
