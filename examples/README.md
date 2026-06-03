# examples — 真实案例库

跑过的真实品牌测量案例,放这里方便:
1. 第一次用工具的人**看产物长什么样**,再决定要不要自己跑一遍
2. 对比不同行业 / 垂类 / 竞品格局下,GEO 测量能挖出什么
3. 给"GEO 到底测什么"这个问题一个可看可点的回答

## 案例列表

| 日期 | 品牌 | 垂类 | 测试 LLM | 总分 | 看点 |
|---|---|---|---|---|---|
| 2026-05-31 | [简知](./jianzhi-20260531/) | AI 学习 | DeepSeek + Qwen | 38.5 | 「收录但不提及」典型 + 紧急声誉风险挖掘 + 12 周渠道行动日历 |

## 想贡献你的案例?

**两条路径,挑舒服的**:

### A. 我懒,信息我填,你帮我打包

→ 开一个 [Case Study 提交 issue](https://github.com/KnightMafiaLau/GEOVisibilityTool/issues/new?template=case-study-submission.yml)
表格化的字段(品牌信息 / 测试设置 / 核心诊断 / 紧急风险...),拖两份 PDF 上去,填到底,提交。
我们看到 issue 会帮你转成 PR。

### B. 我自己来 PR

照 [`jianzhi-20260531/`](./jianzhi-20260531/) 的 7 节式结构写好 README,加上两份 PDF,开 PR。

**强制 7 节(顺序锁死)**:

| 序号 | 章节关键词(必带) |
|---|---|
| 一 | 案例品牌信息 |
| 二 | 测试设置 |
| 三 | 产物 |
| 四 | 关键发现 |
| 五 | 决策路径 |
| 六 | 复现这一份 |
| 七 | 看完这份案例你应该知道 |

CI 会自动 check(`.github/workflows/validate-case-studies.yml` 跑 `scripts/validate-case-study.py`)。缺章节、顺序错、不用中文序号 → PR 直接红。

**本地预检**(开 PR 前自己跑一遍):

```bash
python3 scripts/validate-case-study.py examples/<your-case-dir>
```

通过了再 PR 就不会被 CI 退。

### 提交前都要确认

- 案例**真实跑过**,数字/引用源/零命中场景来自实测,不是编造
- 品牌信息属实
- 公开发布**不会**对第三方造成不当影响(竞品评分基于公开 LLM 答案,但请负责任地展示)
- 已**去敏** probe 原始数据(`probe-results-*.yaml` 可能含第三方网页内容片段)
