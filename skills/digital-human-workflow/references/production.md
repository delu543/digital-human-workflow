# 从文案到完整素材包

`DH` 的解释见 SKILL.md。操作均针对用户私人工作区；JSON 由 Codex 编排，普通用户无需写命令。

先按 [导演手册](director-runbook.md) 完成需求覆盖与出镜策略；长片/圆框的付费覆盖见 [presenter-coverage.md](presenter-coverage.md)，实拍检索见 [stock-search.md](stock-search.md)。

v0.4 新片默认采用独立后期：brief 加 `postproduction.mode=independent`，以干净数字人素材完成下面第 1–3 步，随后按 [editing.md](editing.md) 执行剪辑、渲染和可选剪映导出。第 4–8 步保留为原有 storyboard/复杂 Hyperframes 路径；无需为了选择后期工具重生成声像。全流程维持数字人出镜，不自动切换到真人实拍。

1. 保存用户文案到工作区 `inputs/script.txt`，视觉要求写 `brief.json`。忠实保留原稿，预估五分钟只能作为计划；不要静默扩写或剪短。用户明确要求的模型经核实后写入 `brief.model_requirements`（见 realism.md），并使配置一致；这部分任务创建后不可移除或改低。`DH prepare --script <路径> --brief <路径>` 返回任务 ID。保存这个 ID，后续只恢复它。
2. 先按 [真人感流程](realism.md) 和 [提示词库](prompts.md) 完成 `quality-plan`，检查来源、静态形象、动作匹配与当前模型支持。旧模板用 `--reuse-baseline`，过期能力信息只读刷新；新模板使用有时长上限的 calibration。`run` 返回 `needs_quality_plan` 时这是 Codex 的工作，不能绕过它调用云端。计划通过后 `DH run <id>` 生成/复用配音，返回 `needs_voice_review`；实际试听，按当前 SHA256 完成 `voice-review`。随后 `DH run <id> --wait-seconds 30` 才提交 HeyGen。新模板短片需用户认可后 `accept-baseline`，再制作正式长片。API 完成后下载，MCP 按下一节执行。旧任务恢复原 ID，不重放收费请求；`import` 路径仍可用 `DH import <id> --voice <音频> --avatar <视频>` 做纯本地包装。
3. 字幕从实际数字人音轨提取。默认本地 whisper.cpp DTW，不外传给转写网站。如果原稿与转写不一致，检查发音、专有名词、标点/繁简差异及原始声学 token；可提供有音频依据的修正 token 文件给 `DH align <id> --transcript <文件>`，格式 `[{"text":"实际词","start":实际秒数}]`。不能按字数造时间，不能猜改听不清的内容。需要更强模型时用户安装受支持模型并设置 `DH_WHISPER_MODEL` 后 `align --model small/medium/large-v3`；不得循环盲目重做付费声音。
4. `needs_storyboard` 后实际查看源视频截帧和 `captions.json`。为文意选标题、关键词、步骤、图解/配图；卡片安排在空白区域，留五官、口型与平台边栏安全区。五分钟视频应有随论证变化的画面，不机械每句一张卡。参考仓库 `examples/storyboard.json` 的字段，`start_caption` 是从0开始的字幕编号。
5. 图片先 `DH add-image <id> --file <本地图片> --source <来源说明> --rights <权利依据>`，再在 storyboard 引用返回的相对路径。SVG 图解可本地制作；照片用用户授权图片或已获准的图像工具。数据柱图必须有真实数据与来源，不为视觉效果杜撰。新增图片工具的付费/上传需在用户授权内。
6. `DH run <id> --storyboard <分镜文件>` 自动合成、检查、渲染。内置 title/steps/bars/image；复杂视觉可编辑该任务 `project/` 的 Hyperframes HTML/GSAP，动画按真实时间轴编排，媒体和字体保持本地。先读 Hyperframes 当前文档/已安装技能，编辑后 `DH seal-project <id>`、`DH check <id>`、`DH render <id>`。已渲染的版本须新任务导入音视频保留历史，不能覆盖。
7. `DH verify <id>` 验证尺寸、音轨、时长、全文件解码和工程版本并抽取成片帧。可用 `DH inspect-source <id> --file <成片路径>` 提取连续检查片段；实际查看全部截帧，抽看开头、中间、结尾及所有转场，核对人物、声音、字幕、图解与口型。只看截图不能证明动态自然。如当前工具不能听/播放，不虚构已听；仅请用户完成这一项必要视听，或在合适情形引用已认可原声及可核实的音轨比较证据。
8. 按仓库 `examples/review.example.json` 写真实证据。新任务需包含 motion、scene、`inspected_segments`（start/end/method/evidence）与 `audio_review`。动态 method 为 video_playback 或 user_confirmation；音轨为 listened/user_confirmation/approved_source_comparison，最后一项必须有已认可源音频及实际比较依据。执行 `DH review <id> --file <验收文件>`；按需 `DH bundle <id>`。提供 `exports/final.mp4`、`subtitles.srt` 与必要素材目录；用户需要 ZIP 再调用 bundle，保留既有打包能力但不默认复制大包。包内含文案、分镜、原始声像、字幕、素材来源、可编辑工程、检查与清单；不含密钥、账号配置、原始训练文件或云端签名回执。素材包本身属于用户私人交付，不能上传公共仓库。

## 会员 MCP 的实际执行

`run` / `mcp-begin` 返回的是待执行动作，尚未调用云工具：

- `upload_audio_with_official_mcp`：查当前官方工具，申请音频 direct upload，回执保存到工作区私有 `receipts/`；`DH put-upload <id> --receipt <回执>` 只上传本任务配音，再调用官方 complete upload，`DH record-remote <id> --asset-id <返回ID>`。
- 再 `DH mcp-begin <id>` 会先保存预算与请求，返回精确的本人 avatar/audio 参数。调用官方 `create_video_from_avatar` **一次**，不使用自动代写、自动选人或内置 TTS 的泛化接口。
- 此步仅生成干净人物口播，不让 HeyGen 烧录后期字幕、配乐或插片；按实际工具 schema 使用明确支持的参数，不发明 caption 开关。完成后检查是否带有非预期包装，保留平台要求的水印。
- 返回视频 ID 后立即 `DH record-remote <id> --video-id <ID>`，并遵守工具要求调用 `show_video`。若工具禁止后续状态查询，停止该依赖阶段，等待用户允许的“继续”或工具通知；保存 ID，不重建视频。工具不支持所需动作时明确报告，不使用隐藏网页接口绕过。
- 获得已完成回执后保存 JSON，`DH receive <id> --receipt <回执>` 下载并校验，继续 `run`。不得把签名下载 URL 或 OAuth 令牌写进公开文本。

长片独立导出通过 [render-recovery.md](render-recovery.md) 接回 record-export/verify/review；不得只把导出成功日志当交付。默认小规模视听修订不重做云端声像。
