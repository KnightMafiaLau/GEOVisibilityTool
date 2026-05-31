#!/usr/bin/env python3
"""make-bundle — 生成匿名化诊断数据包(贡献给 GEOVisibilityTool 社区)

读取测试目录里的 probe-log / probe-results / analysis,**去除所有品牌相关信息**,
只保留 recipe 健康度 + 引用模式结构,输出 JSON 包,用户手动附到 GitHub issue。

**这个脚本绝不自动上传任何东西**。你看到 JSON 内容,手动决定要不要分享。

Usage: python3 scripts/make-bundle.py <测试目录> [--vertical 行业类别]

Stdlib only. ~120 lines.
"""
import argparse, json, re, sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

URL_RE = re.compile(r"https?://[^\s<>\"\)\]]+")


def redact_brand(text, brand, competitors):
    """Replace brand name → BRAND_X, competitor names → COMP_1, COMP_2, ..."""
    if not text:
        return text
    result = text
    if brand:
        result = result.replace(brand, "BRAND_X")
    for i, comp in enumerate(competitors or []):
        if comp:
            result = result.replace(comp, f"COMP_{i+1}")
    return result


def main():
    p = argparse.ArgumentParser(description="make anonymized diagnostic bundle")
    p.add_argument("test_dir", help="测试目录路径")
    p.add_argument("--vertical", default=None, help="行业类别(可选,如'3D打印'/'机器人'/'SaaS')")
    p.add_argument("--out", default=None, help="输出文件路径(默认 bundle-<ts>.json)")
    args = p.parse_args()

    d = Path(args.test_dir)
    if not d.is_dir():
        sys.exit(f"[error] {d} 不是目录")

    bundle = {"version": "0.1.0", "vertical": args.vertical, "anonymized": True}

    # 1) 读 plan(只取 LLM 列表 + completed 状态)
    plan_path = d / "probe-plan.yaml"
    brand = None
    if plan_path.exists():
        plan_text = plan_path.read_text(encoding="utf-8")
        b = re.search(r"^brand:\s*(.+)$", plan_text, re.MULTILINE)
        brand = b.group(1).strip() if b else None
        bundle["llms_tested"] = re.findall(r"^\s*-\s*(\S+)$", re.search(r"planned_llms:\s*\n((?:\s*-\s*\S+\n?)+)", plan_text).group(1), re.MULTILINE) if re.search(r"planned_llms:", plan_text) else []
        bundle["llms_completed"] = re.findall(r"llm:\s*(\S+)", plan_text)

    # 2) 读 probe-log(per-LLM 健康度)
    bundle["per_llm_health"] = {}
    for log in d.glob("probe-log-*.jsonl"):
        entries = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
        if not entries: continue
        llm = entries[0]["llm"]
        urls = [e["urls_found"] for e in entries]
        cites = [e["domains_unique"] for e in entries]
        bundle["per_llm_health"][llm] = {
            "query_count": len(entries),
            "panel_opened_rate": sum(1 for e in entries if e["panel_opened"]) / len(entries),
            "urls_found":     {"min": min(urls),  "median": sorted(urls)[len(urls)//2],  "max": max(urls)},
            "domains_unique": {"min": min(cites), "median": sorted(cites)[len(cites)//2], "max": max(cites)},
            "anomaly_count":  sum(1 for e in entries if e["domains_unique"] < {"Qwen":5,"DeepSeek":3,"Kimi":2,"豆包":0}.get(llm, 1)),
        }

    # 3) 读 probe-results(引用域名 pattern,redact 品牌名/竞品官网,聚合 per-intent)
    # 先扫所有 probe-results 提取竞品英文别名(从 "中文 / English" 模式抽取)
    all_competitors_text = ""
    for results_yaml in d.glob("probe-results-*.yaml"):
        all_competitors_text += results_yaml.read_text(encoding="utf-8")
    competitor_names = list({m.group(1).strip() for m in re.finditer(r"      - name:\s*(.+)", all_competitors_text)})
    # 抽英文别名 — 取每个 name 的英文部分(全 ASCII alpha 段, 长度 ≥ 3)
    competitor_aliases = set()
    for name in competitor_names:
        for word in re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", name):
            competitor_aliases.add(word.lower())
    brand_aliases = set()
    if brand:
        for word in re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", brand):
            brand_aliases.add(word.lower())

    def redact_host(h):
        """竞品/品牌官网域名 → BRAND_OWNED / COMP_OWNED_N"""
        if not h: return None
        hl = h.lower()
        for ba in brand_aliases:
            if ba in hl: return "BRAND_OWNED_DOMAIN"
        for i, ca in enumerate(sorted(competitor_aliases)):
            if ca in hl: return f"COMPETITOR_OWNED_DOMAIN_{i+1}"
        return h

    intent_domains = {}
    for results_yaml in d.glob("probe-results-*.yaml"):
        content = results_yaml.read_text(encoding="utf-8")
        blocks = re.split(r"(?=- query_id:)", content)[1:]
        for b in blocks:
            intent_m = re.search(r"intent:\s*(\S+)", b)
            if not intent_m: continue
            intent = intent_m.group(1)
            intent_domains.setdefault(intent, Counter())
            for url in URL_RE.findall(b):
                host = urlparse(url.rstrip(".,;:!?)\"'")).netloc.lower()
                redacted = redact_host(host)
                if redacted:
                    intent_domains[intent][redacted] += 1

    bundle["per_intent_channel_pattern"] = {
        intent: {"top_10_domains": [{"domain": d, "count": c} for d, c in dom.most_common(10)],
                 "total_url_count": sum(dom.values())}
        for intent, dom in intent_domains.items()
    }

    # 4) 元数据(总览)
    bundle["summary"] = {
        "total_queries_probed": sum(h["query_count"] for h in bundle["per_llm_health"].values()),
        "total_url_observations": sum(p["total_url_count"] for p in bundle["per_intent_channel_pattern"].values()),
        "llms_with_anomalies": [l for l, h in bundle["per_llm_health"].items() if h["anomaly_count"] > 0],
    }

    # 5) 输出
    from datetime import datetime
    out_path = Path(args.out) if args.out else d / f"bundle-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    out_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[bundle] 写入 {out_path}", file=sys.stderr)
    print(f"[bundle] 总 query: {bundle['summary']['total_queries_probed']},总 URL 观测: {bundle['summary']['total_url_observations']}", file=sys.stderr)
    print(f"[bundle] **打开文件检查内容**,确认没有敏感信息后再分享到 GitHub issue。", file=sys.stderr)
    print(f"[bundle] 提交链接:https://github.com/KnightMafiaLau/GEOVisibilityTool/issues/new/choose", file=sys.stderr)


if __name__ == "__main__":
    main()
