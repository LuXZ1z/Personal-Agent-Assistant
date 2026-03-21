# 安全说明

## 本地机密勿入库

以下内容**仅应存在于本机**，且已在 `.gitignore` 中排除：

| 类型 | 路径示例 |
|------|----------|
| 系统 / LLM 配置 | `config/system.yaml` |
| 多机器人微信配置 | `config/bots.yaml` |
| 环境变量 | `.env`、`.env.test`、`.env.*`（保留 `*.example` 供模板） |
| 数据库与数据目录 | `*.db`、`data/`、`data.zip` 等 |
| 日志 | `logs/`、`*.log` |

公开仓库中**只应提交** `config/*_example.yaml` 与 `*.example` 模板。

## Git 历史中的泄露风险

若 `config/bots.yaml`、`config/system.yaml` 等**曾经被 `git commit` 过**，即使后来删除并加入 `.gitignore`，**旧提交里仍然含有这些内容**。

**请务必：**

1. **立即轮换**已暴露的密钥：LLM API Key、企业微信 `wechat_token` / `wechat_corp_secret`、EncodingAESKey 等。
2. 若仓库已公开推送，考虑使用 [git-filter-repo](https://github.com/newren/git-filter-repo) 或 BFG 从历史中剔除敏感文件，并 **force push**（需协调所有协作者）。

检查某文件是否曾进入历史：

```bash
git log --all --full-history -- config/bots.yaml
```

## 推送到 GitHub 前自检

```bash
git status
git diff --cached
# 确认未出现 .env、config/bots.yaml、config/system.yaml、data.zip 等
```
