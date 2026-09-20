# 功能与验收责任

本仓库为独立通用实现，不修改或迁移作者原私有工程；没有删除原功能或上传原用户数据。

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
| 原生剪映草稿和重定位 | experimental | 两个 MIT 纯序列化模块；目标 Mac 版本/UI 未由本版验证 |
| 原有 storyboard/自定义 HTML | active | 原路径保留；自定义 HTML 不伪装成可通用无损导出 |
| 新供应商视频生成 API | 未内置 | Codex 用已授权工具准备本地结果，再登记插片 |
| 原生无界面导出/任意加密草稿编辑 | 未采用 | 不复制受限参考实现，不宣称所有参考仓库功能已移植 |

Removed / Changed Existing Capabilities：无功能移除。新片可选 independent 后期分支；旧任务继续原分支，无隐式迁移。剪映是可选后端，缺少它不阻断本地 MP4 路径。
