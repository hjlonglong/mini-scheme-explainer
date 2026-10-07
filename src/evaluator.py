"""求值器：表达式 → 值（解释器的心脏，spec §9）。

evaluate 与 apply 互相递归：
- evaluate 处理符号引用与特殊形式（quote/if/cond/and/or/define/lambda/let/begin），
  其余表达式是函数调用——先求值操作符和全部实参，再交给 apply；
- apply 调用内置过程，或为闭包新建一层环境（外层指向定义时的环境，
  词法作用域）求值函数体。
"""

from stdlib import install_builtins
from env import Environment
from parser import DottedList
from values import BuiltinProc, Closure, NIL, Pair, SchemeError, Symbol


def make_global_env(out):
    """构造初始环境：安装 spec §5 的全部内置过程。"""
    env = Environment()
    install_builtins(env, out)
    return env


def is_truthy(value):
    """只有 #f 是假；0、()、"" 均为真（spec §9）。"""
    return value is not False


def evaluate(expr, env):
    """求值一个表达式。"""
    if isinstance(expr, Symbol):
        return env.lookup(expr.name)
    if isinstance(expr, (int, float, bool, str)):
        return expr  # 自求值字面量
    if expr is NIL:
        return NIL  # 空表字面量
    if isinstance(expr, DottedList):
        raise SchemeError("dotted pair cannot be evaluated as code")
    if isinstance(expr, list):
        return _eval_list(expr, env)
    raise SchemeError(f"cannot evaluate: {expr!r}")


def _eval_list(expr, env):
    """求值括号表达式：特殊形式按各自规则，其余按函数调用处理。"""
    if not expr:
        return NIL
    head = expr[0]
    if isinstance(head, Symbol) and head.name in SPECIAL_FORMS:
        return SPECIAL_FORMS[head.name](expr, env)
    proc = evaluate(head, env)
    args = [evaluate(a, env) for a in expr[1:]]
    return apply_proc(proc, args)


def apply_proc(proc, args):
    """调用一个过程：内置过程直接执行；闭包则新建环境求值函数体。"""
    if isinstance(proc, BuiltinProc):
        try:
            return proc.fn(*args)
        except SchemeError:
            raise
        except Exception as exc:  # 如除零等 Python 异常，包装成统一错误
            raise SchemeError(f"{proc.name}: {exc}")
    if isinstance(proc, Closure):
        if len(args) != len(proc.params):
            raise SchemeError(
                f"wrong number of arguments: expected {len(proc.params)}, got {len(args)}")
        call_env = Environment(proc.env)  # 外层指向定义时的环境（词法作用域）
        for name, value in zip(proc.params, args):
            call_env.define(name, value)
        return eval_sequence(proc.body, call_env)
    raise SchemeError(f"not callable: {proc!r}")


def eval_sequence(forms, env):
    """按 begin 语义顺序求值，返回最后一个表达式的结果。"""
    result = None
    for form in forms:
        result = evaluate(form, env)
    return result


def ast_to_value(datum):
    """把 quote 的静态数据转成运行时值：嵌套列表 → 点对链（spec §6、§11）。"""
    if datum is NIL:
        return NIL
    if isinstance(datum, list):
        if not datum:
            return NIL
        return Pair(ast_to_value(datum[0]), ast_to_value(datum[1:]))
    if isinstance(datum, DottedList):
        result = ast_to_value(datum.tail)
        for item in reversed(datum.items):
            result = Pair(ast_to_value(item), result)
        return result
    return datum  # 数字/布尔/字符串/符号 原样保留


def _check_arity(name, expr, lo, hi=None):
    """校验特殊形式的参数个数。"""
    argc = len(expr) - 1
    if hi is None:
        ok = argc == lo
        want = str(lo)
    else:
        ok = lo <= argc <= hi
        want = f"{lo}-{hi}"
    if not ok:
        raise SchemeError(f"{name}: expected {want} argument(s), got {argc}")


# ---------- 特殊形式（spec §4） ----------

def _sf_quote(expr, env):
    _check_arity("quote", expr, 1)
    return ast_to_value(expr[1])


def _sf_if(expr, env):
    _check_arity("if", expr, 2, 3)
    if is_truthy(evaluate(expr[1], env)):
        return evaluate(expr[2], env)
    if len(expr) == 4:
        return evaluate(expr[3], env)
    return None  # 省略假分支 → 无值，不打印（spec §4.2）


def _sf_cond(expr, env):
    for clause in expr[1:]:
        if not isinstance(clause, list) or not clause:
            raise SchemeError("cond: clause must be (test expr...)")
        test = clause[0]
        if isinstance(test, Symbol) and test.name == "else":
            test_value = True  # else 子句兜底
        else:
            test_value = evaluate(test, env)
        if is_truthy(test_value):
            body = clause[1:]
            if not body:
                return test_value  # 子句无表达式 → 返回测试值本身（spec §4.3）
            return eval_sequence(body, env)
    return None  # 全部不匹配（spec §4.3）


def _sf_and(expr, env):
    result = True
    for e in expr[1:]:
        result = evaluate(e, env)
        if result is False:
            return False  # 短路（spec §4.4）
    return result


def _sf_or(expr, env):
    for e in expr[1:]:
        result = evaluate(e, env)
        if result is not False:
            return result  # 短路（spec §4.4）
    return False


def _sf_define(expr, env):
    if len(expr) < 3:
        raise SchemeError("define: name and expression required")
    target = expr[1]
    if isinstance(target, list):
        # (define (函数名 参数...) 体...) —— 函数定义简写（spec §4.5）
        if not target or not isinstance(target[0], Symbol):
            raise SchemeError("define: function name must be a symbol")
        proc = Closure(target[1:], expr[2:], env)
        env.define(target[0], proc)
        return target[0]  # define 的结果是被定义的符号名（spec §4.5）
    if not isinstance(target, Symbol):
        raise SchemeError("define: name must be a symbol")
    if len(expr) != 3:
        raise SchemeError("define: variable definition takes exactly one expression")
    value = evaluate(expr[2], env)
    env.define(target, value)
    return target


def _sf_lambda(expr, env):
    params = expr[1]
    if params is NIL:
        params = []
    if not isinstance(params, list) or \
            not all(isinstance(p, Symbol) for p in params):
        raise SchemeError("lambda: parameter list must be a list of symbols")
    return Closure(params, expr[2:], env)  # 函数体现在不求值（spec §4.6）


def _sf_let(expr, env):
    bindings = expr[1]
    if bindings is NIL:
        bindings = []
    if not isinstance(bindings, list):
        raise SchemeError("let: bindings must be ((name expr) ...)")
    names, values = [], []
    for b in bindings:
        if not isinstance(b, list) or len(b) != 2 or not isinstance(b[0], Symbol):
            raise SchemeError("let: binding must be (name expr)")
        names.append(b[0])
        values.append(evaluate(b[1], env))  # 全部在外层环境求值 → 并行绑定（spec §4.7）
    new_env = Environment(env)
    for name, value in zip(names, values):
        new_env.define(name, value)
    return eval_sequence(expr[2:], new_env)


def _sf_begin(expr, env):
    return eval_sequence(expr[1:], env)


SPECIAL_FORMS = {
    "quote": _sf_quote,
    "if": _sf_if,
    "cond": _sf_cond,
    "and": _sf_and,
    "or": _sf_or,
    "define": _sf_define,
    "lambda": _sf_lambda,
    "let": _sf_let,
    "begin": _sf_begin,
}
