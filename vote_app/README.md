# 小礼品设计投票 · 一键部署到云端（免费）

把投票程序部署到 **Render**（免费、自带公网 https 地址、支持一键部署），各地同事/客户用手机点开就能投，结果自动实时汇总。

## 程序包含的页面
- 投票页 `/`：13 个礼品卡片（带商品图），每人勾选 1–4 种，填名字提交
- 结果页 `/results`：实时条形图、参与人数、最近投票，每 5 秒自动刷新
- 导出 `/api/export`：一键下载 CSV 结果（Excel 可直接打开）
- 防重复：同一名字不能重复投；超出 4 项自动拦截
- 数据库：本地用 SQLite，部署到 Render 后自动改用免费 Postgres（数据不丢）

## 部署步骤（约 5 分钟，全程免费）

### 第 1 步：把本文件夹上传到 GitHub
1. 打开 https://github.com ，注册/登录，点 **New repository**（仓库名随意，如 `gift-vote`，选 **Public**）。
2. 把 `vote_app/` 整个文件夹的内容上传到这个仓库（直接把文件拖进网页，或本地 `git push`）。

### 第 2 步：一键部署
点击下面的按钮（或手动操作）：

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/YOLO-1995/gift-vote)

> 把上面链接里的 `你的用户名/gift-vote` 换成你第 1 步创建的仓库地址。

手动也行：登录 https://render.com → **New** → **Blueprint** → 连接你的 GitHub 仓库 → 选 `render.yaml` → **Apply**。

### 第 3 步：拿到公网地址
部署完成后（约 1–2 分钟），Render 会给你一个类似 `https://gift-vote.onrender.com` 的地址。
把它发给各地同事/客户即可投票。结果页在 `https://gift-vote.onrender.com/results`。

## 本地运行 / 测试
```bash
pip install -r requirements.txt        # 仅云端需要 psycopg2；本地不装也能跑
python vote_app.py
# 浏览器打开 http://localhost:8765
```

## 注意事项
- **免费套餐限制**：服务 15 分钟无人访问会“休眠”，下次有人打开时约慢 2–3 秒自动唤醒；Postgres 数据库在投票活跃期间正常持久。
- **国内访问速度**：Render 节点在海外，国内打开可能偏慢。若投票人多/在意速度，可改为国内轻量云（腾讯云/阿里云，约 ¥30–60/月），把本文件夹 `python vote_app.py` 跑起来、开放 8765 端口即可，程序无需改代码。
- 数据都在数据库里，随时可在 `/results` 看汇总、在 `/api/export` 导出 CSV。
