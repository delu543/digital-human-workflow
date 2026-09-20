# 数字人工作流

**把文案变成本人数字人口播、字幕、配图与动画成片，并交付完整素材包。**

Codex 负责理解文案、分镜与执行，MiniMax 负责用户自己的声音，HeyGen 负责本人数字人，Hyperframes 在本地合成。默认中文、9:16、1080×1920，目标约五分钟；实际时长由配音决定。

这是可安装的通用工作流与 Codex Skill，不包含作者账号、录音、私人文案、形象、密钥或个人配置。每位用户在自己的电脑保存自己的素材与账户设置。

当前版本 **v0.2.0**：增加素材诊断、分层提示词、当次配音验收、可复用真人感基线和动态检查。详见 [更新记录](CHANGELOG.md) 与 [真人感流程](skills/digital-human-workflow/references/realism.md)。

## 给第一次使用的人

把下面这段话发给你自己的 Codex：

> 请阅读 https://github.com/delu543/digital-human-workflow 的 INSTALL_FOR_CODEX.md，在独立目录安装“数字人工作流”和它的 Skill，引导我完成必要的账号、声音、数字人与预算配置。计费路径由我选择，不使用作者的账号或素材。

首次准备后，在 Codex 输入：

> 用“数字人工作流”制作这段文案，竖屏，字幕清晰，按内容加配图与简洁动画，沿用我已确认的声音、形象与预算。文案：……

你需要亲自完成的通常只有：平台注册/订阅选择、密钥在本地隐藏输入、本人数字人创建与平台同意、第一次声音/形象试听确认、费用上限授权。其他安装、分镜、字幕、渲染、检查和打包由 Codex 执行。详见 [安装入口](INSTALL_FOR_CODEX.md)。

## 可以选择自己的计费方式

| HeyGen 路径 | 账户需求 | 自动化边界 |
|---|---|---|
| 会员 + 官方 MCP/OAuth | 当前账户支持相应功能与额度 | 受工具权限和状态查询规则约束，可能需说“继续” |
| API | 用户自己的 API key 与可用额度 | 支持提交、保存远端 ID、查询、恢复与下载 |
| 导入已有视频 | 已有授权声像素材 | 本地完成字幕、配图、动画和交付 |

程序不会因会员额度不足自动切到 API，不把 Pro 当成 API 余额。价格和单条预算由用户根据当前账户填写；不预设任何套餐为必选。MiniMax 国内/国际站按密钥来源配置，中文本身不决定站点。

## 交付内容

- MP4 成片与 SRT 字幕。
- 配音、原始数字人视频、使用到的配图、分镜和真实时间轴。
- 可编辑的 Hyperframes 工程、来源/权利记录、验收结果与 SHA-256 清单。
- 完整素材 ZIP；密钥、账号配置和云端签名回执不进入素材包。

内置标题、关键词字幕、步骤图、带来源的柱图和插图场景；更复杂的动画由 Codex 编辑本地 Hyperframes 工程。它不会仅凭一句话自动判断所有美术要求，也不会用均分时长假装精准字幕。

## 技术安装

需要 Python 3.11+、Node.js 22+、Git；本地中文对齐还需 C++ 编译器。首次联网下载依赖和约148MB base 模型，不会调用付费生成接口。

```sh
git clone https://github.com/delu543/digital-human-workflow.git
cd digital-human-workflow
python3 scripts/bootstrap.py
.venv/bin/python scripts/setup_whisper.py
.venv/bin/python scripts/install_skill.py
.venv/bin/python -m digital_human --workspace "$HOME/DigitalHumanData" init
.venv/bin/python -m digital_human --workspace "$HOME/DigitalHumanData" doctor
```

Windows 建议 WSL2；原生 Windows 的 Python 路径为 `.venv/Scripts/python.exe`。macOS 已执行本地媒体验证，其他系统的测试范围见 [验证说明](docs/VALIDATION.md)。无需自己写编排命令，Codex 会根据 [Skill](skills/digital-human-workflow/SKILL.md) 继续。

## 稳定性的实际边界

收费调用先保存状态，不确定结果不自动重试；本地字幕/合成失败不会重新收费生成；已完成素材按哈希恢复。用户修改文案、声像或计费路径时创建新任务，修改包装可复用既有声像。

它仍依赖供应商权限、余额、网络和素材质量。首次样片验收不能代替每条视频的口型、字幕和视觉检查；本地五分钟压力测试也不能证明所有账户都能生成五分钟云端视频。现有验证和未验证部分明确列在 [验证说明](docs/VALIDATION.md)，不作“永不失败”的承诺。

[安装与新人流程](INSTALL_FOR_CODEX.md) · [架构与职责](docs/ARCHITECTURE.md) · [费用与恢复](skills/digital-human-workflow/references/billing-and-recovery.md) · [来源与许可证](docs/DEPENDENCIES.md)

原创代码 MIT；第三方字体、GSAP、编码器等按各自许可证使用，见 [NOTICE](NOTICE.md)。
