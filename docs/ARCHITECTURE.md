# 职责、数据与边界

```mermaid
flowchart LR
  U[用户文案与已授权配置] --> J[本地固定任务与预算记录]
  J --> P[来源/静态形象/动作/模型能力检查]
  P --> M[MiniMax 本人配音]
  M --> V[当前配音试听与哈希验收]
  V --> H[HeyGen API 或官方 MCP]
  H --> A[下载本人数字人音视频]
  A --> T[本地声学字幕对齐]
  T --> C[Codex 语义分镜和素材权利记录]
  C --> E[独立剪辑计划和统一时间轴]
  E --> F[Hyperframes 本地成片]
  E --> N[可选 Mac 剪映多轨草稿]
  N --> G[目标剪映 UI 编辑与验收]
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

## v0.2 质量责任

quality.py 管理生成前计划、配音哈希验收和私人模板基线；API 与 MCP 在上传/提交之前共享检查，runner 把缺失条件返回给 Codex。供应商适配负责正确参数和传输，不判断美学；avatar_payload 同时生成 API 和 MCP 参数，避免两条路径漂移。已提交请求恢复分支读取原 ID/回执，不经过新的付费创建分支。

新任务标记 quality_version=1，delivery 要求连续片段与音轨依据；旧已交付任务仍可恢复。配置保持 schema_version=1，新增字段为可选、默认省略，不对旧任务做隐式迁移。证据结构检查无法判定检查者是否真的看过/听过，更不等于自动真人感评分。

## v0.3 后期责任

edit_timeline 将源时间 ranges 与成片时间 overlays/audio 编译为整数微秒时间轴。每段数字人和旁白共享同步组与速度；字幕从原声学 cue 映射，不能估算或独立漂移。editing 创建 jobs/<id>/edits/<revision>/ 的完整独立快照，原 job 的云端操作不变。

edit_hyperframes 和 edit_jianying 消费同一时间轴。后者只调用所保留的 MIT 纯 serializer，在任务 exports 内写全新工程，不修改剪映首页、启动程序或调用内部动态库。跨机器用 portable-plan 重建绝对路径；若原生文件已被手改则拒绝从旧计划覆盖。复杂 HTML 的 edit-seal 标记会阻止不一致的原生导出。

旧 composition 和 run --storyboard 仍可用。新 brief 的 postproduction.mode=independent 使 runner 在干净素材与字幕就绪后返回 needs_edit_plan，由 Codex 执行后续命令。工具选择由交付和用户要求决定，不固定剪映依赖。单纯增加后期层不能修复源人物的身份、眼神或口型缺陷。
