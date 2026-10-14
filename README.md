# BiliNote · 抖音修复版

> 本仓库是 [BiliNote](https://github.com/JefferyHcool/BiliNote)（作者 JefferyHcool）的**二次开发版本**。
> 上游项目的版权、架构与绝大部分功能都属于原作者；本仓库只做了少量针对性修改。

<div align="center">

| | |
|---|---|
| **核心改动** | **修复了抖音（Douyin）视频无法下载的问题** |
| **部署形态** | **只提供 Web 端（Docker Compose），没有开发桌面端** |

</div>

---

## 先看这里：关于桌面端

**本仓库没有桌面端，只有 Web 端。**

上游 BiliNote 提供 Tauri + PyInstaller 打包的桌面客户端，**本仓库没有做这部分开发，也不提供桌面版安装包**。

原因（客观情况，不是能力判断）：

1. 我们这套改动**深度依赖 Docker 环境**（容器配置、镜像源、本地 whisper 模型、宿主机 Chrome 转发），改成桌面端等于全部推倒重配。
2. 上游的 src-tauri 代码里本身就标注了已知问题：

       PyInstaller sidecar 在含非 ASCII / 空格的路径下经常炸

3. 我们实测也确认过：PyInstaller 冻结后的进程启动 GUI 程序会「返回成功但窗口不出现」。

**所以本仓库的交付形态是**：用 docker compose 起服务，浏览器访问 http://localhost:3015

> 仓库里有一个 BiliNoteApp.exe 加 BiliNote.bat，那**只是一个启动器**（负责拉起 Docker 服务、拉起抓取浏览器、再打开浏览器），**不是 BiliNote 桌面客户端**。

---

## 相对上游的改动

### 1. 修复抖音视频无法下载（核心改动）

**问题现象**

用抖音链接生成笔记时直接失败：

    urllib.error.HTTPError: HTTP Error 403: Forbidden
    403 Blocked by ArgusSecurityPlugin Uifid Not Found

**原因分析（排查结论）**

抖音的 aweme/v1/web/aweme/detail/ 接口已经上线了 **secsdk 风控签名**：

- 请求必须带上 x-secsdk-web-signature 这一组签名参数（由页面里的 JS 运行时生成）
- 上游原先依赖的 **a_bogus 签名方案已经失效**，纯 HTTP 请求会被直接拦截
- 用**容器内的 Chromium** 去访问也会被识别、降级，拿不到真实的详情响应

**解决思路**

不再自己伪造签名，而是**让真实浏览器去请求，我们去读它的响应**：

1. 在本机（宿主机）启动一个**带远程调试端口的 Chrome**
2. 后端通过 **CDP（Chrome DevTools Protocol）** 连上去
3. 用这个真实浏览器打开抖音视频页，**拦截页面自己发出的 aweme/detail 响应**
4. 那份响应自带合法签名，直接拿来解析

**相关代码**

| 文件 | 作用 |
|---|---|
| backend/app/downloaders/douyin_browser.py | 新增：通过 CDP 抓取抖音详情（端口探测、CDP 连接、响应提取、失败重试） |
| backend/app/downloaders/douyin_downloader.py | 改造：默认走浏览器抓取；旧的纯 API 方案保留在 DOUYIN_LEGACY_API=1 后面 |

**使用要求（重要）**

抖音下载依赖宿主机上那个 Chrome，所以：

- 需要本机跑一个带调试端口的 Chrome（仓库提供了 start-douyin-chrome.bat 一键启动）
- 该 Chrome 没运行时，抖音下载会报 Connection refused
- .env 里的 DOUYIN_CDP_URL=http://host.docker.internal:9222 控制这个地址

### 2. 支持粘贴整段分享文本

抖音分享出来的内容通常长这样，直接粘贴会被拒：

    7.20 复制打开抖音，看看【xxx的作品】... https://v.douyin.com/xxxx/ 复制此链接...

现在前后端都会**自动从中提取第一个 URL**，粘贴即用。

### 3. 记住上次的选择

平台 / 模型 / 风格 / 画质 / 格式勾选等会记在浏览器本地（localStorage），
下次打开或做完一条笔记后自动回填，不用每次重选。

> 注意：**只记配置，不记视频链接** —— 已成功生成的任务不会把链接留在输入框里。

### 4. 自定义视频下载目录

设置 → 下载配置 → 存储，可以指定下载保存目录，支持**弹窗逐层选文件夹**。

### 5. 导出 Markdown 用笔记标题作文件名

导出 .md 时文件名取笔记正文里的第一个一级标题（不再是视频原题），
并自动清理 Windows 文件名非法字符。

### 6. 笔记生成后自动删除视频（可选）

设置里可开启，生成成功后删掉本次的视频/音频，只保留笔记与封面。

---

## 快速开始（Web 端）

**前置要求**：Docker Desktop 已安装并可运行。

    git clone <本仓库地址>
    cd BiliNote

    # 1) 配置环境变量
    cp .env.example .env
    #    按需修改：端口、镜像源等

    # 2) 启动
    docker compose up -d --build

    # 3) 访问
    #    http://localhost:3015

**首次使用建议**：

1. 进「设置 → 模型」填 LLM 的 API Key（抖音抓取不需要，生成笔记需要）
2. 进「设置 → 音频转写配置」选转写器并下载模型（本地 fast-whisper 无需 Key）

## 抖音下载的准备

在仓库根目录双击运行：

    start-douyin-chrome.bat

它会以 headless 模式拉起一个调试端口为 9222 的 Chrome。

**验证是否就绪**：

    curl http://127.0.0.1:9222/json/version

能返回 Chrome 版本信息即可正常下载抖音视频。

> 如果你用仓库里的 BiliNote.bat 启动（或双击桌面快捷方式），
> 它会**自动**完成「拉起抓取 Chrome → 起服务 → 打开界面」这三步。

---

## 已知限制

- **只有 Web 端**，没有桌面客户端（见上文）
- 抖音下载**依赖宿主机 Chrome**：容器内无法自行启动，这是 CDP 方案的前提
- 抖音抓取**需要能访问到那个调试端口**：若部署到远程服务器，需要那台机器上有可访问的 Chrome 调试端口
- 浏览器**拿不到本机文件夹的绝对路径**（安全限制），所以「选择下载目录」是在**容器可见的目录树**里点选

---

## 致谢

- 原始项目：[**BiliNote**](https://github.com/JefferyHcool/BiliNote) by **JefferyHcool**
- 本项目遵循上游的 **MIT License**

如果这个抖音修复对你有帮助，请优先去给**上游项目**点 Star。
