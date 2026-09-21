# 全数字人的独立后期（v0.3）

目标始终是用户的数字人。用户的训练视频用于创建/校准身份，不擅自改为真人实拍出镜方案。已有数字人视频可以导入后继续剪辑，无需重新生成。

## 职责和工具选择

- MiniMax：已认可音色的配音。先把表达、停顿和读音做好，再生成口型。
- HeyGen：干净的数字人口播，保留平台要求的标记；不要求它同时加字幕、音乐、插片、镜头转场。使用用户本人 avatar 与已确认 audio 的专用接口，不自动改用 Video Agent 代写整片。接口没有某个开关时不能捏造参数。
- Codex：语义分镜、剪辑判断、素材登记、调用与验收。分离制作便于精修，不代表人物自然度自动提高。
- 后期默认用本地 Hyperframes 直接出片。只有用户明确说“使用剪映自动剪辑”或等价地选择剪映执行时，才操作剪映；“自动剪辑”“效果丰富”“可编辑”本身不触发它。仅要求剪映工程时导出草稿，不自动打开应用执行。两条路径共用剪辑时间轴，无需串行经过两套工具。

流程固定的是依赖：配音确定后口型；真实声音后对齐；实际素材到齐后最终时间轴。视觉设计、插片准备可提前进行。剪辑软件、字幕样式和效果数量不写死。

## 可执行入口

`DH` 见 SKILL.md。新制作的 brief 使用 `"postproduction":{"mode":"independent","editor":"auto"}`；editor 是 Codex 的路由偏好，可为 auto/hyperframes/jianying/both；auto 默认 hyperframes，jianying/both 只在用户明确选择对应交付时使用。`run` 完成声像和字幕后返回 `needs_edit_plan`。下面的 JSON 和命令由 Codex 编写与执行，不让用户手工操作。

1. 读取 `captions.json`、实际音视频和用户要求。旧任务也能直接进入，不改变原 job 状态或收费记录。
2. 需要视频插片、配图、音乐/音效时，先 `DH add-media JOB --file FILE --kind video|image|audio --source SOURCE --rights RIGHTS`。只接受本地文件；素材 ID 来自返回值，不能猜测。本人主画面继续用已登记 avatar，插片可用有权使用的现成素材或已获准工具生成的文件。
3. 参考仓库 `examples/edit-plan.json`。创建计划后执行 `DH edit-build JOB --plan FILE --name v1`，生成 `jobs/JOB/edits/v1` 的独立修订。新的修改用 v2/v3，不覆盖旧版本。收费声像完全复用。
4. 本地成片：`DH edit-render JOB v1` 会创建 Hyperframes 工程、检查并渲染；`DH edit-verify JOB v1` 全解码并抽帧。图解/复杂排版也可选原有 storyboard + Hyperframes 路径；不为剪映交付静默把效果压平成视频。
5. 用户明确要求剪映工程时：`DH edit-export JOB v1` 创建 `exports/jianying`，含原生文字、多轨媒体和可重定位计划。它不注册剪映首页、不调用内部引擎、不自动导出 MP4，不能把返回的 `native_app_verified:false` 当成通过。
6. 不需要剪映时跳过第 5 步，不为“以后可能要用”预先复制媒体或生成工程。保留标准素材、SRT 与时间轴即可按需导出。视听检查后，按 production.md 的真实证据要求执行 `DH edit-review JOB v1 --file REVIEW`，默认交付已验收 MP4、SRT 与必要素材目录。仅用户需要 ZIP 时执行 `DH edit-bundle JOB v1`；ZIP 含已经创建的剪映交接包（如有）。后补剪映工程应使用新修订，不能声称旧 ZIP 自动包含它。

若选用复杂 Hyperframes 设计，可在尚未渲染/导出剪映的修订内修改 `project/`，再 `DH edit-seal JOB v1`、`DH edit-render JOB v1`。seal 会标记自定义 HTML；这个修订不能再从旧时间轴导出剪映，避免两个交付的实际内容不一致。需要原生工程时在另一修订用计划表达可映射效果。

## 计划格式

顶层：`schema: digital-human-edit/v1`，可选 ranges、presenter、captions、overlays、audio。未知字段拒绝；不支持的效果不能静默丢弃。

