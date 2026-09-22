# Codex 安装与运行入口

目标：让新用户在自己的 Codex 提供本人的照片/视频和文案，必要配置完成后直接得到数字人成片。读完本文件再读 `skills/digital-human-workflow/SKILL.md` 与 [监制执行规范](skills/digital-human-workflow/references/director-runbook.md)。用户请求安装是安装授权，不是购买会员、生成付费媒体或发布个人视频的授权。

## 1. 建立独立环境

- 检查已有安装与用户工作区，复用正确版本；不要把此仓库覆盖到其他项目。首次 clone 到用户选择的独立目录。
- 检查 Python≥3.11、Node≥22.15、Git。若缺少系统依赖，说明官方安装入口与具体需要；不要要求用户执行不明下载脚本。macOS 编译 whisper.cpp 需要 Command Line Tools；Linux 需要 C++ 编译器；Windows 建议 WSL2。
- 在仓库执行 `python3 scripts/bootstrap.py`：创建 `.venv`、固定 Node 依赖及本地 FFmpeg/FFprobe。安装日志在 `.runtime/`。没有读取密钥、创建声像或修改其他仓库的步骤。
- `.venv/bin/python scripts/setup_whisper.py` 下载校验过的 whisper.cpp v1.9.4 与 base 多语言模型，编译本地 DTW 对齐。首次大文件下载/编译可能数分钟；保存进度，不重复下载已通过哈希校验的文件。
- `.venv/bin/python scripts/install_skill.py` 安装到 `~/.agents/skills/digital-human-workflow`。已有不同安装会停止，不覆盖。Windows 用 `--copy`；用户可指定 `--destination`。若当前 Codex 尚未刷新 Skill 列表，可直接阅读仓库 SKILL.md 继续，不必重装。

## 2. 用户数据在本地独立保存

建议 `~/DigitalHumanData`；可改为用户已有目录。用仓库 Python 运行：

```sh
.venv/bin/python -m digital_human --workspace "$HOME/DigitalHumanData" init
.venv/bin/python -m digital_human --workspace "$HOME/DigitalHumanData" doctor
```

后文将 `仓库Python -m digital_human --workspace 用户工作区` 简称 `DH`。Windows 将 Python 路径改为 `.venv/Scripts/python.exe`。不用依赖调用者当前目录来找个人配置。

工作区的 `profile.json` 保存个人偏好和允许的预算，`secrets.json` 保存本地隐藏输入的密钥，`jobs/` 保存私人文案、素材、回执与成果。代码仓库仅有 `config/profile.example.json` 空模板。绝不能把用户工作区提交到 Git 或放进 PR。

## 3. 仅请用户完成不可代办的事

按 Skill 的 [初始化清单](skills/digital-human-workflow/references/onboarding.md) 执行。先查已有配置，只问缺失项。计费路径、密钥所属区域、授权目的地与预算由用户决定。用户自行完成登录/验证码、密钥隐藏输入、本人形象创建与平台同意、短样片试听认可。Codex 负责其余准备和编排。

一次性汇总这些外部条件；之后用户只需提供文案与不同于默认的要求。不要让用户选择内部文件名、填验收 JSON 或亲自搜每段素材。已获同范围授权不因跨阶段重复询问。外观约束从当前用户素材和意愿提取，不继承作者的配饰、穿搭、背景、人物性别或题材。

官方 HeyGen MCP 地址是 `https://mcp.heygen.com/mcp/v1/`；已有连接优先复用。平台/OAuth 的权限以实际工具返回为准。本仓库不用未知第三方中转，不需要额外 OpenAI API key，不打包作者的 MCP 令牌。

配置从 `config/profile.example.json` 开始，用工作区内的 JSON patch 调用 `DH configure --file <patch>`。`null` 的声像 ID、价格、计费路径都要通过实际账户确认；不能填作者 ID 或猜测值。本人形象至少先建好，不能靠本仓库规避平台验证。

## 4. 完成首次校准后持续出片

按 [制作步骤](skills/digital-human-workflow/references/production.md) 执行。用户无需手工生成分镜 JSON 或验收 JSON；这些是 Codex 的职责。CLI 返回待处理动作时继续完成对应阶段，不把它当成最终答复。

- `prepare` 固定原稿/配置；`quality-plan` 检查静态形象和动作匹配，`voice-review` 验收实际配音，`accept-baseline` 保存用户认可模板；`run` 执行到下一个真实依赖。这些记录由 Codex 写，不让用户填表。
- MCP 需要 Codex 调用实际连接工具，CLI 不伪造 OAuth 请求。若连接工具禁止自动轮询，保存 ID、按工具要求显示视频；允许时才恢复下载和包装。向希望完全无人值守的用户说明这个限制与 API 可选方案，不替其购买或切换。
- 不确定的收费结果先查原记录；字幕/动画问题只修本地，不重新生成昂贵声像。
- 输出文件必须真正存在、通过技术与视听检查。交付成片、SRT 和必要素材目录；ZIP 按需生成，避免重复占用。不给仅含脚本或待执行命令的“完成”。

