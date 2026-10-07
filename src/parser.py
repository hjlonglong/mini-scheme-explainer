"""语法分析：token 序列 → 表达式树（嵌套列表，spec §4）。

- 'x 展开为 (quote x) 简写；
- (a b . c) 点对记法转成 DottedList 节点；
- 数字/布尔/字符串/符号等原子原样保留，由求值器处理。
"""

from values import SchemeError, Symbol


class DottedList:
    """点对记法 (a b . c) 的中间表示：前段元素 + 尾项。"""

    __slots__ = ("items", "tail")

    def __init__(self, items, tail):
        self.items = items
        self.tail = tail

    def __repr__(self):
        return f"DottedList({self.items!r}, {self.tail!r})"


class Parser:
    """递归下降解析器：把 Token 序列解析成嵌套的表达式树。"""

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def parse_all(self):
        """解析到 token 耗尽，返回全部顶层表达式。"""
        exprs = []
        while not self._eof():
            exprs.append(self._datum())
        return exprs

    def _eof(self):
        return self.pos >= len(self.tokens)

    def _peek(self):
        return self.tokens[self.pos]

    def _next(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _datum(self):
        """解析一个完整数据（原子或括号表达式）。"""
        if self._eof():
            raise SchemeError("unexpected end of program")
        tok = self._next()
        if tok.kind == "lparen":
            return self._list()
        if tok.kind == "quote":
            return [Symbol("quote"), self._datum()]
        if tok.kind in ("rparen", "dot"):
            raise SchemeError(f"line {tok.line}: unexpected {tok.value}")
        return tok.value

    def _list(self):
        """解析括号列表，支持 (a b . c) 点对记法。"""
        items = []
        while True:
            if self._eof():
                raise SchemeError("missing closing )")
            if self._peek().kind == "rparen":
                self._next()
                return items
            if self._peek().kind == "dot":
                self._next()
                tail = self._datum()
                if self._eof() or self._peek().kind != "rparen":
                    raise SchemeError("dotted pair: exactly one element and a closing ) expected after .")
                self._next()
                return DottedList(items, tail)
            items.append(self._datum())
