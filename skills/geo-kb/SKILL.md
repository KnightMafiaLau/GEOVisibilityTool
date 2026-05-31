---
name: geo-kb
description: GEOVisibilityTool 本地知识库管理。把每次 probe→analyze→report 运行的产物自动 ingest 到 ~/.geo-kb/kb.sqlite,累积形成"跨 brand、跨 vertical、跨时间"的可查询知识库。**stdlib only(sqlite3)。所有数据全在本地,从不上传**。geo-harness 在每次跑完后自动调用;也可手动 query 历史数据。
triggers:
  - 查 KB
  - 查我跑过的 GEO 历史
  - 这个 LLM 在历史上引谁最多
  - 这个垂类的 visibility 基准
  - geo-kb
  - 历史 GEO 数据
metadata:
  author: KnightMafiaLau
  source: geo-harness v0.1
user-invocable: true
disable-model-invocation: false
---

# geo-kb — 本地 GEO 知识库

## 什么时候用

- **每次 harness 跑完自动 ingest**(geo-harness Phase 6 已自动调用)
- 用户想**手动查 KB**:
  - 跨 brand 看某 LLM × intent 偏好哪些 channel
  - 某品牌历史 visibility 趋势
  - 某 LLM 的 recipe 健康度有没有下降
  - 某垂类的 visibility 基准对比
  - 导出某次完整 run 的视图

## 数据存储位置

```
~/.geo-kb/
└── kb.sqlite        # 唯一文件,SQLite 3 schema
                     # 3 表:runs / citations / recipe_health
```

**全在本地,从不上传任何东西**。备份就是 cp 这个文件。

## 你（Claude）要做的事

### 1. 拿用户问题 → 选 subcommand

| 用户问 | 用 |
|---|---|
| "把这次测试导入 KB" / "ingest" | `kb.py ingest <test-dir> --vertical <V>` |
| "KB 总览" / "我跑了多少" | `kb.py stats` |
| "Qwen 在了解原理类引谁最多" | `kb.py query channels --llm Qwen --intent 了解原理 [--vertical V]` |
| "拓竹的历史 visibility" | `kb.py query trend --brand <slug>` |
| "DeepSeek 的 recipe 健康度趋势" | `kb.py query recipe-health --llm DeepSeek` |
| "3D 打印垂类的 visibility 基准" | `kb.py query benchmark --vertical "3D 打印"` |
| "导出这次 run 看" | `kb.py export <run-id>` |

### 2. 路径约定

- `kb.py` 在 repo 的 `scripts/kb.py`(用户 clone 后路径可能各异)
- 用户可能在 GEOVisibilityTool 根目录运行 → `python3 scripts/kb.py ...`
- 也可能装 alias / 加 PATH → `kb.py ...` 直接调
- **第一次用 KB 之前调用 `kb.py init`**(创建 ~/.geo-kb/ + schema)

### 3. ingest 自动化(geo-harness 内部)

geo-harness Phase 6 完成后,**自动调用**:

```bash
python3 <repo-path>/scripts/kb.py ingest <test-dir> --vertical <从 plan.yaml 或用户输入推断>
```

如果用户没指定 vertical,**问一次**("这个品牌属于什么垂类?如 3D 打印 / SaaS / 机器人 等"),用于后续跨 brand 查询。

### 4. KB 查询结果如何反哺其他 skill

(v1 是手动 query;v2 可考虑让 sub-skill 自动读 KB)

- **geo-queries** 生成 query 前可查:`kb.py query channels --vertical <V>` 看该垂类历史强信号,调整生成倾向
- **geo-channels** 出投放建议前可查:`kb.py query benchmark --vertical <V>` 看 cross-brand 平均水平,调整 ROI 定级口径
- **geo-analyze** 出分数后可加 cross-vertical benchmark 注脚:"本品牌 visibility 91.6,同垂类 3 个品牌平均 75.3"

### 5. 跑完后给用户

> KB 已更新:
> - run_id = <N>
> - 累积:<X> runs / <Y> brands / <Z> verticals / <W> citations
> - 这次新增:<n> citations / <m> recipe_health entries
>
> 想查:
> - `kb.py query channels --llm X --intent Y` — 跨 brand 找强信号
> - `kb.py query trend --brand <slug>` — 看自家历史趋势
> - `kb.py stats` — 总览

---

## 几个常见坑(别踩)

- **不要让 KB 路径硬编码到 ~/.geo-kb/** 之外的位置 — 用户备份 / 多机同步靠这个固定路径
- **不要把品牌名 / 竞品名 自动 redact**(那是 make-bundle 干的,for 公开分享;KB 是本地用,fidelity 优先)
- **不要在 sub-skill 里实现"读 KB"**(v1 KB 是 read-only by user;v2 再考虑接入)
- **不要 ingest 一个不完整的测试目录**(probe-plan.yaml 必须有,缺它就 sys.exit)

---

## 不做的事

- 不上传 KB 到任何远端
- 不在 ingest 时去敏(全 fidelity 本地存)
- 不替代 make-bundle.py(那是 for 公开 issue 分享的脱敏 bundle)
- 不在 Constitution 6 条边界内 — kb.py 是 scripts/ 下的 helper(~250 行,sqlite3 + stdlib),不属于 skill 内部 Python,不受 §6 的 150 行约束
