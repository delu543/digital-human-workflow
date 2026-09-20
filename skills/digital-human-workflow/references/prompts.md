# 提示词与调用责任（v0.2）

以下是可填充的通用模板，不是已验收结果。变量来自该用户授权素材与当次要求，全部保存在私人工作区。不要把作者本人形象或上次任务的文案复制给新人。先看真实素材，再选模板；没有合格源素材时提示词不能创造其真实动作信息。

## A. Codex 诊断与导演任务（不发给视频模型）

> 目标：自然、可信、像该用户真实拍摄的口播。按原片、静态形象、声音、裸数字人、包装成片顺序检查。每个问题记录证据位置、已确认事实、待验证假设、最小改动和验证方式。先找最早出现的缺陷。保留原稿立场和已认可的声音，不通过增加生成次数代替诊断。停止条件是底片通过基线检查或达到本轮授权边界。

把“某频道的感觉”译成可执行的设计语言：叙事节奏、现场感、证据镜头、图解方式、色彩和声音关系；不要只把频道名塞进生成提示词。可借鉴制作方法，不复制其商标、专属素材或暗示代言。

## B. 静态场景 / look 提示词（图像或官方创建 look 能力）

仅在已有授权且需要新场景时使用；先出静态图并检查，通过后才付视频费用。以实际参考的姿势与照明为准替换括号：

> Use the supplied authorized reference as the identity and pose reference. Preserve the person's facial proportions, glasses, hairstyle, age, clothing, and [seated/standing] posture. Keep the camera at [observed eye level and angle]. Place the scene in [concrete ordinary room and a few plausible objects]. Match the environment light to the observed [direction and softness] on the face, with consistent contact shadows at [visible contact surface]. Keep believable room proportions, ordinary material texture, natural skin detail and restrained depth of field. The result should look like a candid frame from a real interview recorded in this room.

专注所需改变。例如讲堂采用与原片相近的座位、桌沿和机位，背景是普通黑板/投影幕与少量真实陈设。不要同时把坐着的人改成站立、换衣、换强光、换镜头。确实需要站姿讲课时先取得匹配姿态参考，再设计该场景。

避免默认添加：perfect skin、flawless face、ultra cinematic、dramatic rim light、epic、extreme bokeh、8K masterpiece。它们不是禁词表，而是通常与“普通相机真实记录”目标冲突的美化方向。输入脸太小/眼睛被反光盖住时不靠长负面提示词修复。

## C. MiniMax 口语表达（先给 Codex，非 API 的虚构 prompt 字段）

> 保持原稿观点、事实与称呼。听起来是在向一个具体的人解释，而不是朗诵广告。按意思自然连读，关键转折处停一下；避免每个短句相同停顿。只调整已获许可的口语表达和标点，不添加无意义的语气词。标出确需检查的读音和数字；以实际试听确定效果。

调用只使用官方参数：用户认可的 model/voice_id/speed，默认不传 emotion。MiniMax T2A没有本工作流自造的 `delivery_prompt` 字段。默认一次合成；两版比较必须在用户授权的有限候选数和累计预算内。保留原稿、实际送出的文字、参数和回执，记下选择理由。已有偏好优先复用。

## D. HeyGen 动作提示词（只管动作）

Avatar V 基线优先 **null / 不发送**。确有必要时只写一个具体小动作或一项表情，通常1–2个短分句；以下任选其一并按参考能做的动作调整：

- `A small nod at the main point.`
- `One restrained hand gesture while explaining; hands return to rest.`
- `A relaxed, attentive expression.`

不是把三句一起用。不要编排每隔几秒眨眼/转头，不要求持续紧盯镜头，不混入背景、照明、镜头推拉、走路换站姿、口播台词。不堆“眼神+眉毛+头+肩+手+呼吸”动作清单。场景留给 B，剪辑留给 E。没有指定参考的 V 会自参考；指定参考时检查同组与姿势/机位匹配。API/MCP 的实际支持以当时官方 schema 为准，不静默忽略不支持字段。

## E. Hyperframes 剪辑 brief（本地导演层）

> 用一条真实感通过的口播为主线。先听台词，以论点和语气确定镜头段落。保留说话节奏与声画同步。选择能解释当句内容的证据图/图解/B-roll；字幕用简洁层级、自然断句、有限关键词强调。动效短而有目的，不让每个字跳动。每个转场说明它服务的语义；同机位数字裁切明确视为裁切。自然肤色、统一画面质感，避免把背景处理成无纹理的棚景。音乐与环境声轻量混合，以人声为准，不掩盖停顿缺陷。

约30秒可用“人物开场 → 证据/图解 → 回到人物结论”的结构，段落长度服从真实音轨，不把这个示例当固定秒表。五分钟片按论证展开，不机械复制短片节奏。生成分镜时先遵循当前 Hyperframes skill/固定版本接口，记录实际素材权利。只改包装时复用已经验收的声像，避免重付费。

## 提交前快速自查

- 这句提示词到底控制图像、声音、动作还是剪辑？送到对应工具了吗？
- 姿势、机位、光线和参考相容吗？是否一次改了太多变量？
- 所选模型/字段/价格在当前账户核对过吗？实际配音已确认了吗？
- 静态图不通过，是否却准备继续付视频费？
- 验收证据来自真实视听还是“模型高端/文件高清”的推断？
