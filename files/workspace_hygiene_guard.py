#!/usr/bin/env python3
"""pre_tool_call guard: keep the Hermes workspace tidy.

Blocks write_file/patch calls that would create files directly in the
workspace ROOT (/srv/hermes-workspace). Scratch must go in tmp/,
durable work in projects/. Everything else passes untouched.
"""
import json
import os
import sys

WS = "/srv/hermes-workspace"
ALLOWED_TOP = {"projects", "tmp", ".hermes.md"}

def norm(p, cwd):
    p = os.path.expanduser(str(p))
    if not os.path.isabs(p):
        p = os.path.join(cwd or "/", p)
    return os.path.normpath(p)

def main():
    payload = json.load(sys.stdin)
    name = payload.get("tool_name")
    inp = payload.get("tool_input") or {}
    target = inp.get("path") or inp.get("file_path")
    if not target:
        return
    t = norm(target, payload.get("cwd"))
    if os.path.dirname(t) != WS:
        return  # not a workspace-root child -> allow
    base = os.path.basename(t)
    if base in ALLOWED_TOP:
        return
    print(json.dumps({
        "action": "block",
        "message": (
            f"Workspace hygiene: '{base}' cannot be written at the workspace root. "
            f"Scratch/temp -> {WS}/tmp/<task>/ ; durable work -> {WS}/projects/<repo>/. "
            "Retry with the file inside one of those directories."
        ),
    }))

if __name__ == "__main__":
    main()
