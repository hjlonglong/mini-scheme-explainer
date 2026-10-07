"""入口：读文件或标准输入，逐表达式求值并打印结果（spec §2）。

- 每个顶层表达式的求值结果独占一行；
- 结果为 None（如 display、newline）时不打印；
- 多个文件共享同一个全局环境（后一文件可见前一文件的 define）。
"""

import sys

from evaluator import make_global_env, evaluate
from lexer import tokenize
from parser import Parser
from printer import to_string
from values import SchemeError


def run(source, env, out):
    """求值一段程序文本，把每个结果写入 out 流。"""
    source = source.lstrip("\ufeff")  # 容忍文件开头的 UTF-8 BOM
    for expr in Parser(tokenize(source)).parse_all():
        result = evaluate(expr, env)
        if result is not None:
            out.write(to_string(result) + "\n")
            out.flush()


def main(argv):
    out = sys.stdout
    env = make_global_env(out)  # 所有输入共享一个全局环境（spec §2）
    if argv:
        for path in argv:
            with open(path, "r", encoding="utf-8") as source_file:
                run(source_file.read(), env, out)
    else:
        run(sys.stdin.read(), env, out)


def _normalize_streams():
    """统一输出换行为 \\n、编码为 UTF-8，保证跨平台逐字节一致。

    Windows 下文本流默认把 \\n 翻译成 \\r\\n，会导致输出与期望不符。
    """
    for stream, newline in ((sys.stdout, "\n"), (sys.stderr, None),
                            (sys.stdin, None)):
        if hasattr(stream, "reconfigure"):
            try:
                if newline is None:
                    stream.reconfigure(encoding="utf-8")
                else:
                    stream.reconfigure(encoding="utf-8", newline=newline)
            except (OSError, ValueError):
                pass


if __name__ == "__main__":
    _normalize_streams()
    try:
        main(sys.argv[1:])
    except SchemeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:  # 未预期错误也给出干净提示，而非裸 traceback
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
