#!/usr/bin/env python3
"""
validate-case-study.py — 校验 examples/<case>/README.md 的 7 节式结构

用法:
    python3 scripts/validate-case-study.py examples/jianzhi-20260531
    python3 scripts/validate-case-study.py examples/                # 校验全部子目录(跳过 examples/README.md)
    python3 scripts/validate-case-study.py --changed                # 校验 git diff vs origin/main 涉及的 examples/ 子目录(CI 用)

为什么要有这个:
    case study README 的结构是这个项目对外的"案例长这样"承诺。结构稳定,
    后续案例之间能横向对比;新贡献者也有现成模板。靠 review 维护这件事
    会逐渐松动,所以用 CI 卡死。

退出码:0=通过,1=有错。出错时把缺失的章节标题列出来,贡献者一眼能改。
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REQUIRED_SECTIONS = [
    "案例品牌信息",
    "测试设置",
    "产物",
    "关键发现",
    "决策路径",
    "复现",            # "复现这一份" / "复现方式" 都接受
    "看完",            # "看完这份案例你应该知道" 等
]

CN_NUMERALS = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]


def find_h2(text: str) -> list[str]:
    """Return list of all level-2 markdown headers (## ...) verbatim."""
    return re.findall(r"^##\s+(.+?)\s*$", text, flags=re.MULTILINE)


def check_readme(readme: Path) -> list[str]:
    """Return list of error messages; empty list = passing."""
    errors: list[str] = []
    if not readme.is_file():
        return [f"找不到 {readme}"]

    text = readme.read_text(encoding="utf-8")
    headers = find_h2(text)

    # 1. Required section keywords (order matters)
    found_indices: list[int] = []
    for keyword in REQUIRED_SECTIONS:
        matches = [i for i, h in enumerate(headers) if keyword in h]
        if not matches:
            errors.append(
                f"缺章节关键词:`## {keyword}`(实际章节:{headers or '一个都没有'})"
            )
            continue
        found_indices.append(matches[0])

    # 2. Order must match
    if not errors and found_indices != sorted(found_indices):
        errors.append(
            "章节顺序错了:期望 "
            + " → ".join(REQUIRED_SECTIONS)
            + f",实际 {headers}"
        )

    # 3. Numbering must be 一/二/三... 不能漏号
    seven_headers = [h for h in headers if any(h.startswith(n + "、") for n in CN_NUMERALS)]
    if len(seven_headers) < 7:
        errors.append(
            f"用中文序号(一、二、三...)的章节只有 {len(seven_headers)} 个,"
            f"应该 ≥7。命中:{seven_headers}"
        )

    return errors


def list_case_dirs(examples_root: Path) -> list[Path]:
    """All immediate subdirs of examples/ that contain a README.md."""
    out: list[Path] = []
    for child in sorted(examples_root.iterdir()):
        if child.is_dir() and (child / "README.md").is_file():
            out.append(child)
    return out


def changed_case_dirs(repo_root: Path, base: str = "origin/main") -> list[Path]:
    """Case dirs touched by current branch vs base. Used by CI."""
    try:
        diff = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except subprocess.CalledProcessError as e:
        print(f"[validate] git diff failed:{e.stderr}", file=sys.stderr)
        return []
    seen: set[Path] = set()
    for line in diff.splitlines():
        if not line.startswith("examples/"):
            continue
        parts = line.split("/")
        if len(parts) < 3:
            # examples/README.md — skip
            continue
        case = repo_root / "examples" / parts[1]
        if case.is_dir() and (case / "README.md").is_file():
            seen.add(case)
    return sorted(seen)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "target",
        nargs="?",
        help="examples/<case>/ 路径 或 examples/ 目录;省略时配合 --changed",
    )
    ap.add_argument(
        "--changed",
        action="store_true",
        help="只校验 git diff vs origin/main 涉及的 examples/ 子目录(CI 用)",
    )
    ap.add_argument(
        "--base",
        default="origin/main",
        help="--changed 的 diff 基准(默认 origin/main)",
    )
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parent.parent

    cases: list[Path]
    if args.changed:
        cases = changed_case_dirs(repo_root, args.base)
        if not cases:
            print("[validate] 本次 diff 不涉及 examples/<case>/,跳过")
            return 0
    elif args.target:
        target = Path(args.target).resolve()
        if (target / "README.md").is_file() and target.parent.name == "examples":
            cases = [target]
        elif target.name == "examples":
            cases = list_case_dirs(target)
        else:
            print(
                f"[validate] {target} 不是 examples/<case>/ 也不是 examples/",
                file=sys.stderr,
            )
            return 2
    else:
        ap.print_help()
        return 2

    fail = 0
    for case in cases:
        readme = case / "README.md"
        errs = check_readme(readme)
        rel = readme.relative_to(repo_root)
        if errs:
            fail += 1
            print(f"✗ {rel}")
            for e in errs:
                print(f"    - {e}")
        else:
            print(f"✓ {rel}")

    if fail:
        print(
            f"\n[validate] {fail} 个案例不合规。"
            f"\n参考 examples/jianzhi-20260531/README.md 的 7 节式结构:"
            f"\n  " + " → ".join(f"## {n}、{s}" for n, s in zip(CN_NUMERALS, [
                "案例品牌信息",
                "测试设置",
                "产物",
                "关键发现",
                "决策路径",
                "复现这一份",
                "看完这份案例你应该知道",
            ])),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
