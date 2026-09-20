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
| 本次配音验收 | quality.py、voice-review.json | 绑定最终音频哈希；转写不能代替试听 |
| 真人感模板复用 | 私人工作区 baselines/ | 用户真实认可；声像/动作变化使模板失效 |
| 参数与提示词分层 | providers、references/prompts.md | API/MCP同一参数源，V不传expressiveness |
| 字幕 | alignment.py | 实际 token 时间、原稿一致 |
| 分镜/图片/动画 | Skill、composition.py、sources.json | 意义吻合、权利可用、脸部安全 |
| 渲染 | media.py、Hyperframes | 本地版本固定，检查与工程对应 |
| 交付 | delivery.py、review.json | 全解码、视听证据、ZIP完整性 |

API 适配器协议测试、免费短样片验证、五分钟本地渲染与五分钟云端真人生成是不同证据，具体范围见 VALIDATION.md。没有已有用户配置时，缺失的登录、本人同意、音色与形象验收是外部条件，不能填占位值绕过。

v0.2 未移除 API、会员 MCP、导入、克隆、字幕、动画、渲染或素材包能力。行为变化是新收费视频增加质量条件、新任务交付增加动态证据；旧已提交请求仍只恢复。没有覆盖既有素材或默认切换模型/账单。
