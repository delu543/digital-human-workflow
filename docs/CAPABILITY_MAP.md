# 功能与验收责任

本仓库为独立通用实现；功能移除按当前用户要求明确记录，不修改或迁移私有工程。

## v0.5 有意移除

Removed / Changed Existing Capabilities：移除剪映专用集成、原生草稿导出/重定位命令、第三方序列化模块及相关文档。保留独立剪切、时间映射、字幕、画中画、插片、混音和 MP4 导出。旧用户工程与已交付文件不删除，新素材包不自动附带旧编辑器扩展。

| 能力 | 实现/状态真源 | 验收要求 |
|---|---|---|
| 首次安装与 Skill 安装 | scripts/bootstrap.py、install_skill.py | 独立目录与无覆盖 |
| 用户配置与私密凭证 | config.py、工作区 profile/secrets | 空模板、隐藏输入、无日志回显 |
| 配音/一次声音克隆 | providers/minimax.py、cloning.py | 回执复用、本人试听、预算含激活 |
| HeyGen API | providers/heygen.py、cloud.py | 实际 look ID、原配音资产、异步 ID |
| HeyGen 会员 | Skill + 官方 MCP，job.json | 工具权限内执行、无账单切换 |
| 恢复与重复收费保护 | storage.py、budget.py、cloud.py | 超时/中断/撤销授权单测 |
| 源素材检查 | media.inspect_source、本地 evidence | 元数据、连续片段；不自动判断眼部或光线质量 |
| 生成前质量计划 | quality.py、quality-plan.json | 静态形象、姿势/机位、引擎能力；缺失时上传前阻止 |
| 用户指定模型约束 | brief.model_requirements、storage.py、quality.py | 任务绑定要求；MiniMax/HeyGen 实际付费参数不符时阻止，旧任务恢复兼容 |
| 本次配音验收 | quality.py、voice-review.json | 绑定最终音频哈希；转写不能代替试听 |
| 真人感模板复用与撤销 | 私人工作区 baselines/、revoke-baseline | 用户真实认可；声像/动作变化或明确否定使模板停止复用；保留源证据与已付费恢复 |
| 参数与提示词分层 | providers、references/prompts.md | API/MCP同一参数源，V不传expressiveness |
| 字幕 | alignment.py | 实际 token 时间、原稿一致 |
| 分镜/图片/动画 | Skill、composition.py、sources.json | 意义吻合、权利可用、脸部安全 |
| 渲染 | media.py、Hyperframes | 本地版本固定，检查与工程对应 |
| 交付 | delivery.py、review.json | 全解码、视听证据、ZIP完整性 |

API 适配器协议测试、免费短样片验证、五分钟本地渲染与五分钟云端真人生成是不同证据，具体范围见 VALIDATION.md。没有已有用户配置时，缺失的登录、本人同意、音色与形象验收是外部条件，不能填占位值绕过。

v0.2 未移除 API、会员 MCP、导入、克隆、字幕、动画、渲染或素材包能力。行为变化是新收费视频增加质量条件、新任务交付增加动态证据；旧已提交请求仍只恢复。没有覆盖既有素材或默认切换模型/账单。

## v0.3 新增与保留

| 能力 | 状态 | 实现/验收边界 |
|---|---|---|
| 全数字人独立后期 | active | editing / edit_timeline；新修订，收费声像复用 |
| 剪切、重排、同步变速 | active | 同一来源映射驱动画面、声音、字幕；不剪穿发音区间 |
| 视频/图片插片与分轨混音 | active | add-media + overlays/audio；来源和哈希登记 |
| 位置、缩放、旋转、透明度关键帧 | active | editor-independent timeline + Hyperframes；线性曲线 |
| 干净人物与独立字幕 | active | avatar 专用生成路径 + alignment；不要求 HeyGen 包装 |
| 原有 storyboard/自定义 HTML | active | 原路径保留；自定义 HTML 不伪装成可通用无损导出 |
| 新供应商视频生成 API | 未内置 | Codex 用已授权工具准备本地结果，再登记插片 |

新片采用 independent 后期分支；旧任务继续原分支，无隐式迁移。

## v0.4 新增与边界

| 能力 | 实现/状态 | 验收和适配边界 |
|---|---|---|
| 最少输入与监制流程 | Skill / director-runbook | Codex 生成需求覆盖和内部计划；账号同意、首次声像认可仍需本人 |
| 实拍视频检索 | Skill / stock-search | 有实际 Pexels 选材经验；网页/API 由 Codex 调用可用工具，未新增通用素材 API 适配器 |
| 分段人物覆盖规划 | coverage.py / plan_presenter.py | 整数音频 sample、已覆盖扣除、完整语句装 reel；不自行生成或计费 |
| 多 reel / 连续圆框 | Skill + 现有生成路径 + 自定义合成 | Codex 编排高级分支；并非基础 run 全自动多 reel；声音/口型映射另验收 |
| 真圆蒙版 | edit_hyperframes.py | 以短轴计算圆半径；头部裁切仍需针对用户素材，非自动人脸跟踪 |
| 一次性独立导出 | export_worker.py / export_project.py | 本地前台或 macOS LaunchAgent，超时和次数边界；需要支持硬链接的输出文件系统 |
| 导出登记恢复 | record-export | 工程/视频哈希、检查报告、无覆盖写入；已有交付状态不倒退 |
| 渲染兼容适配 | hf-compat.mjs，Hyperframes 0.8.48 | 内存适配竖屏捕获和审计采样；版本不符停止，Node ≥22.15 |
| 进程停止 | processes.py / psutil | 跟踪本任务子进程包括独立会话；不按名称关闭其他浏览器，不是系统沙箱 |

原 API/MCP/import、声音克隆、预算/不确定请求保护、字幕、storyboard、独立剪辑与 ZIP 均保留。默认素材目录、ZIP 按需是工作流选择，未移除打包命令。无私人配置迁移；不得把个人已验收的长片推广成所有用户/平台均已验证。
