# Wamess SideStore Source

自动跟踪 VeneraX、Venera Next、PiliPlus、EhPanda 的最新正式 GitHub Release。
IPA 直接链接到上游附件，不上传或修改安装包。

## 使用

1. 将这个目录的内容上传到公开 GitHub 仓库，默认分支使用 `main`。
2. 打开 Actions → Update SideStore source → Run workflow。
3. 在 SideStore 中添加以下地址，将 `OWNER` 和 `REPOSITORY` 替换为实际值：

   ```text
   https://raw.githubusercontent.com/OWNER/REPOSITORY/main/source.json
   ```

若推送失败，检查仓库 Actions 权限和 `main` 分支保护规则是否允许机器人直接提交。
这里尚未设置远程仓库，源地址需在上传后确定。

## 配置

- `source-config.json`：源名称和标识。标识发布后保持不变。
- `apps.json`：应用信息及 `assetRegex`。正则完整匹配文件名，并单独强制 `.ipa` 扩展名；JSON 中的反斜杠需写作 `\\`。
- `update.py`：读取 IPA 内真实 Bundle ID、版本、构建号、最低 iOS 版本；检查附件大小和上游提供的 SHA-256。
- `.github/workflows/update.yml`：每六小时更新一次，也可手动触发。

本地运行（Python 3.10 或以上，仅使用标准库）：

```sh
python3 update.py
```

可以通过 `GH_TOKEN` 环境变量提供 GitHub API token；公开仓库本地运行不强制提供。
仅收录最新正式版，不收录预发布版本，也不保留旧版安装记录。
零个或多个 IPA 匹配、下载失败、IPA 损坏或 Bundle ID 重复会终止更新并保留原有源文件。

GitHub 定时任务可能延迟；公开仓库连续 60 天没有活动时可能自动停用，需要在 Actions 中重新启用。
此源更新应用目录，手机端仍需由 SideStore 检查并安装更新。
