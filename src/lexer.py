"""词法分析：把程序文本切成词（token）序列（spec §3）。

支持的词：括号 ( )、引用简写 '、点对记法 .、整数与浮点数、布尔 #t/#f、
字符串（转义 \\n \\t \\" \\\\）、符号；分号 ; 开头到行尾是注释。
"""

import re

from values import SchemeError, Symbol

# 原子（数字/符号）的结束符：空白、括号、引用、分号、双引号
_DELIMITERS = set(" \t\r\n()'\";")

# 数字：可带正负号，小数点前后至少有一边有数字
_NUMBER_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)$")

# 字符串转义表（spec §3）
_STRING_ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}


class Token:
    """一个词：kind 是类别，value 是内容，line 用于报错定位。"""

    __slots__ = ("kind", "value", "line")

    def __init__(self, kind, value, line):
        self.kind = kind
        self.value = value
        self.line = line

    def __repr__(self):
        return f"Token({self.kind!r}, {self.value!r})"


def tokenize(source):
    """把程序文本切成 Token 列表。"""
    tokens = []
    i, n = 0, len(source)
    line = 1
    while i < n:
        c = source[i]
        if c in " \t\r\n":
            if c == "\n":
                line += 1
            i += 1
        elif c == ";":  # 注释：到行尾为止（spec §3）
            while i < n and source[i] not in "\r\n":
                i += 1
        elif c == "(":
            tokens.append(Token("lparen", c, line))
            i += 1
        elif c == ")":
            tokens.append(Token("rparen", c, line))
            i += 1
        elif c == "'":  # 引用简写（spec §3）
            tokens.append(Token("quote", c, line))
            i += 1
        elif c == '"':
            i, text, line = _read_string(source, i, line)
            tokens.append(Token("string", text, line))
        else:
            start = i
            while i < n and source[i] not in _DELIMITERS:
                i += 1
            tokens.append(_classify_atom(source[start:i], line))
    return tokens


def _read_string(source, i, line):
    """从 source[i] == '"' 开始读一个字符串，返回 (新位置, 内容, 新行号)。"""
    i += 1  # 跳过左引号
    n = len(source)
    buf = []
    while i < n:
        c = source[i]
        if c == '"':
            return i + 1, "".join(buf), line
        if c == "\\":
            i += 1
            if i >= n:
                raise SchemeError(f"line {line}: incomplete string escape")
            esc = source[i]
            buf.append(_STRING_ESCAPES.get(esc, "\\" + esc))
            i += 1
        else:
            if c == "\n":
                line += 1
            buf.append(c)
            i += 1
    raise SchemeError(f"line {line}: unterminated string")


def _classify_atom(text, line):
    """判断一个原子是布尔、点、数字还是符号。"""
    if text == "#t":
        return Token("boolean", True, line)
    if text == "#f":
        return Token("boolean", False, line)
    if text == ".":
        return Token("dot", text, line)
    if text.startswith("#"):
        raise SchemeError(f"line {line}: unknown literal {text}")
    if _NUMBER_RE.match(text):
        if "." in text:
            return Token("number", float(text), line)
        return Token("number", int(text), line)
    return Token("symbol", Symbol(text), line)
