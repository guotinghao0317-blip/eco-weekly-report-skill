# 飞书 CLI：组员首次准备

以 [larksuite/cli 官方仓库](https://github.com/larksuite/cli)和本机 `lark-cli --help` 为准；CLI 会更新，执行前不要凭记忆猜参数。以下命令不含任何组织凭据。

## 安装

先安装 Node.js（含 npm/npx）及 Python 3。官方推荐：

```sh
npx @larksuite/cli@latest install
lark-cli --version
lark-cli doctor --offline
```

AI 工具若支持加载飞书 CLI 官方技能，可再安装与 CLI 配套的技能：

```sh
npx skills add larksuite/cli -g -y
```

本仓库的周报技能与飞书 CLI 官方技能分工不同：前者描述周报业务流程，后者提供随 CLI 更新的命令用法。

## 配置、登录与诊断

```sh
lark-cli config init
lark-cli auth login
lark-cli auth status
lark-cli doctor
lark-cli whoami
```

首次配置由引导完成；若本机已有其他应用配置，应核对当前 profile 和应用，不直接覆盖。组员分别以自己的飞书身份登录。建议使用组织认可的应用配置，由管理员按需开通 API 权限；应用密钥不得提交 GitHub，也不要贴进聊天或日志。

`auth login` 不带参数会请求广泛权限。实际周报推荐先根据本期读取群消息、下载附件、读取/更新文档的操作申请**所需权限**，从 CLI 的 `--help`、内嵌指南和错误返回确认精确 scope；例如先核对：

```sh
lark-cli auth check --scope 'im:message:readonly'
lark-cli auth check --scope 'im:chat:read'
```

飞书 CLI 当前群历史消息指南明确列出这两个读取权限。文档读写、附件下载和发消息涉及的其他 scope，以当时 CLI 的错误信息及 `auth scopes` 核对后再申请；不在示例中一口气申请全部领域。群历史消息还受应用权限、用户授权和群成员可见性影响。权限设置页面显示“已开通”也不能代替 `auth check` 与真实读取验证。

登录 URL 或二维码由 CLI 当次生成，请在有效期内完成授权。切勿把 URL 中的设备码或 access token 放入仓库。涉及审批的权限按组织流程办理，不尝试绕过。

## 常用只读检查

```sh
lark-cli im +chat-search --help
lark-cli im +chat-messages-list --help
lark-cli im +messages-search --help
lark-cli wiki +node-get --help
lark-cli docs +fetch --help
```

例如，下列只读命令使用本地配置里的链接与群 ID；尖括号内容由使用者自己的环境提供：

```sh
lark-cli wiki +node-get --as user --node-token '<SOP_URL>'
lark-cli docs +fetch --as user --doc '<FULL_REPORT_URL>' --scope outline --doc-format markdown
lark-cli im +chat-messages-list --as user --chat-id '<CHAT_ID>' --start '<ISO_START>' --end '<ISO_END>'
```

执行读取前确认 `--as user` / `--as bot`：用户身份读取自己的可见资源，机器人身份只能读取应用可见资源。文档写入先用 `docs +fetch --scope outline` 定位，再用 `docs +update --dry-run` 预览，写后回读核对。群消息发送用 `im +messages-send --dry-run` 预览，并遵守技能规定的**逐条展示正文、逐条确认**。

运行时优先读取与当前 CLI 版本一致的内嵌指南：

```sh
lark-cli skills read lark-shared
lark-cli skills read lark-im
lark-cli skills read lark-doc
lark-cli skills read lark-wiki
```

如果命令报缺权限，记录缺少的 scope、对应操作和使用的身份，补授权后重试一次。若仍失败，检查应用权限、文档共享和群成员身份；不要反复向群发相同问题。
