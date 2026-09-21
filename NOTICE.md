# 第三方说明

本仓库原创代码使用 MIT；不改变依赖、字体、供应商及用户素材的原有许可。

- psutil 7.2.2：BSD-3-Clause，版权与条款见 [上游 LICENSE](https://github.com/giampaolo/psutil/blob/release-7.2.2/LICENSE)；通过正常包安装，不复制/修改其源码。
- `scripts/hf-compat.mjs` 针对 Hyperframes 0.8.48（HeyGen / Apache-2.0）精确代码上下文做运行时兼容适配，改变捕获保护与审计采样；上游源码和 LICENSE 留在正常安装的依赖中，不重分发修改后的包。

- Hyperframes 0.8.48：Apache-2.0，经 npm 安装，未复制上游源码到本仓库。
- GSAP 3.14.2：Standard No Charge GSAP License，**不是 MIT**。通过固定 npm 依赖安装，渲染工程包含保留原版权头的 `gsap.min.js`。使用/再分发须遵守其条款，特别是竞争性可视化动画构建产品限制。[许可](https://gsap.com/community/standard-license/)
- Noto Sans CJK SC Regular：SIL Open Font License 1.1。随仓库附带未修改字体和 `templates/assets/OFL.txt`；不能单独销售字体或擅用保留字体名称。
- whisper.cpp v1.9.4：MIT，安装时获取原始源码与原许可证。base 模型来自 whisper.cpp 官方模型发布来源并校验 SHA-256。
- Requests：Apache-2.0；imageio-ffmpeg：BSD-2-Clause；@ffprobe-installer/ffprobe 包：按其 npm 包许可。FFmpeg/FFprobe 的具体二进制按其编译选项对应的 LGPL/GPL 条款使用；不因 Python/npm 包许可而改变。运行时本地下载，不提交二进制到本仓库。
- MiniMax 与 HeyGen 属于外部服务，账户订阅、形象/声音权利及生成内容使用遵守各平台适用条款。平台水印保留。


重分发运行时或制作商用衍生产品前，核对实际依赖 LICENSE 和 FFmpeg `-version` / build 配置；本仓库的 MIT 不能为用户的照片、录音、配乐或第三方媒体授予权利。
