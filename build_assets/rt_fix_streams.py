"""Runtime hook: corrige sys.stdin/stdout/stderr quando o app roda sem console.

PyInstaller com console=False deixa esses streams como None. Varias bibliotecas
(jupyter_client, ipykernel, click, tqdm) chamam .fileno() ou .write() neles e
crasham. Substituimos por handles validos para os.devnull, que tem fileno real.
"""
import os
import sys

for name in ("stdin", "stdout", "stderr"):
    if getattr(sys, name, None) is None:
        try:
            mode = "r" if name == "stdin" else "w"
            setattr(sys, name, open(os.devnull, mode, buffering=1, encoding="utf-8"))
        except Exception:
            pass
