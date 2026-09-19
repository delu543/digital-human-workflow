# 职责、数据与边界

```mermaid
flowchart LR
  U[用户文案与已授权配置] --> J[本地固定任务与预算记录]
  J --> M[MiniMax 本人配音]
  M --> H[HeyGen API 或官方 MCP]
  H --> A[下载本人数字人音视频]
  A --> T[本地声学字幕对齐]
  T --> C[Codex 语义分镜和素材权利记录]
  C --> F[Hyperframes 本地合成]
  F --> Q[技术检查及视听验收]
  Q --> D[MP4 / SRT / 完整素材包]
```

配置模板仅定义规格，个人配置独立保存。`Workspace` 管理工作区，`Job` 固定原稿、配置与素材哈希；本地原子写入和任务锁避免并发写坏。`budget` 在网络副作用前预留金额/credits，`cloud` 保存回执与远端 ID，`providers` 只负责官方接口协议。预算预留不是供应商账单。

`runner` 执行可以确定的阶段；语义分镜、官方 MCP、视听验收留给 Codex 按 Skill 执行，不能用“全自动”掩盖这些职责。`alignment` 只接受声学时间；`composition` 生成可编辑 HTML/GSAP 工程；`media` 固定本地编码器；`delivery` 将渲染与检查绑定到工程/文件哈希并白名单打包。

用户工作区布局：

```text
profile.json / secrets.json       个人偏好、权限与凭证
jobs/<id>/script.txt, profile.json 固定任务输入
jobs/<id>/job.json                阶段、收费请求、远端ID、素材哈希
jobs/<id>/receipts/               私有接口回执，可恢复但不交付/公开
jobs/<id>/assets/, project/       原始素材与本地可编辑工程
jobs/<id>/captions.json           声学字幕
jobs/<id>/timeline.json           实际时间轴与分镜
jobs/<id>/sources.json            来源和使用权
jobs/<id>/evidence/               私有检查证据
jobs/<id>/exports/                成片与完整素材包
```

网络数据流：MiniMax 接收所选站点的脚本和声音样本；HeyGen 接收用户音频和形象 ID；本地对齐、分镜与渲染不要求向第三个转写服务上传。安装从 npm/PyPI/GitHub/Hugging Face 下载固定依赖，Hyperframes 遥测关闭。Codex 自身的数据处理取决于用户的 Codex 配置；不能把本地渲染误说成整个会话完全离线。

本版本适合单用户 Codex 工作区，不是多租户托管 SaaS：未实现集中计费、跨设备队列、对象存储与账户权限系统。源代码可以扩展，但这些能力不能从“GitHub 开源”推断为已存在。
