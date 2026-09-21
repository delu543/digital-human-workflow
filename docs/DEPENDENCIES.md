# 采用的成熟方案

接口依据核对日期：2026-09-19；剪辑集成核对日期：2026-09-20。供应商文档会变化；实际账号与接口响应优先，升级需重新跑对应测试。

| 依赖 | 版本/来源 | 采用范围与边界 |
|---|---|---|
| Hyperframes | [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes), 0.8.48 | HTML/GSAP 本地渲染、check，不引入整套托管服务 |
| GSAP | 3.14.2，npm lock 固定 | 可定位时间轴动画，许可见 NOTICE |
| whisper.cpp | [ggml-org/whisper.cpp](https://github.com/ggml-org/whisper.cpp), v1.9.4 | 本地中文 DTW 字词时间；关闭 flash attention |
| Noto CJK | [notofonts/noto-cjk](https://github.com/notofonts/noto-cjk) | 仓库内原始字体 SHA-256 为 `2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b`，OFL 同目录 |
| Requests / imageio-ffmpeg | 2.34.2 / 0.6.0 | HTTPS、便携编码器，无浏览器凭证抓取 |
| psutil | [giampaolo/psutil](https://github.com/giampaolo/psutil)，7.2.2 / BSD-3-Clause | 独立导出器追踪和停止本任务进程树；不扫描或杀死无关浏览器 |
| FFprobe installer | 2.1.2 | 选当前平台预编译探测工具，固定 lock |



采用本地轻量编排而不引入通用队列/工作流服务器：目标是在个人 Codex 内执行，所需状态是每任务文件、锁和远端 ID；更大系统会增加部署与凭证暴露面。Whisper 转写并不保证每个专有名词正确，所以一致性检查失败必须回看音频，不能以“模型给了结果”为验收。

官方接口与使用说明：

- [HeyGen audio-to-video](https://developers.heygen.com/audio-to-video)：上传音频资产后生成 avatar video，不使用 HeyGen TTS 覆盖 MiniMax 音色。
- [HeyGen assets](https://developers.heygen.com/assets)：API multipart 或官方 MCP direct upload；保存资产 ID。
- [HeyGen MCP](https://developers.heygen.com/mcp/overview)：官方 OAuth，工具可用性与会员额度按实际账户核实。
- [MiniMax 同步语音](https://platform.minimax.io/docs/api-reference/speech-t2a-http)：`speech-2.8-hd`、hex 音频输出，按所选站点认证。
- [MiniMax 声音克隆](https://platform.minimax.io/docs/api-reference/voice-cloning-clone)：首次样本与试听，已有音色不重复克隆。
- [Codex Skills](https://developers.openai.com/zh-Hans/docs/build-skills)、[Codex MCP](https://developers.openai.com/codex/mcp)：当前安装发现与连接规则；本仓库不强绑某个 Codex 模型或另购 OpenAI API。

模型、计费、套餐名称不属于固定开源依赖版本。代码固定默认模型以保留已验收输出，但允许用户配置；不要因为发布了新模型而自动更换用户音色效果。

v0.4 核对日期：2026-09-21。Hyperframes 0.8.48 的两个精确位置通过 Node `registerHooks` 在内存适配，保留 Apache-2.0 来源说明；不修改分发包，不自动升级。适配范围只有 macOS 竖屏捕获保护和 appearsBy 截止时间补采样；原断言/阈值保留。psutil 用法依据 [官方进程 API](https://psutil.io/)，采用发布版本的进程身份校验和子进程枚举，减少平台自写进程管理代码。

素材方法参考 [Pexels API](https://www.pexels.com/api/documentation/)、[Pexels License](https://www.pexels.com/license/) 与 [Mixkit License](https://mixkit.co/license/)；未把素材库或电影片段打包入仓库。[VideoSeek](https://github.com/6v17/VideoSeek) 仅列为大量已授权本地媒体的可选索引，AGPL-3.0，未安装/复制/集成。macOS 一次性任务依据 [Apple launchd 文档](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html)，不引入常驻工作流服务。
