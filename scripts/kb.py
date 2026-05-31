#!/usr/bin/env python3
"""kb.py — GEOVisibilityTool 本地知识库管理

把每次 probe→analyze→report→channels 运行的产物 ingest 到 ~/.geo-kb/kb.sqlite,
累积形成"跨 brand、跨 vertical、跨时间"的可查询知识库。

Stdlib only (sqlite3 + json + re + pathlib)。所有数据**全在本地**,不上传。

Commands:
  init                                     初始化 ~/.geo-kb/ + 创建 schema
  ingest <test-dir> [--vertical <v>]       把测试目录的产物导入 KB
  stats                                    总览(总 runs / brands / citations 等)
  query channels --llm <X> --intent <Y>    跨 brand 查某 LLM × intent 的 top channel
  query trend --brand <slug>               某品牌历史 visibility 趋势
  query recipe-health --llm <X>            某 LLM 的 recipe 健康度趋势
  query benchmark --vertical <V>           某垂类的 cross-brand visibility 基准
  export <run-id> [--format json|md]       导出某次 run 的完整 KB 视图
"""
import argparse, json, re, sqlite3, sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

KB_DIR = Path.home() / ".geo-kb"
DB_PATH = KB_DIR / "kb.sqlite"
URL_RE = re.compile(r"https?://[^\s<>\"\)\]]+")

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,
    brand_slug TEXT NOT NULL,
    vertical TEXT,
    test_dir TEXT NOT NULL,
    run_date TEXT NOT NULL,
    llms_completed TEXT,
    total_queries INTEGER,
    visibility_score REAL,
    ingested_at TEXT NOT NULL,
    UNIQUE(brand_slug, run_date, test_dir)
);
CREATE TABLE IF NOT EXISTS citations (
    citation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER REFERENCES runs(run_id) ON DELETE CASCADE,
    qid TEXT NOT NULL,
    intent TEXT NOT NULL,
    llm TEXT NOT NULL,
    domain TEXT NOT NULL,
    url TEXT,
    is_brand_owned INTEGER DEFAULT 0,
    is_competitor_owned INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS recipe_health (
    health_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER REFERENCES runs(run_id) ON DELETE CASCADE,
    qid TEXT NOT NULL,
    intent TEXT NOT NULL,
    llm TEXT NOT NULL,
    panel_opened INTEGER,
    urls_found INTEGER,
    domains_unique INTEGER,
    is_anomaly INTEGER
);
CREATE INDEX IF NOT EXISTS idx_cit_llm_intent ON citations(llm, intent);
CREATE INDEX IF NOT EXISTS idx_cit_domain ON citations(domain);
CREATE INDEX IF NOT EXISTS idx_runs_brand ON runs(brand_slug);
CREATE INDEX IF NOT EXISTS idx_runs_vertical ON runs(vertical);
CREATE INDEX IF NOT EXISTS idx_health_llm ON recipe_health(llm);
"""

EXPECTED_MIN = {"Qwen": 5, "qwen": 5, "千问": 5, "DeepSeek": 3, "deepseek": 3,
                "Kimi": 2, "kimi": 2, "豆包": 0, "Doubao": 0, "doubao": 0}


def db_connect():
    KB_DIR.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(SCHEMA)
    return con


def cmd_init(args):
    con = db_connect()
    con.close()
    print(f"[init] KB 已初始化: {DB_PATH}", file=sys.stderr)


def cmd_ingest(args):
    d = Path(args.test_dir).resolve()
    if not d.is_dir(): sys.exit(f"[ingest] {d} 不是目录")
    con = db_connect()
    cur = con.cursor()

    # 解析 probe-plan
    plan = (d / "probe-plan.yaml")
    if not plan.exists(): sys.exit(f"[ingest] 缺 probe-plan.yaml")
    pt = plan.read_text(encoding="utf-8")
    brand = re.search(r"^brand:\s*(.+)$", pt, re.MULTILINE).group(1).strip()
    brand_slug = re.sub(r"[^a-zA-Z0-9-]+", "-", brand.lower()).strip("-") or "unnamed"
    llms_completed = re.findall(r"llm:\s*(\S+)", pt)
    run_date = re.search(r"created_at:\s*(\S+)", pt).group(1)[:10] if re.search(r"created_at:", pt) else datetime.now().strftime("%Y-%m-%d")

    # 提取品牌 + 竞品英文别名(用于 redact 域名分类)
    competitor_names = set()
    for results_yaml in d.glob("probe-results-*.yaml"):
        text = results_yaml.read_text(encoding="utf-8")
        competitor_names.update(m.group(1).strip() for m in re.finditer(r"      - name:\s*(.+)", text))
    brand_aliases = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", brand)}
    competitor_aliases = set()
    for name in competitor_names:
        for word in re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", name):
            competitor_aliases.add(word.lower())

    # 读 analysis 抓 visibility
    visibility = None
    for amd in d.glob("analysis-*.md"):
        m = re.search(r"Visibility Score:[*\s]*([\d.]+)", amd.read_text(encoding="utf-8"))
        if m: visibility = float(m.group(1)); break

    # 写 runs
    cur.execute("""INSERT OR IGNORE INTO runs (brand, brand_slug, vertical, test_dir, run_date,
                   llms_completed, total_queries, visibility_score, ingested_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (brand, brand_slug, args.vertical, str(d), run_date,
                 json.dumps(llms_completed), 0, visibility, datetime.now().isoformat()))
    cur.execute("SELECT run_id FROM runs WHERE brand_slug=? AND run_date=? AND test_dir=?", (brand_slug, run_date, str(d)))
    run_id = cur.fetchone()[0]
    cur.execute("DELETE FROM citations WHERE run_id=?", (run_id,))
    cur.execute("DELETE FROM recipe_health WHERE run_id=?", (run_id,))

    # 写 citations(从 probe-results)
    total_q = 0
    for results_yaml in d.glob("probe-results-*.yaml"):
        content = results_yaml.read_text(encoding="utf-8")
        llm_m = re.search(r"target_llm:\s*(\S+)", content)
        if not llm_m: continue
        llm = llm_m.group(1)
        blocks = re.split(r"(?=- query_id:)", content)[1:]
        total_q += len(blocks)
        for b in blocks:
            qid = re.search(r"query_id:\s*(\w+)", b).group(1)
            intent = re.search(r"intent:\s*(\S+)", b).group(1)
            cm = re.search(r"citations:\s*\n((?:    - .+\n?)+)", b)
            if not cm: continue
            for url in re.findall(r"    - (\S+)", cm.group(1)):
                if not url.startswith("http"): url_full = None; domain = url.lower()
                else: url_full = url.rstrip(".,;:!?)\"'"); domain = urlparse(url_full).netloc.lower()
                if not domain: continue
                is_brand = int(any(a in domain for a in brand_aliases))
                is_comp = int(any(a in domain for a in competitor_aliases)) if not is_brand else 0
                cur.execute("""INSERT INTO citations (run_id, qid, intent, llm, domain, url, is_brand_owned, is_competitor_owned)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (run_id, qid, intent, llm, domain, url_full, is_brand, is_comp))

    # 写 recipe_health(从 probe-log)
    for log in d.glob("probe-log-*.jsonl"):
        for line in log.read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            e = json.loads(line)
            mn = EXPECTED_MIN.get(e["llm"], 1)
            cur.execute("""INSERT INTO recipe_health (run_id, qid, intent, llm, panel_opened, urls_found, domains_unique, is_anomaly)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (run_id, e["qid"], e["intent"], e["llm"], int(e["panel_opened"]), e["urls_found"], e["domains_unique"], int(e["domains_unique"] < mn)))

    cur.execute("UPDATE runs SET total_queries=? WHERE run_id=?", (total_q, run_id))
    con.commit()
    cit_n = con.execute("SELECT COUNT(*) FROM citations WHERE run_id=?", (run_id,)).fetchone()[0]
    health_n = con.execute("SELECT COUNT(*) FROM recipe_health WHERE run_id=?", (run_id,)).fetchone()[0]
    con.close()
    print(f"[ingest] run_id={run_id} brand='{brand}' vertical={args.vertical}", file=sys.stderr)
    print(f"[ingest] 写入 {cit_n} citations / {health_n} recipe_health 条目", file=sys.stderr)


def cmd_stats(args):
    con = db_connect()
    runs = con.execute("SELECT COUNT(*), COUNT(DISTINCT brand_slug), COUNT(DISTINCT vertical) FROM runs").fetchone()
    cit = con.execute("SELECT COUNT(*), COUNT(DISTINCT domain) FROM citations").fetchone()
    health = con.execute("SELECT COUNT(*), SUM(is_anomaly) FROM recipe_health").fetchone()
    llms = con.execute("SELECT llm, COUNT(*) FROM citations GROUP BY llm ORDER BY 2 DESC").fetchall()
    print(f"runs: {runs[0]} ({runs[1]} brands, {runs[2]} verticals)")
    print(f"citations: {cit[0]} ({cit[1]} unique domains)")
    print(f"recipe health: {health[0]} entries, {health[1]} anomalies")
    print(f"per-LLM citations: " + ", ".join(f"{l}={n}" for l, n in llms))
    con.close()


def cmd_query(args):
    con = db_connect()
    if args.subq == "channels":
        # 跨 brand: 某 LLM × intent 的 top channel(排除 brand/competitor 官网)
        sql = """SELECT c.domain, COUNT(*) as cnt, COUNT(DISTINCT r.brand_slug) as brands
                 FROM citations c JOIN runs r ON c.run_id=r.run_id
                 WHERE c.llm=? AND c.intent=? AND c.is_brand_owned=0 AND c.is_competitor_owned=0"""
        params = [args.llm, args.intent]
        if args.vertical: sql += " AND r.vertical=?"; params.append(args.vertical)
        sql += " GROUP BY c.domain ORDER BY cnt DESC LIMIT 15"
        rows = con.execute(sql, params).fetchall()
        print(f"top channels for LLM={args.llm} intent={args.intent}" + (f" vertical={args.vertical}" if args.vertical else " (all verticals)"))
        for d, n, b in rows: print(f"  {n:4d}  {d:<40} ({b} brands)")
    elif args.subq == "trend":
        rows = con.execute("SELECT run_date, visibility_score FROM runs WHERE brand_slug=? ORDER BY run_date", (args.brand,)).fetchall()
        print(f"visibility trend for brand_slug={args.brand}")
        for d, v in rows: print(f"  {d}  {v if v else '(no visibility data)'}")
    elif args.subq == "recipe-health":
        rows = con.execute("""SELECT date(r.ingested_at) as d,
                              ROUND(AVG(h.panel_opened),2) as opened,
                              ROUND(AVG(h.domains_unique),1) as avg_dom,
                              SUM(h.is_anomaly) as anom_n,
                              COUNT(*) as n
                              FROM recipe_health h JOIN runs r ON h.run_id=r.run_id
                              WHERE h.llm=? GROUP BY d ORDER BY d""", (args.llm,)).fetchall()
        print(f"recipe health trend for LLM={args.llm}")
        print(f"{'date':<12} {'panel_opened':<14} {'avg_domains':<12} {'anomalies':<10} {'queries':<8}")
        for d, op, ad, an, n in rows: print(f"{d:<12} {op:<14} {ad:<12} {an:<10} {n:<8}")
    elif args.subq == "benchmark":
        rows = con.execute("""SELECT brand, visibility_score, run_date FROM runs
                              WHERE vertical=? AND visibility_score IS NOT NULL ORDER BY visibility_score DESC""", (args.vertical,)).fetchall()
        if not rows: print(f"no benchmark data for vertical={args.vertical}"); return
        avg = sum(r[1] for r in rows) / len(rows)
        print(f"vertical={args.vertical}: {len(rows)} brands, avg visibility={avg:.1f}")
        for b, v, d in rows: print(f"  {v:5.1f}  {b}  ({d})")
    con.close()


def cmd_export(args):
    con = db_connect()
    run = con.execute("SELECT * FROM runs WHERE run_id=?", (args.run_id,)).fetchone()
    if not run: sys.exit(f"[export] no run with id={args.run_id}")
    print(f"# Run #{args.run_id}\nbrand: {run[1]}\nvertical: {run[3]}\ndate: {run[5]}\nvisibility: {run[8]}")
    print(f"\n## Citations\n")
    for r in con.execute("SELECT llm, intent, domain, COUNT(*) FROM citations WHERE run_id=? GROUP BY llm, intent, domain ORDER BY 4 DESC LIMIT 30", (args.run_id,)).fetchall():
        print(f"  {r[0]:<10} {r[1]:<10} {r[2]:<40} x{r[3]}")
    con.close()


def main():
    p = argparse.ArgumentParser(description="GEOVisibilityTool 本地 KB")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(func=cmd_init)
    pi = sub.add_parser("ingest"); pi.add_argument("test_dir"); pi.add_argument("--vertical", default=None); pi.set_defaults(func=cmd_ingest)
    sub.add_parser("stats").set_defaults(func=cmd_stats)
    pq = sub.add_parser("query"); pq.add_argument("subq", choices=["channels", "trend", "recipe-health", "benchmark"])
    pq.add_argument("--llm"); pq.add_argument("--intent"); pq.add_argument("--brand"); pq.add_argument("--vertical")
    pq.set_defaults(func=cmd_query)
    pe = sub.add_parser("export"); pe.add_argument("run_id", type=int); pe.add_argument("--format", default="md", choices=["md", "json"])
    pe.set_defaults(func=cmd_export)
    a = p.parse_args(); a.func(a)


if __name__ == "__main__":
    main()
