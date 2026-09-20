# Codex 安装与运行入口

目标：让新用户在自己的 Codex 提交文案与视觉要求，得到自己的数字人成片和素材包。读完本文件再读 `skills/digital-human-workflow/SKILL.md`。用户请求安装是安装授权，不是购买会员、生成付费媒体或发布个人视频的授权。

## 1. 建立独立环境

- 检查已有安装与用户工作区，复用正确版本；不要把此仓库覆盖到其他项目。首次 clone 到用户选择的独立目录。
- 检查 Python≥3.11、Node≥22、Git。若缺少系统依赖，说明官方安装入口与具体需要；不要要求用户执行不明下载脚本。macOS 编译 whisper.cpp 需要 Command Line Tools；Linux 需要 C++ 编译器；Windows 建议 WSL2。
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

官方 HeyGen MCP 地址是 `https://mcp.heygen.com/mcp/v1/`；已有连接优先复用。平台/OAuth 的权限以实际工具返回为准。本仓库不用未知第三方中转，不需要额外 OpenAI API key，不打包作者的 MCP 令牌。

配置从 `config/profile.example.json` 开始，用工作区内的 JSON patch 调用 `DH configure --file <patch>`。`null` 的声像 ID、价格、计费路径都要通过实际账户确认；不能填作者 ID 或猜测值。本人形象至少先建好，不能靠本仓库规避平台验证。

## 4. 完成首次校准后持续出片

按 [制作步骤](skills/digital-human-workflow/references/production.md) 执行。用户无需手工生成分镜 JSON 或验收 JSON；这些是 Codex 的职责。CLI 返回待处理动作时继续完成对应阶段，不把它当成最终答复。

- `prepare` 固定原稿/配置；`quality-plan` 检查静态形象和动作匹配，`voice-review` 验收实际配音，`accept-baseline` 保存用户认可模板；`run` 执行到下一个真实依赖。这些记录由 Codex 写，不让用户填表。
- MCP 需要 Codex 调用实际连接工具，CLI 不伪造 OAuth 请求。若连接工具禁止自动轮询，保存 ID、按工具要求显示视频；允许时才恢复下载和包装。向希望完全无人值守的用户说明这个限制与 API 可选方案，不替其购买或切换。
- 不确定的收费结果先查原记录；字幕/动画问题只修本地，不重新生成昂贵声像。
- 输出文件必须真正存在、通过技术与视听检查。交付成片、SRT、完整 ZIP；不给仅含脚本或待执行命令的“完成”。

v0.3 新片默认使用独立后期，按 [editing.md](skills/digital-human-workflow/references/editing.md) 编写 brief 与剪辑计划。HeyGen 只生成干净人物；字幕、视频插片和混音由本地后期完成。用户指定剪映时额外生成原生草稿；否则无需安装剪映。原生交付复用了随仓库保留 MIT 许可的纯序列化模块，不需要再安装整个 MCP 服务。目标 Mac 剪映的实际兼容性必须另做短工程验收，不能由安装成功推断。

`edit-build` 在原 job 下创建独立修订，不改变旧收费状态。`edit-render` 本地出片；`edit-export` 生成可选原生草稿；`relink-draft` 在全新目录重建路径。跨机器交付时由 Codex 处理本地重定位和目标编辑器 UI 检查，用户不需要编辑内部 JSON。源草稿、手改版本和失败产物均保留。

## 5. 安装验收

运行 `DH doctor` 与 `.venv/bin/python -m unittest discover -s tests -v`。不使用付费接口来测试安装。初次真实短样片在用户账户授权的预算内进行；这是声像和权限验证，技术单测不能代替它。

升级先保存本地工作区位置、当前任务 ID 和已验证输出；代码仓库升级不迁移/上传用户个人数据。保留原版本与既有素材，依赖发生变化后重做对应本地检查。

## 从 v0.1 升级

确认代码工作树状态，保留本地修改后更新仓库，不强制覆盖或强推。符号链接安装的 Skill 随仓库更新；复制安装运行 `scripts/install_skill.py --update`，仅更新属于本仓库的副本，并保留完整本地备份，不覆盖其他 Skill。

旧 profile 缺少新增的 `minimax.emotion`、`heygen.reference_look_id/motion_prompt` 时按省略处理，不重写旧任务快照或哈希。已提交/已完成任务按原 ID 恢复，升级不要求重新生成。尚未提交的新收费视频增加质量计划和当次配音检查；旧的 approvals 开关不能证明新模板真人感已通过。已有真实认可的视频可先保存计划、导入视频，再登记基线。新任务增加动态验收字段，已交付旧任务保持原结果。

新增检查可能因缺少原素材、无法试听或用户尚未认可新模板停下，这是具体质量条件，不能冒充全流程完成。暂停生成时在私人工作区关闭 generation；恢复须有用户后续指令，升级不会自动打开授权。
