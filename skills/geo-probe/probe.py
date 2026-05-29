"""geo-probe helpers — 机械活只在这。

Stdlib only. 判断和编排归 SKILL.md。

Commands:
  wait                          随机等 20-60 秒（防风控）
  init <path>                   创建输出 YAML 文件头
  append <path>                 把一条 result block 原子追加到文件（block 从 stdin 读）
  extract-citations             从 stdin 抽 URL，输出去重的域名 YAML 列表
"""
import argparse
import random
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

URL_RE = re.compile(r"https?://[^\s<>\"\)\]]+")


def cmd_wait(args):
    seconds = random.uniform(args.min, args.max)
    print(f"[wait] sleeping {seconds:.1f}s before next query...", file=sys.stderr)
    time.sleep(seconds)
    print(f"{seconds:.1f}")


def cmd_init(args):
    path = Path(args.path)
    if path.exists() and not args.overwrite:
        sys.exit(f"[init] {path} exists; use --overwrite")
    path.write_text(
        f"brand: {args.brand}\n"
        f"target_llm: {args.llm}\n"
        f"probed_at: {args.probed_at}\n"
        f"probed_by: {args.probed_by}\n"
        f"queries_total: {args.total}\n"
        f"\nresults:\n",
        encoding="utf-8",
    )
    print(f"[init] created {path}", file=sys.stderr)


def cmd_append(args):
    path = Path(args.path)
    if not path.exists():
        sys.exit(f"[append] {path} doesn't exist; run `init` first")
    block = sys.stdin.read().rstrip()
    if not block.startswith("- "):
        sys.exit("[append] block must start with '- ' (YAML list item)")
    existing = path.read_text(encoding="utf-8").rstrip()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(existing + "\n" + block + "\n", encoding="utf-8")
    tmp.replace(path)
    print(f"[append] appended to {path}", file=sys.stderr)


def cmd_extract_citations(args):
    text = sys.stdin.read()
    seen = set()
    for url in URL_RE.findall(text):
        url = url.rstrip(".,;:!?)\"'")
        domain = urlparse(url).netloc.lower()
        if domain:
            seen.add(domain)
    if not seen:
        print("citations: []")
        return
    print("citations:")
    for domain in sorted(seen):
        print(f"  - {domain}")


def main():
    p = argparse.ArgumentParser(description="geo-probe helpers")
    sub = p.add_subparsers(dest="cmd", required=True)

    pw = sub.add_parser("wait")
    pw.add_argument("--min", type=float, default=20.0)
    pw.add_argument("--max", type=float, default=60.0)
    pw.set_defaults(func=cmd_wait)

    pi = sub.add_parser("init")
    pi.add_argument("path")
    pi.add_argument("--brand", required=True)
    pi.add_argument("--llm", required=True)
    pi.add_argument("--total", type=int, required=True)
    pi.add_argument("--probed-at", required=True)
    pi.add_argument("--probed-by", required=True)
    pi.add_argument("--overwrite", action="store_true")
    pi.set_defaults(func=cmd_init)

    pa = sub.add_parser("append")
    pa.add_argument("path")
    pa.set_defaults(func=cmd_append)

    pe = sub.add_parser("extract-citations")
    pe.set_defaults(func=cmd_extract_citations)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
