#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import select
import subprocess
import sys
import time


def main() -> None:
    proc = subprocess.Popen(
        ["/readflag"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    assert proc.stdin is not None
    assert proc.stdout is not None

    buf = b""
    expr: str | None = None
    answered = False

    deadline = time.time() + 8.0
    while time.time() < deadline:
        if proc.poll() is not None:
            break

        r, _, _ = select.select([proc.stdout], [], [], 0.25)
        if not r:
            continue

        chunk = os.read(proc.stdout.fileno(), 4096)
        if not chunk:
            break

        sys.stdout.buffer.write(chunk)
        sys.stdout.buffer.flush()

        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            s = line.decode("utf-8", errors="ignore").strip()
            if s.startswith("(") and all(c in "0123456789()+- " for c in s):
                expr = s

        if not answered and (b"input your answer:" in buf or b"input your answer:" in chunk):
            if expr is None:
                raise SystemExit("[audit] no expression captured")
            if not re.fullmatch(r"[0-9()+\-\s]+", expr):
                raise SystemExit(f"[audit] unexpected expression: {expr!r}")
            ans = eval(expr)
            proc.stdin.write(str(ans).encode() + b"\n")
            proc.stdin.flush()
            answered = True

    # Drain any remaining output.
    try:
        rest = proc.communicate(timeout=2.0)[0]
    except Exception:
        proc.kill()
        rest = b""

    if rest:
        sys.stdout.buffer.write(rest)
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
