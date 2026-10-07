"""打印：把值转换为文本（spec §8）。

- to_string      ：write 语义，字符串带引号、控制字符转义；
- display_text   ：display 语义，字符串原样输出，其余与 to_string 一致；
- 点对链打印成真列表 (1 2 3) 或点对 (1 . 2)，并带环检测防御。
"""

from values import BuiltinProc, Closure, NIL, Pair, SchemeError, Symbol

# 字符串输出时的转义（spec §8：换行/制表符等打印为转义形式）
_STRING_ESCAPES = [
    ("\\", "\\\\"),
    ('"', '\\"'),
    ("\n", "\\n"),
    ("\t", "\\t"),
    ("\r", "\\r"),
]


def to_string(value, _seen=None):
    """把值转换为可读文本（write 语义）。"""
    if value is NIL:
        return "()"
    if value is True:
        return "#t"
    if value is False:
        return "#f"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, Symbol):
        return value.name
    if isinstance(value, str):
        return '"' + _escape(value) + '"'
    if isinstance(value, (Closure, BuiltinProc)):
        return "#<procedure>"
    if isinstance(value, Pair):
        return _pair_to_string(value, _seen if _seen is not None else set())
    raise SchemeError(f"cannot print value of type: {type(value).__name__}")


def display_text(value):
    """display 语义：字符串原样输出，其余与 to_string 一致（spec §5）。"""
    if isinstance(value, str):
        return value
    return to_string(value)


def _escape(s):
    for raw, escaped in _STRING_ESCAPES:
        s = s.replace(raw, escaped)
    return s


def _pair_to_string(pair, seen):
    """点对链 → 列表文本：尾项是空表打印成列表，否则打印成点对。"""
    parts = []
    cur = pair
    while isinstance(cur, Pair):
        pid = id(cur)
        if pid in seen:  # 环检测：本语言无法构造环，仅作防御
            parts.append("...")
            break
        seen.add(pid)
        parts.append(to_string(cur.car, seen))
        cur = cur.cdr
    if cur is not NIL:
        parts.append(".")
        parts.append(to_string(cur, seen))
    return "(" + " ".join(parts) + ")"
