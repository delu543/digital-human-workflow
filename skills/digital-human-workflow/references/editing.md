# 全数字人的独立后期（v0.5）

目标是用户的数字人。训练视频用于创建或校准身份，不擅自改为真人实拍出镜方案。已有数字人素材可以导入后继续剪辑，无需重新生成。

## 职责与依赖

- MiniMax 先完成已认可音色的配音，检查表达、停顿和读音，再生成口型。
- HeyGen 只负责干净的数字人口播；使用本人形象和确定的音频，不同时承担字幕、音乐、插片或转场。保留实际平台要求的标记。
- Codex 负责语义分镜、素材登记、剪辑计划与验收；本地 Hyperframes 执行字幕、插片、镜头和混音，直接导出 MP4。

顺序固定的是配音→口型、实际音频→对齐、实际素材→最终时间轴。视觉设计、插片准备可提前进行。字幕样式和效果数量依据用户要求，不以更换工具代替设计。

## 执行入口

`DH` 见 SKILL.md。新 brief 使用 `"postproduction":{"mode":"independent"}`。`run` 完成声像和字幕后返回 `needs_edit_plan`；这是 Codex 的下一步，不让用户填写 JSON。

1. 读取 `captions.json`、实际音视频和用户要求；复用合格声像，不改变原任务收费记录。
2. 用 `DH add-media JOB --file FILE --kind video|image|audio --source SOURCE --rights RIGHTS` 登记本地插片或音效。ID 来自命令返回，不能猜测；素材须有相应使用权。
3. 参考 `examples/edit-plan.json` 编写计划，执行 `DH edit-build JOB --plan FILE --name v1`。新的修改用新修订名，保留原版。
4. `DH edit-render JOB v1` 创建工程、检查并渲染；`DH edit-verify JOB v1` 完整解码并抽帧。已有 storyboard 与自定义 HTML 路径继续可用。
5. 按 production.md 检查真实画面和音轨，执行 `DH edit-review JOB v1 --file REVIEW`，交付 MP4、SRT 和必要素材目录。仅需要 ZIP 时执行 `DH edit-bundle JOB v1`。

复杂 Hyperframes 设计可在未渲染的修订里修改 `project/`，再 `DH edit-seal JOB v1` 和 `DH edit-render JOB v1`。已有成片或手改工程保留，新改动另建修订。源码可以修改；已渲染的视频像素不能拆成独立的人物动作，不承诺任意桌面软件工程转换。

## 计划格式

顶层：`schema: digital-human-edit/v1`，可选 ranges、presenter、captions、overlays、audio。未知字段拒绝；不支持的效果不能静默丢弃。

- `ranges` 是数字人源素材上的 start/end 秒数，可按指定顺序重排，可重复取片段。省略则保留全部。speed 默认 1；改变时人物视频、声音和字幕同步映射。reason 记录删留原因，visual 可为该段设置镜头。数字人表达已自然时不机械加速或清除全部气口。
- 剪口不能穿过当前字幕的发音区间。先用真实音频找句间边界；需要词级精剪时先取得并核实更细的对齐，不删除保护范围绕过检查。
- `captions.style` 控制字号、颜色、位置与基础运动；`replacements` 的键是原字幕序号字符串，例如 `"2":"核实后的专有名词"`。它不修改配音；原稿观点不擅自更换。
- `overlays` 使用最终成片时间：id、kind（video/image/text）、asset 或 text、start、duration；视频可设 source_start/speed。插片默认静音，旁白连续。visual 支持 fit=contain/cover，x/y/scale/rotation/opacity 和线性 keyframes。正 x 向右，正 y 向上，x/y 单位为半画幅；scale=1 表示按画幅适配。circle 蒙版由本地渲染支持。
- 关键帧例：`"keyframes":{"scale":[{"time":0,"value":1},{"time":3,"value":1.05}]}`。time 是片段内秒数，第一点必须为 0。片段长度变化后同步调整关键帧。
- `audio` 为配乐/音效：asset、start、duration、source_start、speed、volume、fade_in、fade_out。默认音量仅是起点，必须根据实际混音检查。需要人声压低配乐时可拆为相邻音乐片段并分别设音量，保护音频连续性。
- 默认轨道：人物 0、插片 1–9、人声 10、音乐/音效 20–99、字幕 100、标题 110–999。同轨不能重叠，叠画用不同轨道。内部时间以整数微秒保存，实际渲染仍由帧率取样；不是微秒精度画面承诺。

## 插片与视觉质量

先回答每个镜头帮助观众理解什么。例如“两个孩子正在写作业”可切入一段普通住宅中两名孩子学习的中景，声音和字幕继续，论点结束后回到数字人。不给每句话硬塞素材，不以快速闪切掩盖人物缺陷。

生成时描述具体人物数量、场景、动作、机位和光线。优先检查手笔接触、动作连续性、人物数量与画幅裁切；照片推近不冒充真实视频。新视频供应商须有相应授权与有限预算；这个版本接受其本地结果，不声称已经内置所有视频生成 API。生成画面记录为示意素材。

字幕先保证读得清、断句自然、避开脸与平台边栏，再使用少量强调。复杂动画按用户风格选择，不默认逐字弹跳、频繁缩放或全片高饱和。按旁白、环境声、音乐、强调音效的实际作用混音。

## 出镜覆盖与长片恢复

生活实拍与图解小素材分开管理，按 [stock-search.md](stock-search.md) 检索和裁切。圆形人物的覆盖、同台词口型映射和字幕避让按 [presenter-coverage.md](presenter-coverage.md) 执行；具体头部裁切依素材确定。长片独立导出及结果登记按 [render-recovery.md](render-recovery.md) 执行。

升级不删除用户旧工作区中的编辑器产物。新素材包只整理当前独立流程需要的文件；旧扩展工程需单独保留，不能宣称它已被自动迁移或包含进新包。
