# 第三方说明

本仓库原创代码使用 MIT；不改变依赖、字体、供应商及用户素材的原有许可。

- Hyperframes 0.8.48：Apache-2.0，经 npm 安装，未复制上游源码到本仓库。
- GSAP 3.14.2：Standard No Charge GSAP License，**不是 MIT**。通过固定 npm 依赖安装，渲染工程包含保留原版权头的 `gsap.min.js`。使用/再分发须遵守其条款，特别是竞争性可视化动画构建产品限制。[许可](https://gsap.com/community/standard-license/)
- Noto Sans CJK SC Regular：SIL Open Font License 1.1。随仓库附带未修改字体和 `templates/assets/OFL.txt`；不能单独销售字体或擅用保留字体名称。
- whisper.cpp v1.9.4：MIT，安装时获取原始源码与原许可证。base 模型来自 whisper.cpp 官方模型发布来源并校验 SHA-256。
- Requests：Apache-2.0；imageio-ffmpeg：BSD-2-Clause；@ffprobe-installer/ffprobe 包：按其 npm 包许可。FFmpeg/FFprobe 的具体二进制按其编译选项对应的 LGPL/GPL 条款使用；不因 Python/npm 包许可而改变。运行时本地下载，不提交二进制到本仓库。
- Jianying Local MCP：MIT；仅保留提交 `f47f907e7bc15e68082238e50ca5964c50b2f559` 的 `native.py`、`advanced_native.py` 两个未修改的纯数据序列化模块。原作者署名、许可证、第三方说明及其引用的许可文本见 [vendor/jianying](src/digital_human/vendor/jianying/)。不包含其 MCP 服务、素材案例、文件系统管理器或剪映二进制；本仓库适配层另行实现。
- MiniMax 与 HeyGen 属于外部服务，账户订阅、形象/声音权利及生成内容使用遵守各平台适用条款。平台水印保留。

`mcncarl/jianying-headless` 仅用于研究剪辑决策、版本约束与验收方法，没有复制代码或调用其原生引擎。所核查版本是个人学习/非商业许可，不在本产品中分发；商业客户若独立选择使用，须先取得上游书面商业许可。本项目的 MIT 不改变该限制。

重分发运行时或制作商用衍生产品前，核对实际依赖 LICENSE 和 FFmpeg `-version` / build 配置；本仓库的 MIT 不能为用户的照片、录音、配乐或第三方媒体授予权利。
