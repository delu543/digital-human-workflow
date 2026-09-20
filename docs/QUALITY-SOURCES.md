# 真人感方案的官方依据

核对日期：2026-09-20。采用的是官方协议和制作建议，没有复制第三方实现、引入新的模型依赖或绑定付费套餐。官方页面可能变化；账户实际 look 能力、工具 schema 和实时价格优先。

| 来源 | 本项目采用内容与边界 |
|---|---|
| [Avatar V 开发文档](https://developers.heygen.com/avatar-v) | 先查 supported_api_engines；动作参考需同组且满足同意要求；expressiveness 不用于 V |
| [Create Video schema](https://developers.heygen.com/reference/create-video) | 外部音频输入；顶层 motion_prompt，engine 内 reference_look_id；会员桥接同时核对实际 MCP schema |
| [Avatar V 制作建议](https://help.heygen.com/en/articles/14602997-how-to-get-the-best-results-with-avatar-v-in-heygen) | 核对动作源、主体大小、角度与表演信息；不同创建路线的时长要求分开看 |
| [动作提示词指南](https://help.heygen.com/en/articles/12805098-fine-tune-avatar-gestures-and-movements-with-custom-motion-prompts-avatar-iv-v) | 短而具体、动作和表情职责明确；文中 Avatar IV 分节限制不泛化给所有引擎 |
| [Avatar Voice FAQ](https://help.heygen.com/en/articles/15544929-avatar-voice-faq-troubleshooting-best-practices-and-credits) | 先处理音频与输入形象，避免靠复杂提示词修补源头 |
| [Digital Twin 拍摄建议](https://help.heygen.com/en/articles/8389138-digital-twin-video-avatar-filming-tips) | 稳定机位、清楚光线与自然表演；传统训练建议不当成所有 V 输入的硬限制 |
| [MiniMax T2A HTTP](https://platform.minimax.io/docs/api-reference/speech-t2a-http) | emotion 默认省略；fluent/whisper 的模型限制；只使用受支持的发音/停顿语法，不用自造字段 |

10–15秒自然基线、24小时能力记录有效期、240字符动作提示词上限、分层验收与单变量排查，是本工作流的工程策略。它们不是供应商质量保证。代码负责检查状态和证据记录；人像/声音的主观真实感仍由实际样片验收。
