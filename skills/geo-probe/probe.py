"""geo-probe helpers — 机械活只在这。Stdlib only. 判断归 SKILL.md.

Commands: wait | init | append | extract-citations | log | verify-log
"""
import argparse, json, random, re, sys, time
from pathlib import Path
from urllib.parse import urlparse

URL_RE = re.compile(r"https?://[^\s<>\"\)\]]+")

# 每 LLM 每 query citations 最低应有条数(低 = recipe 没跑或 panel 没开)。0 = 不报警
EXPECTED_MIN_CITATIONS = {
    "Qwen": 5, "qwen": 5, "千问": 5, "DeepSeek": 3, "deepseek": 3,
    "Kimi": 2, "kimi": 2, "豆包": 0, "Doubao": 0, "doubao": 0,
}


def cmd_wait(args):
    s = random.uniform(args.min, args.max)
    print(f"[wait] sleeping {s:.1f}s before next query...", file=sys.stderr)
    time.sleep(s)
    print(f"{s:.1f}")


def cmd_init(args):
    path = Path(args.path)
    if path.exists() and not args.overwrite:
        sys.exit(f"[init] {path} exists; use --overwrite")
    head = (f"brand: {args.brand}\ntarget_llm: {args.llm}\n"
            f"probed_at: {args.probed_at}\nprobed_by: {args.probed_by}\n"
            f"queries_total: {args.total}\n\nresults:\n")
    path.write_text(head, encoding="utf-8")
    print(f"[init] created {path}", file=sys.stderr)


def cmd_append(args):
    path = Path(args.path)
    if not path.exists():
        sys.exit(f"[append] {path} doesn't exist; run `init` first")
    block = sys.stdin.read().rstrip()
    if not block.startswith("- "):
        sys.exit("[append] block must start with '- ' (YAML list item)")
    if args.citations_from:  # 从文件注入 citations(URL 不进 chat,防 sanitizer)
        urls, seen = [], set()
        for f in args.citations_from:
            for u in URL_RE.findall(Path(f).read_text(encoding="utf-8")):
                u = u.rstrip(".,;:!?)\"'")
                if u and u not in seen:
                    seen.add(u); urls.append(u)
        cite = "  citations:\n" + "\n".join(f"    - {u}" for u in urls) if urls else "  citations: []"
        if "  citations: !INJECT!" in block:
            block = block.replace("  citations: !INJECT!", cite)
        elif "\n  notes:" in block:
            block = block.replace("\n  notes:", "\n" + cite + "\n  notes:", 1)
        else:
            block = block.rstrip() + "\n" + cite
        print(f"[append] injected {len(urls)} URLs from {len(args.citations_from)} file(s)", file=sys.stderr)
    existing = path.read_text(encoding="utf-8").rstrip()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(existing + "\n" + block + "\n", encoding="utf-8")
    tmp.replace(path)
    print(f"[append] appended to {path}", file=sys.stderr)


def cmd_extract_citations(args):  # 输出 URL 列表;不去重(同 URL 多次=信号)
    urls = [u for u in (x.rstrip(".,;:!?)\"'") for x in URL_RE.findall(sys.stdin.read())) if u]
    if not urls:
        print("citations: []"); return
    print("citations:")
    for u in urls: print(f"  - {u}")


def cmd_log(args):
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
             "qid": args.qid, "intent": args.intent, "llm": args.llm,
             "recipe": args.recipe, "panel_opened": args.panel_opened,
             "urls_found": args.urls_found, "domains_unique": args.domains_unique}
    if args.note:
        entry["note"] = args.note
    with open(args.path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[log] {entry['qid']} {entry['llm']} urls={entry['urls_found']} domains={entry['domains_unique']}", file=sys.stderr)


def cmd_verify_log(args):
    path = Path(args.path)
    if not path.exists():
        sys.exit(f"[verify-log] no log at {path}")
    entries = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not entries:
        sys.exit(f"[verify-log] empty log at {path}")
    by_llm = {}
    for e in entries:
        by_llm.setdefault(e["llm"], []).append(e)
    print(f"[verify-log] {path.name} — {len(entries)} entries / {len(by_llm)} LLM(s)")
    any_bad = False
    for llm, es in by_llm.items():
        mn = EXPECTED_MIN_CITATIONS.get(llm, 1)
        ds = sorted(e["domains_unique"] for e in es)
        op = sum(1 for e in es if e["panel_opened"])
        bad = [e for e in es if e["domains_unique"] < mn]
        print(f"\n  {llm} ({len(es)}q, expected_min={mn}): panel_opened={op}/{len(es)}, "
              f"domains min={ds[0]} median={ds[len(ds)//2]} max={ds[-1]}")
        if bad:
            any_bad = True
            print(f"    ⚠ ANOMALIES ({len(bad)}):")
            for a in bad:
                print(f"      [{a['qid']}] {a['intent']}: {a['domains_unique']} domains, panel_opened={a['panel_opened']}")
        else:
            print(f"    ✓ no anomalies")
    sys.exit(2 if any_bad else 0)


def _bool(s): return s.lower() in ("true", "1", "yes")


def main():
    p = argparse.ArgumentParser(description="geo-probe helpers")
    sub = p.add_subparsers(dest="cmd", required=True)

    pw = sub.add_parser("wait"); pw.add_argument("--min", type=float, default=20.0)
    pw.add_argument("--max", type=float, default=60.0); pw.set_defaults(func=cmd_wait)

    pi = sub.add_parser("init"); pi.add_argument("path")
    for n in ("brand", "llm", "probed-at", "probed-by"): pi.add_argument(f"--{n}", required=True)
    pi.add_argument("--total", type=int, required=True)
    pi.add_argument("--overwrite", action="store_true"); pi.set_defaults(func=cmd_init)

    pa = sub.add_parser("append"); pa.add_argument("path")
    pa.add_argument("--citations-from", action="append", default=[],
                    help="读文件抽 URL 注入到 block 的 citations 字段(防 chat sanitizer);可多次")
    pa.set_defaults(func=cmd_append)
    pe = sub.add_parser("extract-citations"); pe.set_defaults(func=cmd_extract_citations)

    pl = sub.add_parser("log"); pl.add_argument("path")
    for n in ("qid", "intent", "llm", "recipe"): pl.add_argument(f"--{n}", required=True)
    pl.add_argument("--panel-opened", type=_bool, required=True)
    pl.add_argument("--urls-found", type=int, required=True)
    pl.add_argument("--domains-unique", type=int, required=True)
    pl.add_argument("--note", default=None); pl.set_defaults(func=cmd_log)

    pv = sub.add_parser("verify-log"); pv.add_argument("path"); pv.set_defaults(func=cmd_verify_log)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
