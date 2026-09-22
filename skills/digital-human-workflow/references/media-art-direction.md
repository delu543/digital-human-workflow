# 素材选择、GPT生图与图生图

按镜头用途决定工具，不按“AI项目”决定所有东西都生成。选项来自用户要求、素材权利、画幅、时长和预算。生成装饰素材与真实生活插片是不同类别，分别记录。

| 镜头用途 | 优先路线 | 需检查 |
|---|---|---|
| 用户指定真实人物活动、日常情境 | Pexels/Mixkit等许可实拍 | 动作/关系/环境相符；目标画幅保住互动；完整连续段可用 |
| 纸张、光影、材料、背景、图解中的小资产 | 已授权素材或GPT生图 | 品牌调性、留白、材质、分辨率、透明边缘、后期文字区 |
| 已有产品/品牌/人物参考需要局部变化 | GPT图生图/编辑 | 哪张是编辑对象，哪些是身份/风格/构图参考；不变项与改动边界 |
| 必须连续发生、实拍找不到的特定动作 | 已授权视频生成工具 | 实际模型/费用、动作连续、物件接触、身份与机位；不拿静图推近替代 |
| 标志、字幕、UI或真实数据 | 授权原文件与可编辑排版 | 文字正确、品牌许可、数据来源；不让生图模型杜撰事实 |

## 实拍的广告片筛选

延续 [实拍检索](stock-search.md) 的动作搜索方法。横片优先landscape，竖片优先portrait；原生比例不合但可以保留全部关键对象时才裁切。人物、双手、产品、互动双方应落在最终安全区内。

先搜具体动作，再收窄外观/环境与镜头：`team reviewing printed document`、`person editing video workstation`、`teacher explaining at classroom screen`、`hands writing notebook close up`。它们是查询语法，不指定所有用户都用相同演员或地区。

Pexels可用站内Videos、搜索引擎 `site:pexels.com/video/ <动作>`，有用户API授权才调用官方视频搜索并选择orientation/size。Mixkit按类别/关键词进入作品页，核对该条是Free还是Restricted；不把整个网站都算作商用许可。记录实际query、页面、作者、许可日期、源片入出点和拒绝原因。

每个关键镜头先看少量候选的完整采用段；只下载优选项。内容不符就有方向地改词或换镜头设计，不为填满画面拿漂亮但无关的库存片。电影和台词搜索只能帮助定位，公开观看不是广告使用许可。

## GPT图像工具的调用顺序

1. 先确定生成还是编辑、交付画幅、主体/文字/圆框安全区和必需分层。能复用合格资产就复用。场景需真实视频时，不把它改成大照片。
2. 环境有OpenAI内置生图工具时优先用实际工具；不要求额外API key。需编辑本地参考图，先查看它，再按工具当前schema传入参考路径或最近图像；两种引用方式不能混用，不虚构工具参数。
3. 环境没有工具时说明缺失，使用已授权替代路径。用户明确选择API/CLI时才使用其账号和预算，先核对当天官方模型与edit参数。内置工具未披露模型版本时如实记录“未披露”，不能用提示词声称选择了指定模型。
4. 先生成一份适合用途的资产。选择精度、材质和构图，而非一律堆“8K、电影级、完美皮肤”。多参考输入逐张注明角色，避免把风格参考中的人误当新身份。
5. 检查实际图像：主体、脸/手/产品轮廓、透视、光向、材质、文字区、透明通道。需要修正时只改具体问题；保持用户要求的不变项，不借图生图改掉人脸或品牌。
6. 选定后保存到当前用户工程，登记生成工具、时间、实际披露的模型、提示词、参考角色、许可/同意与文件哈希。不要让引用只指向聊天临时文件，也不把私人参考图发布到公共仓库。
7. 图像是后期材料：标题、字幕、准确标签留在HTML/图形层，使用轻微光影或尺度运动，保持阅读停留。生图不是动画模型，也不是把完整PPT截成图片后移动。

## 可填充提示词

装饰底图：

> Generate a [target aspect ratio] photographic material plate for [brand tone / scene purpose]. Show [specific surface and restrained lighting]. Keep [planned text area] quiet, low contrast and uncluttered. Match the palette and light direction of [approved reference]. No people, lettering, logos or fabricated interface. This will sit behind editable typography and real video, not replace the footage.

局部图生图：

> Edit image 1 as the target. Use image 2 only as [material / lighting / composition] reference. Change only [requested region/elements]. Preserve [authorized identity, product shape, approved features, camera perspective]. Match contact shadows and illumination. Reserve [specified safe areas] for separately typeset captions. Do not add unrelated subjects or brand text.

这些是框架，括号必须由当次真实需求替换。没有背景修改需求时不新造场景；人物图片改变后，旧口型校准不能自动当作新形象已经通过。

## 模型、成本和状态

“最好”需要按用途核对：精确编辑、自然照片、透明资产、连续动作可能需要不同能力。保存官方来源日期与实际工具回执；不自动升级已有认可声音或把新模型价格写死为所有用户默认。候选数、总预算与不确定收费结果纳入同一任务账本；本地排版失败不重复付图像/视频费用。

本仓库提供Codex编排流程与素材登记，不内置所有生成供应商的通用API适配器。外部调用遵守实际工具权限；没有工具、权利或预算时暂停该素材步骤，其他独立工作继续。
