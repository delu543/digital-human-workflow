# 最少人工配置

Codex 先完成仓库 `INSTALL_FOR_CODEX.md` 的本地安装和 `DH init`、`DH doctor`，再只收集确实缺失的输入。

1. **计费选择**：HeyGen 会员 MCP、付费 API、已生成视频导入，三者任选。核对当前账户的授权、可用形象和实际费用，不预设必须 Pro 或必须 API。完全无人值守优先说明 API 的可恢复异步路径；尊重用户最终选择。
2. **MiniMax 站点与密钥**：国际站 https://platform.minimax.io/ ，国内站 https://platform.minimaxi.com/ 。语言是中文不决定密钥区域；按用户账户所在地选择。音色质量取决于模型和样本，不声称同模型国际站更好。用户在所选站点的 API Keys 页面创建密钥，在本地终端运行 `DH secrets minimax` 隐藏输入。Codex 不索取密钥正文。
3. **声音**：已有认可的 `voice_id` 就复用。没有时，用户提供有授权、清楚干净的 10 秒至 5 分钟录音（API 最大20MB），并授权上传目的地、克隆和试听费用上限。Codex 保存简短校准稿，brief 使用 `{"purpose":"calibration"}`，`DH prepare` 后执行 `DH clone-voice <id> --sample <录音或视频>`。程序会保存回执并执行一次用于激活的短合成。让用户听实际试听，认可后再写入长期 `voice_id` 和 `approvals.voice=true`。克隆与试听成本均计入预算。
4. **形象**：用户进入 https://app.heygen.com/avatar/my-avatars 创建本人形象并完成平台同意流程。Codex 可用只读 `list_avatars` / looks 接口读取。主页 URL 中的集合 ID 未必是生成所需 look ID；从账户实际可用 look 中选择并验证。不能替换为陌生人样片。
5. **HeyGen 连接**：会员用官方远程 MCP `https://mcp.heygen.com/mcp/v1/`，用户完成 OAuth 登录。按当前 Codex 的 MCP 设置添加，CLI 可先查 `codex mcp --help`，再 `codex mcp add heygen --url https://mcp.heygen.com/mcp/v1/` 和 `codex mcp login heygen`。已有可用连接就复用。API 路径在 HeyGen 账户创建 API key，用户本地运行 `DH secrets heygen`。本仓库不重新实现 OAuth，也不要求安装非官方 HeyGen 包。
6. **一次校准**：按 [真人感流程](realism.md) 核对来源、静态形象、动作参考、当前能力与价格，保存质量计划。先试听最终配音，再生成有限时长短样片；用户实际认可后 `accept-baseline` 保存可复用模板，并记录 `approvals.voice/identity/style=true`。旧全局开关不能替代具体模板基线；已认可样片可导入登记，无需为了升级重付费。以后相同模板和授权不重复询问设置。

使用 `DH configure --file <工作区内patch.json>` 设置配置；完整字段见仓库 `config/profile.example.json`。`authorization.generation`、`voice_clone`、`destinations` 和预算必须对应真实授权，不因拿到密钥自动设为允许。`destinations` 为 `minimax_international` 或 `minimax_china`，以及 `heygen`；模型/音色/路径变更后准备新任务。价格写到 `rates`，`verified_at` 使用核实日期；空值是未配置，不是免费。

不要替用户购买会员；不要把样片、录音、脚本、个人配置、缓存或日志提交到代码仓库。完成后交付简短说明：下次在当前 Codex 输入文案、风格要求即可启动；MCP 中途等待由真实工具权限决定。

首次只收集真正缺失的声像素材与文案；从已有视频能选出合格照片/音频时由 Codex 处理，不重复要求另拍。人物外观、说话风格和出镜方式由当前用户决定；详细制作顺序见 [director-runbook.md](director-runbook.md)。照片本身无法包含完整声音/动作信息，缺这类素材时提出具体最小补充要求。
