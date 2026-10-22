# 生态业务数据周报 Skill

供组员在支持本地 Skill、文件和终端操作的 AI 工具中使用。它帮助完成每周四至次周三的生态数据分析，并更新完整版周报和组周报摘要。飞书群消息在发送前逐条征求使用者确认。

## 第一次使用

1. 按 [飞书 CLI 准备](references/feishu-cli.md)安装 `lark-cli`，以**自己的飞书账号**完成应用配置和授权。
2. 从本仓库下载技能文件夹并导入所用工具。WorkBuddy 可通过技能管理界面导入本地技能包；豆包工作可在“技能·连接器·伙伴”中导入本地技能文件。入口以当前客户端界面为准。详见 [工具适配](references/platforms.md)。
3. 确认工具允许读取本地文件、执行终端命令，并可访问飞书。安装 Python 3，在技能目录创建虚拟环境，再安装 `requirements.txt`。macOS/Linux：`python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt`；Windows PowerShell：`py -3 -m venv .venv; .venv\Scripts\python.exe -m pip install -r requirements.txt`。
4. 复制 `examples/workspace-config.example.json` 为工作目录中的 `workspace-config.json`，填入你有权访问的周度 SOP、生态数据群、完整版周报和组周报链接。真实链接、群 ID、令牌及数据只在自己的工作环境中使用，不放入本仓库。

## 每周调用

在工具中选择此技能，或说：

> 请用“生态业务数据周报”技能完成最近一期周报。统计周期按 SOP 的周四至周三，先检查群里已有回数；需要向群发消息时先给我看完整内容，等我逐条确认。完成后更新完整版和组周报，并回读核验。

若工具无法自动发现技能，可让它先读取本仓库的 `SKILL.md`，再执行上述请求。首次填好本地配置后，后续无需反复粘贴链接；每期仍需核对目标章节。

## 你会得到什么

- 两份飞书周报链接和本期关键结论。
- 本地 `weekly-input.json`、`metrics.json` 和七张规定图；组周报的两张摘要图按当期 SOP 制作。
- 数据来源、过滤条件、覆盖天数、未解决的口径差异和待业务方补充的指标。

如 BI 分区尚未到齐，可先交付已核实部分，并清楚列出缺口；不要把部分周报说成完整交付。重复运行时更新本期章节，不另建同名章节。

## 仓库内容

`SKILL.md` 是跨工具执行规则；`references/` 提供安装、口径和工具导入说明；`scripts/prepare_report.py` 负责确定性校验和制图；`examples/` 仅含虚构数据。仓库不包含公司周报原文、真实回数、截图、应用密钥或访问令牌。

## 验证

```sh
.venv/bin/python scripts/prepare_report.py examples/weekly-input.example.json --out-dir output
```

Windows 将 `.venv/bin/python` 换成 `.venv\Scripts\python.exe`。脚本应生成一份 `metrics.json` 和七张 PNG。该示例只用于检查技能包能否运行，不能用于飞书周报。