新片使用独立后期，按 [editing.md](skills/digital-human-workflow/references/editing.md) 编写 brief 与剪辑计划。HeyGen 只生成干净人物；字幕、视频插片和混音由本地后期完成并直接导出，不需要桌面剪辑软件或其专用 MCP。

`edit-build` 在原 job 下创建独立修订，不改变旧收费状态。`edit-render` 本地出片，`edit-verify` 检查实际文件，`edit-review` 记录视听验收。用户不需要编辑内部 JSON。保留源素材、手改版本和必要恢复证据；失败产物与重复副本在确认无引用、无活动进程后，按用户授权和项目清理规则处理，不无限保留临时数据。

## 长片的进阶编排

- 根据 [真实素材搜索](skills/digital-human-workflow/references/stock-search.md) 先分解可见动作，再搜站点、预览候选、下载正式文件、裁切和记录来源。选材失败不能用不相关库存片或静态大照片假装满足“视频插片”。
- 按 [人物覆盖与圆框](skills/digital-human-workflow/references/presenter-coverage.md) 选择仅出镜区间生成或持续画中画。`scripts/plan_presenter.py` 只计算覆盖、缺口、句段和 sample 映射，不发起收费。Codex 用用户已批准的工具和预算逐段生成，保存对应回执并组装；不要声称基础 `DH run` 已内置多 reel 编排。
- 长片采用 [有限后台导出](skills/digital-human-workflow/references/render-recovery.md)；完成后用 `DH record-export`（修订加 `--revision`）登记检查与渲染哈希，再走正常 `verify`/视听验收。该程序不访问云端，不自动重试。
- 对照 [制作经验](docs/PRODUCTION-LEARNINGS.md) 检查人物动作、角色声音、字幕占位、动态节奏与真实视频语义，保留已合格部分。新的意见只能在不改变原稿观点与明确要求的前提下优化。

模型、原生清晰度、单次/总时长、水印和价格按当天账户核实；选择由用户决定。能力不足时说明差距和可执行选项，不把免费方案宣传为任意长度、无水印、最高画质。

## 5. 安装验收

广告片、双语字幕和已有成片短版按 [v0.6 广告升级说明](docs/ADVERTISING-UPGRADE.md) 执行。先读 Skill 对应引用，再由 Codex 选择 `production_tools.py` 的字幕、时钟审计与头部裁切工具；不要求用户编写参数。工具只负责本地确定性部分，不能把计划检查当成实际视听通过。用户无需额外安装桌面剪辑工具。

可选素材模型、实拍网站、BGM/音效与出镜方式按本片需求选择；需要账号/授权时沿用已确认路径，不能自动继承作者套餐或付费额度。GPT 内置生图可用时不要求额外 API Key；没有该工具也不伪造已生成结果。

运行 `DH doctor` 与 `.venv/bin/python -m unittest discover -s tests -v`。不使用付费接口来测试安装。初次真实短样片在用户账户授权的预算内进行；这是声像和权限验证，技术单测不能代替它。

升级先保存本地工作区位置、当前任务 ID 和已验证输出；代码仓库升级不迁移/上传用户个人数据。保留原版本与既有素材，依赖发生变化后重做对应本地检查。

## 升级与旧产物

v0.5 已移除专用原生编辑器导出和重定位命令及其依赖。旧 brief 的 editor 字段不再作为受支持的执行路线；新 brief 只需 postproduction.mode=independent。旧工作区与已交付文件不迁移、不删除；需要使用旧工程时保留原版本环境，新后期修改创建独立修订。

### 从 v0.1 升级

确认代码工作树状态，保留本地修改后更新仓库，不强制覆盖或强推。符号链接安装的 Skill 随仓库更新；复制安装运行 `scripts/install_skill.py --update`，仅更新属于本仓库的副本，并保留完整本地备份，不覆盖其他 Skill。

旧 profile 缺少新增的 `minimax.emotion`、`heygen.reference_look_id/motion_prompt` 时按省略处理，不重写旧任务快照或哈希。已提交/已完成任务按原 ID 恢复，升级不要求重新生成。尚未提交的新收费视频增加质量计划和当次配音检查；旧的 approvals 开关不能证明新模板真人感已通过。已有真实认可的视频可先保存计划、导入视频，再登记基线。新任务增加动态验收字段，已交付旧任务保持原结果。

新增检查可能因缺少原素材、无法试听或用户尚未认可新模板停下，这是具体质量条件，不能冒充全流程完成。暂停生成时在私人工作区关闭 generation；恢复须有用户后续指令，升级不会自动打开授权。