- `ranges` 是数字人源素材上的 start/end 秒数，可按指定顺序重排，可重复取片段。省略则保留全部。speed 默认 1；改变时人物视频、声音和字幕同步映射。reason 记录删留原因，visual 可为该段设置镜头。数字人表达已自然时不机械加速或清除全部气口。
- 剪口不能穿过当前字幕的发音区间。先用真实音频找句间边界；需要词级精剪时先取得并核实更细的对齐，不删除保护范围绕过检查。
- `captions.style` 控制字号、颜色、位置与基础运动；`replacements` 的键是原字幕序号字符串，例如 `"2":"核实后的专有名词"`。它不修改配音；原稿观点不擅自更换。
- `overlays` 使用最终成片时间：id、kind（video/image/text）、asset 或 text、start、duration；视频可设 source_start/speed。插片默认静音，旁白连续。visual 支持 fit=contain/cover，x/y/scale/rotation/opacity 和线性 keyframes。正 x 向右，正 y 向上，x/y 单位为半画幅；scale=1 表示按画幅适配。circle 蒙版当前仅本地路径支持。
- 关键帧例：`"keyframes":{"scale":[{"time":0,"value":1},{"time":3,"value":1.05}]}`。time 是片段内秒数，第一点必须为 0。片段长度变化后同步调整关键帧。
- `audio` 为配乐/音效：asset、start、duration、source_start、speed、volume、fade_in、fade_out。默认音量仅是起点，必须根据实际混音检查。需要人声压低配乐时可拆为相邻音乐片段并分别设音量，保护音频连续性。
- 默认轨道：人物 0、插片 1–9、人声 10、音乐/音效 20–99、字幕 100、标题 110–999。同轨不能重叠，叠画用不同轨道。内部时间以整数微秒保存，实际渲染仍由帧率取样；不是微秒精度画面承诺。

## 插片与视觉质量

先回答每个镜头帮助观众理解什么。例如“两个孩子正在写作业”可切入一段普通住宅中两名孩子学习的中景，声音和字幕继续，论点结束后回到数字人。不给每句话硬塞素材，不以快速闪切掩盖人物缺陷。

生成时描述具体人物数量、场景、动作、机位和光线。优先检查手笔接触、动作连续性、人物数量与画幅裁切；照片推近不冒充真实视频。新视频供应商须有相应授权与有限预算；这个版本接受其本地结果，不声称已经内置所有视频生成 API。生成画面记录为示意素材。

字幕先保证读得清、断句自然、避开脸与平台边栏，再使用少量强调。复杂动画按用户风格选择，不默认逐字弹跳、频繁缩放或全片高饱和。按旁白、环境声、音乐、强调音效的实际作用混音。

## 剪映可编辑性的边界

适配采用 MIT 的 Jianying Local MCP 固定提交中的两个纯序列化模块，来源见 NOTICE。没有复制参考仓库 jianying-headless 的受限实现，没有随代码附带编辑器、字体缓存、效果资源或账号信息。

首次使用目标 Mac/剪映版本时，用独立短工程实测：打开、改一句字幕、替换插片、单独调整配乐、保存退出、冷重开、导出。必要时由 Codex 通过可用的电脑控制工具完成 UI 操作；无法完成时只暂停原生验收，本地剪辑仍可继续。不要向正在运行的剪映草稿目录盲写，不降级编辑器或放宽保护来假装兼容。当前生成的是实验性原生交接格式，不能承诺任意版本自动导入。

换电脑后使用 `DH relink-draft --source <解包的jianying目录> --out <新目录>` 重建本地路径，原包保留。手工修改过的草稿不允许从旧计划覆盖；它成为独立版本，继续通过剪映编辑。没有自动双向同步。

原生字幕能改字、时间和样式；人物/插片仍是视频像素，不能拆出其内部人物动作。字体、裁切、动效表现须看原生导出，不宣称与 Hyperframes 逐像素一致。复杂 HTML/GSAP 动画无法通用转换：选择原生可表达的设计，或经用户接受后输出独立渲染元素并标明内部不可编辑。

## v0.4 补充

生活实拍与图解小素材分开管理，检索与裁切按 [stock-search.md](stock-search.md)。全程圆形人物的覆盖、声源映射和字幕避让按 [presenter-coverage.md](presenter-coverage.md)，不能仅将旧人物任意片段循环。旧 mask:circle 在非正方形画布上已修为真圆；具体头部裁切需要素材检查。长片独立导出及结果登记按 [render-recovery.md](render-recovery.md)。原生剪映尚不支持已验证圆形蒙版转换，继续明确报错，不扁平化冒充可编辑。
