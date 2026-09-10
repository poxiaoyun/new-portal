"""Build the 晓石云 demo page from the reference-rendered DOM.

Structure and class names are taken verbatim from the reference markup so the
compiled stylesheet applies 1:1. Every text node, link and image is then
replaced with 成都破晓石科技 (poxiaoshi.cn) content.
"""
import re, html, os

SRC = 'dom.html'
OUT = '../xiaoshi-cloud/index.html'
MISS = []

body = open(SRC, encoding='utf-8').read()
body = body[body.find('<body') + 6:]
body = body[:body.rfind('</body>')]
body = re.sub(r'<script[\s\S]*?</script>', '', body)
body = re.sub(r'<link rel="preload"[^>]*>', '', body)

# --------------------------------------------------------------- text mapping
T = {
 # announcement / nav
 'New:': '新品:',
 'Overview': '首页',
 'Product': '产品',
 'LLMs': '解决方案',
 'Pricing': '价格与服务',
 'Docs': '文档中心',
 'Company': '关于我们',
 'About us': '公司简介',
 'Our Blog': '公司动态',
 'Affiliates': '开源项目',
 'Careers': '加入我们',
 'Contact': '联系我们',
 'Talk to Sales': '联系销售',
 'Open Console': '预约演示',
 'Read the API': '查看文档',
 'Choose a platform_': '选择产品_',
 'PipeLLM': '晓石云',
 # hero
 'Enterprise AI control plane': '云原生 · 混合云 · AI 智算',
 'One control plane for': '智算为中心的',
 'production agents.': 'AI 原生云内核',
 'One endpoint': '多云纳管',
 'Policy routing': '异构调度',
 'Managed tools': '模型资产',
 # hero terminals
 '~/lens': '~/moha',
 '$ pipellm lens tail --agent checkout': '$ xiaoshi moha push model --encrypt',
 '✔ tool calls captured': '✔ 资产已加密入库',
 '→ replay ready': '→ 版本可追溯',
 '~/loop': '~/rune',
 '$ pipellm loop run agent --production': '$ xiaoshi rune job submit --gpu 8',
 '$ pipellm loop run agent --env production': '$ xiaoshi rune job submit --gpu 8',
 '✔ managed tools attached': '✔ 训练任务已调度',
 '→ Lens trace linked to Relay': '→ 推理服务弹性伸缩',
 '~/relay': '~/xmcp',
 '$ pipellm relay route --model approved': '$ xiaoshi xmcp attach cluster --cloud huawei',
 '✔ policy resolved': '✔ 多云已纳管',
 '→ response streamed': '→ 配额与计费就绪',
 # three products
 'Relay · Loop · Lens': 'Rune · XMCP · Moha',
 'Three products. One control plane.': '三大核心产品，一个智算底座。',
 'Loop': 'Rune',
 'Relay': 'XMCP',
 'Lens': 'Moha',
 '~/pipellm/control-plane.mjs': '~/xiaoshi/control-plane.yaml',
 'request active': '任务运行中',
 '01 / Loop · Agent Runtime': '01 / Rune · AI 训推平台',
 'Run the agent.': '跑通每一次训练。',
 'Session state, execution, and agent context stay here.': '训练任务、推理服务与算力配额在这里统一编排。',
 'Session': '任务',
 'sess_checkout_42': 'rune-job-2048',
 'Tool lease': 'GPU 配额',
 'websearch attached': '8 × A800 / pool-cn-southwest',
 'State': '状态',
 'durable': '运行中',
 'Open Loop': '进入 Rune',
 'Active product': '当前产品',
 'Model Gateway': '多云纳管',
 'Open\n              Relay': '进入 XMCP',
 'POST': 'POST',
 'Relay\n        </span>': 'XMCP\n        </span>',
 'OpenAI': 'Kubernetes',
 'Anthropic': 'vCenter',
 'Gemini': 'OpenStack',
 '03 / Lens · Observability &amp; Audit': '03 / Moha · AI 资产仓库',
 'Record the decision.': '沉淀每一份资产。',
 'Route, approvals, and tool activity become traceable evidence.':
     '模型、数据集与访问记录都成为可追溯的资产。',
 'Trace': '资产',
 'tr_01H9K6': 'moha/model-llama-3.1',
 'Runs': '版本',
 '4 completed': '12 个版本',
 'Approval': '加密',
 'policy passed': 'AES-256 已启用',
 'Open Lens': '进入 Moha',
 'Managed tools': '统一纳管',
 'Governed by Relay, attached inside Loop, and recorded by Lens.':
     '由 XMCP 接入，在 Rune 中调度，并由 Moha 归档。',
 'websearch.attach': 'multicloud.attach',
 'Current result': '当前结果',
 'approved model selected': '训练任务已调度',
 'Translates protocols and routes requests to approved models.':
     '统一接入多云算力，并把任务调度到最优资源池。',
 # gateway section
 'Relay · Model Gateway': 'XMCP · 多云纳管',
 'Keep the SDK. Govern every model call.': '不改现有体系，纳管每一朵云。',
 'Open Relay': '进入 XMCP',
 'Relay control path': 'XMCP 纳管路径',
 'Translate': '接入',
 'Keep the client contract your application already uses.':
     '自动识别并接入 Kubernetes、vCenter、OpenStack、华为云等平台。',
 'Enforce': '安全',
 'Apply approved models, provider access, and Loop policy.':
     '基于零信任架构与 Mesh 网络，保障跨云通信安全可靠。',
 'Route': '调度',
 'Select the right approved provider for each model call.': '按业务需求与资源状况智能优化资源分配。',
 'SDK-compatible request': '多云统一接入',
 'Keep the client. Change the layer underneath.': '保留原有云平台，替换下方的连接层。',
 'OpenAI SDK': 'Kubernetes',
 'Anthropic SDK': 'vCenter',
 'Google Gen AI SDK': 'OpenStack',
 'LangChain': '华为云',
 'Relay decision': 'XMCP 决策',
 'Protocol': '平台',
 'Policy': '策略',
 'approved': '已授权',
 'provider selected': '已选择最优节点',
 # runtime section
 'Loop · Agent Runtime': 'Rune · AI 训推平台',
 'One stateful loop for production agents.': '一体化的训推流水线。',
 'View the platform docs': '查看产品文档',
 '~/loop/agent-session.mjs': '~/rune/training-job.yaml',
 'session live': '任务运行中',
 'Loop SDK · Agent Runtime': 'RUNE · AI 训推一体',
 'Run the agent. Keep the context.': '提交任务，全程可控。',
 'Node.js': 'Python',
 'Python': 'YAML',
 'cURL': 'cURL',
 'import': 'import',
 'loop': 'rune',
 'from': 'from',
 'const': 'const',
 'run': 'submit',
 'await': 'await',
 'agent': 'job',
 '"support-triage"': '"llm-finetune-7b"',
 'session': 'pool',
 'tools': 'dataset',
 '"websearch"': '"moha://datasets/corpus-v3"',
 '"@pipellm/loop"': '"@xiaoshi/rune"',
 'policy applied before execution': '执行前已完成策略校验',
 'trace opens with the run': '训练与推理全程留痕',
 'state retained': '配额已保留',
 'policy allowed': '已授权访问',
 'Operator view': '运维视图',
 'approval trail': '调度记录',
 'trace ready': '实时可查',
 # audit section
 'Lens · Observability &amp; Audit': 'Moha · AI 资产仓库',
 'Decisions you can replay.': '每一份资产都可追溯。',
 'See what happened, why it was allowed, and what evidence stays with the outcome.':
     '看清谁在什么时候访问了什么、为什么被允许，以及留下了哪些证据。',
 '~/lens/tr_01H9K6.json': '~/moha/assets.json',
 '4 events': '4 条记录',
 'production': '生产环境',
 'Decision replay': '资产审计轨迹',
 'agent.run': 'moha.push',
 'checkout_42 started': 'model-llama-3.1 上传',
 'started': '已上传',
 'tool.websearch': 'encrypt.aes256',
 'context attached': '数据加密完成',
 'attached': '已加密',
 'approval.refund': 'access.grant',
 'review required': '跨租户授权复核',
 'model.response': 'rune.pull',
 'outcome recorded': '训练任务拉取',
 'recorded': '已记录',
 'Selected decision': '选中记录',
 'A policy gate asks for review.': '一次越权访问被策略拦截。',
 'The requested refund exceeded the autonomous limit, so the action paused for an operator.':
     '该请求超出了所属租户的访问范围，操作被暂停并交由管理员复核。',
 'Trigger': '触发条件',
 'action: refund.create ($286.00)': 'tenant: edu-university-a',
 'refunds over $200 require approval': '跨租户读取需管理员授权',
 'Outcome': '结果',
 'approved by ops': '已由管理员批准',
 'Evidence bundle': '证据包',
 'Everything needed to explain this decision stays connected to the trace.':
     '所有能解释这次操作的证据，都与这条记录绑定在一起。',
 'approver: m.hsu': 'approver: ma.qing',
 'policy: refund.threshold': 'policy: tenant.access.scope',
 'decision: approved': 'decision: approved',
 'complete and exportable': '完整且可导出',
 'Trace integrity': '记录完整性',
 'context, policy, and outcome linked': '上下文、策略与结果已关联',
 'Replay any decision without reconstructing the run.': '无需重放任务，即可回看任意一次访问。',
 # pricing
 'Modular pricing_': '灵活的计价方式_',
 'Pricing that follows the layer you use.': '按使用的产品线计价。',
 'View all pricing': '查看完整报价',
 'Usage by model': '按算力与任务量',
 'Model gateway rates through one API.': '以统一的算力单价支撑训练与推理。',
 'Base + usage': '订阅 + 节点',
 'Agent runtime capacity and managed runs.': '按纳管集群与节点规模订阅授权。',
 'Observability retention and recorded events.': '按资产仓库容量与存储时长计费。',
 'Build Agent\n            Service': '交付与实施\n            服务',
 'Custom': '定制报价',
 'Scoped development and production delivery.': '按项目范围提供开发与生产交付。',
 'See commercial details': '查看商务条款',
 # tools
 'Give agents live context.': '一个入口，接入所有大模型。',
 'Explore WebSearch': '了解 AI Router',
 'WebSearch API': 'AI Router API',
 'Explore all four routes': '查看四种接入方式',
 'API keys and usage': '密钥与用量',
 'Deep': '对话',
 'Simple': '向量',
 'Reader': '重排',
 'News': '多模态',
 'search': 'search',
 'const response = await fetch(': 'const response = await fetch(',
 '{ query: "agent updates" }': '{ model: "deepseek-v3", messages }',
 # blog
 'Insights &amp; Resources': '公司动态',
 'Explore Our Blog': '查看全部动态',
 'Agent Memory Is the Next Bottleneck in AI Applications': '破晓石完成阿里云 PPU 适配',
 'Context Engineering for AI Agents: How to Stop Your AI from Forgetting': '破晓石与海光完成兼容性认证',
 'Why You Should Use a Unified LLM Gateway Instead of Multiple API Keys': '破晓石交付马基努油田云项目',
 'Read More': '阅读全文',
 'Browse Docs': '浏览文档',
 # faq
 'Frequently Asked Questions': '常见问题',
 'Answers evolve with the platform.': '答案会随产品迭代持续更新。',
 # cta
 'Ready to ship': '即刻开启您的',
 'production agents?': '云原生与 AI 之旅？',
 'Talk to Sales': '联系销售',
 'Work email address': '企业邮箱',
 # footer
 'Platform': '产品',
 'Documentation': '文档与资源',
 'Resources': '解决方案',
 'PIPELLM AI': '晓石云智算平台',
 'Models': 'KubeGems',
 'Getting Started': '快速开始',
 'API Reference': 'API 参考',
 'OpenAI Compatible': '私有化部署',
 'Anthropic Compatible': '离线安装',
 'Gemini Compatible': '版本变更',
 'Changelog': '最佳实践',
 'Blog': '混合云',
 'Status': '智算中心',
 'Security': '教育行业',
 'Privacy': '能源制造',
 'Terms': 'AI 应用',
 'All Systems Operational': '所有服务运行正常',
}

SENT = {
 'Relay connects every model, Loop runs every agent, and Lens explains every decision — without changing SDKs.':
   '专注云原生开源、混合云与 AI 智算平台，为企业提供覆盖容器云、混合云、智算云及 AI 能力的全栈解决方案。',
 'Relay governs model access, Loop runs stateful agents, and Lens turns every decision into an inspectable record.':
   'Rune 承载 AI 训推，XMCP 纳管多云资源，Moha 沉淀模型与数据资产，三者共享同一套权限、配额与可观测体系。',
 'Relay sits between your application and model providers. Keep familiar client calls, change the base URL, and let Relay translate protocols, apply policy, and route approved models.':
   'XMCP 位于您的业务与各类云平台之间。沿用原有集群与运维习惯，由 XMCP 统一接入、统一策略、统一计量，把多云真正用成一朵云。',
 'Keep the familiar OpenAI client while Relay reaches the approved model behind it.':
   '保留原有 Kubernetes 访问方式，由 XMCP 完成跨云连接与统一纳管。',
 'Managed tools, policy controls, approval trails, and operator visibility without turning the page into a wall of dashboard copy.':
   '覆盖模型开发、训练、推理与部署全流程，同时保持克制简洁的操作界面：算力配额、任务状态与调度记录一屏可见。',
 'One Loop call keeps execution, session state, and managed tools attached for the whole run.':
   '一次提交即可完成资源申请、训练、调优、推理与部署，算力配额与数据来源全程保持可见。',
 'Relay follows provider pricing. Loop and Lens combine a platform base with usage. Build Agent is a scoped professional service.':
   'XMCP 与 Moha 采用订阅制授权，Rune 按算力与任务量计费，交付与实施服务按项目范围报价。',
 'WebSearch API: $0.01 simple/reader, $0.08 deep/news per successful request.':
   'AI Router API：按调用量阶梯计费，企业版支持私有化部署与专属配额。',
 'Call WebSearch from Loop or your app. Relay governs access, and Lens keeps every tool invocation connected to the run.':
   '通过 AI Router 统一调用各家大模型与多模态能力；XMCP 负责通道治理，Moha 保留每一次调用的完整记录。',
 'Guides, implementation notes, and production patterns for teams building with AI.':
   '了解我们的最新进展、产品发布和行业洞察。',
 "Bigger context windows aren't the answer. The future of AI agents lies in smarter memory systems — semantic retrieval, relational linking, and temporal awareness. Here's why agent memory architecture matters more than raw context size.":
   '晓石云平台完成阿里云 PPU 算力适配，Rune 训推一体平台可直接调度国产加速卡资源，进一步降低企业 AI 基础设施的异构成本。',
 "AI agents lose track of goals during long tasks due to context rot. Learn how LangChain's Deep Agents SDK uses a three-layer compression strategy to manage context windows, and what this means for your AI stack.":
   '晓石云全线产品完成与海光处理器的兼容性认证，覆盖容器云、多云纳管与 AI 智算平台，为全信创场景提供稳定支撑。',
 'Managing multiple AI provider API keys is a growing pain for engineering teams. A unified LLM gateway eliminates key sprawl, simplifies SDK integration, and gives you the freedom to switch between models without changing a single line of code.':
   '面向中东能源行业交付云原生 SaaS 化服务，通过 XMCP 统一纳管多地域资源，以计量计费支撑跨境业务的精细化运营。',
 'New to PipeLLM? Build faster with the right developer tools.': '初次了解晓石云？从开发者文档快速上手。',
 'Start with quickstarts, SDK examples, and production workflow guides.': '快速开始、SDK 示例与生产环境落地指南一应俱全。',
 'Short answers for teams bringing agents into production.': '关于晓石云产品与交付的常见解答。',
 'Relay, Loop, and Lens in one production control plane.': '一个底座，贯穿多云纳管到 AI 训推全流程。',
 'Connect every model with Relay, run every agent in Loop, and explain every decision through Lens.':
   '从多云纳管到 AI 训推，从资产沉淀到应用落地，晓石云陪您走完全程。',
 'Model gateway for protocol translation and routing.': '现代化 AI 训推一体平台，覆盖模型开发、训练、推理与部署。',
 'Stateful agent runtime with managed tools.': '基于 Mesh 网络的多云纳管平台，实现多云互联与计量计费。',
 'Observability, replay, and audit for every decision.': '私有化 AI 模型与数据集仓库，支持加密存储与版本治理。',
 'Model gateway and routing.': '现代化 AI 训推一体平台。',
 'Stateful agent runtime.': '基于 Mesh 网络的多云纳管平台。',
 'Observability and audit.': '私有化 AI 资产仓库。',
 'How PipeLLM is built for production AI teams.': '以技术驱动成长，云原生与 AI 智算自主可控。',
 'Product notes, architecture, and developer guides.': '产品发布、行业洞察与客户实践。',
 'Partner with PipeLLM and share the platform.': 'KubeGems 等自研开源项目与社区生态。',
 'Build reliable agent infrastructure with us.': '和我们一起构建面向未来的 AI 原生基础设施。',
 'Talk to the PipeLLM team.': '与晓石云团队交流您的多云与 AI 智算需求。',
 'Building production AI.': '原生无界 · 破晓时刻。',
 '© 2026 PipeLLM.': '© 2026 成都破晓石科技有限公司 · 四川省成都市高新区银泰悦坊17号楼9层 · 蜀ICP备·备案号占位',
 'New: Opus 5 is now live on the PipeLLM Relay. Enjoy a limited-time 30% discount on DeepSeek v4 Pro!':
   'Rune 2.6 正式发布：训推一体流水线支持英伟达与国产 GPU 异构算力池，多租户配额与弹性伸缩同步上线。'
   '   ·   破晓石完成阿里云 PPU 适配，国产加速卡正式纳入 Rune 调度。',
 'Opus 5 is now live on the PipeLLM Relay. Enjoy a limited-time 30% discount on DeepSeek v4 Pro!':
   'Rune 2.6 正式发布：训推一体流水线支持英伟达与国产 GPU 异构算力池，多租户配额与弹性伸缩同步上线。'
   '   ·   破晓石完成阿里云 PPU 适配，国产加速卡正式纳入 Rune 调度。',
 'Trusted by startups, enterprises, and AI innovators worldwide.':
   '已服务能源、教育、制造与智算中心等行业的领先客户。',
 'Build Agent Service': '交付与实施服务',
}

FAQ = [
 ('What is PipeLLM built for?', '晓石云的产品矩阵覆盖哪些场景？',
  '晓石云覆盖云原生开源、混合云与 AI 智算平台。XMCP 负责多云纳管，Rune 提供 AI 训推一体化能力，Moha 沉淀模型与数据资产，AI Router 与 ChatBox 面向 AI 应用层。'),
 ('What makes PipeLLM different?', '晓石云与其他厂商的差异在哪里？',
  '我们以云原生为统一基座，自研 KubeGems 等开源项目，平台全栈采用 Golang，兼容国产服务器、操作系统与算力芯片，可完全私有化交付。'),
 ('Can we keep our existing SDKs?', '是否能对接我们现有的云平台与框架？',
  '支持。XMCP 可自动识别并接入 Kubernetes、vCenter、OpenStack、华为云等平台；Rune 兼容主流训练框架与 Transformer 生态，并提供集成 IDE 与桌面仿真环境。'),
 ('What does Relay control?', 'Rune 支持哪些 GPU 与调度方式？',
  '支持英伟达、华为昇腾等国产 GPU，兼容异构 GPU 资源池管理，提供多维调度、多租户资源隔离与弹性伸缩能力。'),
 ('Where do agent tools run?', '是否支持私有化与离线部署？',
  '全线产品支持私有化部署，可在离线环境下安装与升级。Moha 提供数据加密存储与传输加密，满足企业合规与安全要求。'),
 ('What does Lens record?', 'Moha 会记录哪些内容？',
  'Moha 记录模型与数据集的版本、元数据、标签与访问轨迹，支持全生命周期追踪、搜索分类、标签治理与协同发布。'),
 ('Is the platform available now?', '如何获取产品与试用？',
  'XMCP、Rune、Moha 与 AI Router 均已提供商业版，可通过官网预约演示，我们会在一个工作日内与您联系，并安排专家团队深入交流。'),
]
for q_en, q_cn, a_cn in FAQ:
    SENT[q_en] = q_cn
    T[q_en] = q_cn
SENT.update({
 'PipeLLM is a production control plane for AI agents. Relay governs model access, Loop runs stateful agent workloads, and Lens records the decisions behind every run.': FAQ[0][2],
 'Instead of stitching together a gateway, runtime, and observability stack, teams get three coordinated products, familiar SDK compatibility, shared controls, and a trace that stays connected from model request to agent outcome.': FAQ[1][2],
 'Yes. Route supported OpenAI-, Anthropic-, and Gemini-compatible traffic through PipeLLM.': FAQ[2][2],
 'Relay is the model gateway for approved models, routing policy, provider access, and tool permissions.': FAQ[3][2],
 'Managed tools attach inside Loop under the policy configured in Relay. Lens records every invocation.': FAQ[4][2],
 'Lens captures the request path, tool activity, approvals, and final outcome for observability, replay, and audit.': FAQ[5][2],
 'Relay is available today. Loop and Lens workspaces are being prepared.': FAQ[6][2],
})

# ------------------------------------------------------------ attribute swaps
ATTR = {
 'https://www.pipellm.ai/model': 'https://www.poxiaoshi.cn/blog/',
 'https://www.pipellm.ai/blog/agent-memory-next-bottleneck': 'https://www.poxiaoshi.cn/blog/',
 'https://www.pipellm.ai/blog/context-engineering-for-ai-agents': 'https://www.poxiaoshi.cn/blog/',
 'https://www.pipellm.ai/blog/why-unified-llm-gateway': 'https://www.poxiaoshi.cn/blog/',
 'https://www.pipellm.ai/blog': 'https://www.poxiaoshi.cn/blog/',
 'https://www.pipellm.ai/pricing': 'https://www.poxiaoshi.cn/',
 'https://www.pipellm.ai/': 'https://www.poxiaoshi.cn/',
 'https://console.pipellm.ai': 'https://console.poxiaoshi.cn',
 'https://api.pipellm.ai': 'https://api.poxiaoshi.cn',
 'https://docs.pipellm.ai': 'https://docs.poxiaoshi.cn',
 'https://docs.pipellm.ai/api-reference/introduction': 'https://docs.poxiaoshi.cn',
 'https://docs.pipellm.ai/websearch/overview.zh': 'https://docs.poxiaoshi.cn',
 '/relay': 'https://www.poxiaoshi.cn/products/rune/',
 '/runtime': 'https://www.poxiaoshi.cn/products/rune/',
 '/audit': 'https://www.poxiaoshi.cn/products/moha/',
 '/models': 'https://www.poxiaoshi.cn/products/',
 '/pricing': 'https://www.poxiaoshi.cn/',
 '/assets/logo-B-0OxcOB.svg': 'assets/img/logo.svg',
 '/pipellm-assets/dithered-bg-01.webp': 'assets/img/dither-bg-01.webp',
 '/pipellm-assets/dithered-bg-03.webp': 'assets/img/dither-bg-03.webp',
 '/pipellm-assets/dithered-footer.webp': 'assets/img/dither-footer.webp',
 '/pipellm-assets/cta-dithered.webp': 'assets/img/cta-dither.webp',
 '/pipellm-assets/product-image-01-1440.webp': 'assets/img/grid-ambient.webp',
 '/pipellm-assets/perspective-grid.webp': 'assets/img/perspective-grid.webp',
 '/pipellm-assets/data-icon.svg': 'assets/img/icon-cloud.svg',
 '/pipellm-assets/language-pixel.svg': 'assets/img/icon-chip.svg',
 '/pipellm-assets/plug-play.svg': 'assets/img/icon-db.svg',
 '/pipellm-assets/workflow-icon.svg': 'assets/img/icon-hex.svg',
 '/pipellm-assets/privacy-pixel.svg': 'assets/img/icon-gate.svg',
 '/pipellm-assets/team-overline-icon.svg': 'assets/img/icon-mark.svg',
 '/pipellm-assets/faq-icon.svg': 'assets/img/icon-faq.svg',
 '/pipellm-assets/information-icon.svg': 'assets/img/icon-info.svg',
 '/pipellm-assets/faq-toggle.svg': 'assets/img/icon-plus.svg',
 '/pipellm-assets/blog-cms/agent-memory-next-bottleneck.png': 'assets/img/blog/cover-ppu.png',
 '/pipellm-assets/blog-cms/context-engineering-for-ai-agents.png': 'assets/img/blog/cover-hygon.png',
 '/pipellm-assets/blog-cms/why-unified-llm-gateway.png': 'assets/img/blog/cover-oilfield.png',
 'PipeLLM logo': '晓石云 logo',
 'PipeLLM announcement': '晓石云公告',
 'PipeLLM partner ecosystem': '晓石云客户',
 'PipeLLM control plane services': '晓石云核心产品',
 'SDK request examples': '云平台接入示例',
 'Loop SDK examples': 'Rune 示例',
 'WebSearch route examples': 'AI Router 接入示例',
 'Your work email': '您的企业邮箱',
 'Talk to Sales': '联系销售',
 'Open Console': '预约演示',
 'Copy code': '复制代码',
 'mailto:support@pipellm.com': 'mailto:support@xiaoshiai.cn',
 'mailto:sales@pipellm.com': 'mailto:support@xiaoshiai.cn',
 'mailto:careers@pipellm.com': 'mailto:support@xiaoshiai.cn',
 'https://status.pipellm.com': 'https://www.poxiaoshi.cn/',
 'https://www.youtube.com': 'https://docs.poxiaoshi.cn',
 'https://github.com': 'https://github.com/poxiaoyun',
 'https://x.com/pipellmai': 'mailto:support@xiaoshiai.cn',
 'https://www.instagram.com': 'https://www.poxiaoshi.cn/contact/',
 'aria-label="YouTube"': 'aria-label="文档中心"',
 'aria-label="GitHub"': 'aria-label="GitHub"',
 'aria-label="X"': 'aria-label="邮箱"',
 'aria-label="Instagram"': 'aria-label="联系我们"',
 'support@pipellm.com': 'support@xiaoshiai.cn',
 'Tsingcloud': '云控智行',
 'PipeLLM': '晓石云',
 'Relay': 'Rune',
 'Loop': 'XMCP',
 'Lens': 'Moha',
}

# partner logo strip -> 晓石云 customers
PARTNERS = [
 ('china-mobile', 'logo-china-mobile.png', '中国移动 · China Mobile'),
 ('nvidia', 'logo-nvidia.png', 'NVIDIA'),
 ('anton', 'logo-anton.png', 'ANTON 安东石油'),
 ('cenc', 'logo-cenc.png', '中国地震台网中心'),
 ('swufe', 'logo-swufe.png', '西南财经大学'),
 ('swjtu', 'logo-swjtu.png', '西安交通大学'),
 ('cloudminds', 'logo-cloudminds.png', '达阀机器人'),
 ('wanwuzhilian', 'logo-wanwuzhilian.png', '万物智联'),
]

# ------------------------------------------- 0. scoped pre-replacements
def rep_section(anchor, pairs, end_marker=None):
    """Replace inside the slice that starts at `anchor`."""
    global body
    i = body.find(anchor)
    if i < 0:
        MISS.append('anchor: ' + anchor[:60])
        return
    j = body.find(end_marker, i) if end_marker else len(body)
    if j < 0:
        j = len(body)
    chunk = body[i:j]
    for a, b in pairs:
        if a not in chunk:
            MISS.append('scoped miss: ' + a[:60])
        chunk = chunk.replace(a, b)
    body = body[:i] + chunk + body[j:]


# pricing cards: 01 == compute (Rune), 02 == multicloud (XMCP)
rep_section('<section id="pricing"', [
    ('<h3>Relay</h3>', '<h3>Rune</h3>'),
    ('<h3>Loop</h3>', '<h3>XMCP</h3>'),
])
# AI Router section: console link label
rep_section('<section id="tools"', [('<b>Open Console</b>', '<b>打开控制台</b>')])
# runtime signal strip keeps the dataset reference
rep_section('<section id="runtime"', [('<b>websearch.attach</b>', '<b>moha://datasets/corpus-v3</b>')])
# control-plane "next section" divider
body = body.replace('const next = await fetch("https://api.pipellm.ai/next-section");',
                    'const next = await fetch("https://api.poxiaoshi.cn/products");')

# ------------------------------------------------- 1. rebuild partner marquee
m = re.search(r'<div class="tf-partner-logo-track">[\s\S]*?</div>\s*</div>\s*</div>\s*</section>', body)
if not m:
    MISS.append('partner track')
else:
    items = []
    for _ in range(2):
        for key, f, name in PARTNERS:
            items.append(
                f'<div class="tf-partner-logo is-wordmark" title="{name}" aria-label="{name}">'
                f'<img src="assets/img/{f}" alt="" aria-hidden="true"></div>')
    block = ('<div class="tf-partner-logo-track">' + ''.join(items) +
             '</div>\n      </div>\n    </div>\n  </section>')
    body = body[:m.start()] + block + body[m.end():]

# --------------------------------------------------- 2. rebuild footer columns
FOOTER = [
 ('产品', [('产品总览', 'https://www.poxiaoshi.cn/'),
        ('Rune', 'https://www.poxiaoshi.cn/products/rune/'),
        ('XMCP', 'https://www.poxiaoshi.cn/products/xmcp/'),
        ('Moha', 'https://www.poxiaoshi.cn/products/moha/'),
        ('KubeGems', 'https://kubegems.io'),
        ('AI Router', 'https://www.poxiaoshi.cn/products/ai-router/')]),
 ('文档与资源', [('快速开始', 'https://docs.poxiaoshi.cn'),
            ('API 参考', 'https://docs.poxiaoshi.cn'),
            ('私有化部署', 'https://docs.poxiaoshi.cn'),
            ('离线安装', 'https://docs.poxiaoshi.cn'),
            ('版本变更', 'https://docs.poxiaoshi.cn'),
            ('最佳实践', 'https://docs.poxiaoshi.cn')]),
 ('解决方案', [('混合云', 'https://www.poxiaoshi.cn/solutions'),
           ('智算中心', 'https://www.poxiaoshi.cn/solutions'),
           ('教育行业', 'https://www.poxiaoshi.cn/cases'),
           ('能源制造', 'https://www.poxiaoshi.cn/cases'),
           ('AI 应用', 'https://www.poxiaoshi.cn/products/chatbox/')]),
 ('公司', [('联系我们', 'mailto:support@xiaoshiai.cn'),
         ('联系销售', 'mailto:support@xiaoshiai.cn'),
         ('加入我们', 'https://www.poxiaoshi.cn/about/'),
         ('__HIRING__', '')]),
]
m = re.search(r'<div class="tf-footer-columns">[\s\S]*?</div>\s*</div>\s*<div class="tf-footer-status">', body)
if not m:
    MISS.append('footer columns')
else:
    cols = []
    for title, links in FOOTER:
        lis = []
        for text, href in links:
            if text == '__HIRING__':
                lis.append('<span class="tf-footer-hiring"><i></i>原生无界 · 破晓时刻。</span>')
                continue
            tgt = ' target="_blank" rel="noopener noreferrer"' if href.startswith('http') else ' rel="noopener noreferrer"'
            lis.append(f'<a class="tf-footer-link hover-scramble" href="{href}"{tgt}>{text}</a>')
        cols.append(f'<div class="tf-footer-column"><h3>{title}</h3>'
                    f'<div class="tf-footer-link-list">{"".join(lis)}</div></div>')
    # NOTE: the regex already consumed the last column's </div> plus the
    # </div> that closes .tf-footer-columns, so only ONE closing div is owed
    # here. Adding a second one closes .tf-reference-footer-shell early and
    # pushes .tf-footer-status / .tf-footer-bottom / img.tf-footer-grid out of
    # the footer, which lets the 928px decorative grid escape
    # overflow:hidden and blow up the mobile layout viewport (doc scrollWidth
    # 659 instead of 390).
    body = body[:m.start()] + ('<div class="tf-footer-columns">' + ''.join(cols) +
                               '</div>\n    <div class="tf-footer-status">' +
                               body[m.end():])


# ------------------------------------- 2b. rebuild footer social links
SOCIALS = [
    ('https://docs.poxiaoshi.cn', '文档中心', 'target="_blank" rel="noopener noreferrer"',
     '<path d="M12 7v14"></path><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"></path>'),
    ('https://github.com', 'GitHub', 'target="_blank" rel="noopener noreferrer"',
     '<path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"></path><path d="M9 18c-4.51 2-5-2-7-2"></path>'),
    ('mailto:support@xiaoshiai.cn', '邮箱', '',
     '<rect width="20" height="16" x="2" y="4" rx="2"></rect><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"></path>'),
    ('https://www.poxiaoshi.cn/contact/', '联系我们', 'target="_blank" rel="noopener noreferrer"',
     '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"></path><circle cx="12" cy="10" r="3"></circle>'),
]
m = re.search(r'<div class="tf-footer-socials">[\s\S]*?</div>\s*</div>', body)
if not m:
    MISS.append('footer socials')
else:
    links = ''.join(
        f'<a href="{href}" aria-label="{label}" {attrs}>'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{paths}</svg></a>'
        for href, label, attrs, paths in SOCIALS)
    body = body[:m.start()] + '<div class="tf-footer-socials">' + links + '</div>\n        </div>' + body[m.end():]

# ------------------------------------------------- 3. text-node level swapping
def swap_text(mo):
    raw = mo.group(0)
    inner = raw[1:-1]
    lead = inner[:len(inner) - len(inner.lstrip())]
    tail = inner[len(inner.rstrip()):]
    core = inner.strip()
    core = core.replace('&nbsp;', ' ')
    if not core:
        return raw
    if core in SENT:
        new = SENT[core]
    elif core in T:
        new = T[core]
    else:
        return raw
    return '>' + lead + new + tail + '<'


body = re.sub(r'>[^<>]+<', swap_text, body)

# leftovers check (long-form copy only)
for old in SENT:
    if old in body:
        MISS.append('leftover: ' + old[:70])

# env var names inside the static syntax-highlighted code samples
body = body.replace('process.env.PIPELLM_API_KEY', 'process.env.XIAOSHI_API_KEY')

# -------------------------------------------- 4. rewrite attributes / urls
for k, v in sorted(ATTR.items(), key=lambda kv: -len(kv[0])):
    body = body.replace(k, v)

# --------------------------------------------------- 5. gateway code surface
CODE_LINES = [
    ('<span class="tf-syntax-keyword">import</span> { Cloud } from '
     '<span class="tf-syntax-string">"@xiaoshi/xmcp"</span>;', 0),
    ('', 0),
    ('<span class="tf-syntax-keyword">const</span> cloud = '
     '<span class="tf-syntax-keyword">await</span> '
     '<span class="tf-syntax-function">Cloud</span>.attach({', 0),
    ('  <span class="tf-syntax-property">platform</span>: '
     '<span class="tf-syntax-string">"kubernetes"</span>,', 1),
    ('  <span class="tf-syntax-property">region</span>: '
     '<span class="tf-syntax-string">"cn-southwest-1"</span>,', 1),
    ('  <span class="tf-syntax-property">policy</span>: '
     '<span class="tf-syntax-string">"zero-trust-mesh"</span>', 1),
    ('});', 0),
    ('', 0),
    ('<span class="tf-syntax-comment">// 统一纳管 · 统一计量 · 统一策略</span>', 0),
]
old_code = re.search(
    r'<div class="relative font-mono">[\s\S]*?<div class="font-mono text-sm leading-\[21px\] overflow-x-auto">[\s\S]*?</div>\s*</div>\s*</div>\s*</div>\s*</div>',
    body)
if not old_code:
    MISS.append('gateway code surface')
else:
    nums = ''.join(
        f'<div class="h-[21px]">{i + 1 if i < len(CODE_LINES) else ""}</div>'
        for i in range(9))
    code = ''.join(
        f'<div class="h-[21px] relative whitespace-pre">{"　" * ind}{line}</div>'
        for line, ind in CODE_LINES)
    code += ''.join('<div class="h-[21px] relative whitespace-pre"></div>'
                    for _ in range(max(0, 9 - len(CODE_LINES))))
    new = ('<div class="relative font-mono"><div class="p-4 font-mono text-sm">'
           '<div class="grid grid-cols-[auto_1px_1fr] gap-4 items-start">'
           f'<div class="flex flex-col text-right text-[#4A5568] font-mono text-sm leading-[21px] select-none min-w-[2rem]">{nums}</div>'
           '<div class="w-px bg-[#2d3748] flex-shrink-0"></div>'
           f'<div class="font-mono text-sm leading-[21px] overflow-x-auto">{code}</div>'
           '</div></div></div>')
    body = body[:old_code.start()] + new + body[old_code.end():]

# ------------------------------------------- 6. rebuild CTA action char spans
LABEL_NEEDLE = '<span class="tf-brand-action-label" aria-hidden="true">'
SR = re.compile(r'<span class="sr-only">\s*([^<]+?)\s*</span>')
ORDER = [0, 7, 2, 9, 4, 11, 6, 1, 8, 3, 10, 5]


def label_block(text):
    out = []
    for i, ch in enumerate(text):
        c = '&nbsp;' if ch == ' ' else html.escape(ch)
        out.append(f'<span style="--tf-brand-char:{ORDER[i % len(ORDER)]}">{c}</span>')
    return LABEL_NEEDLE + ''.join(out) + '</span>'


pieces, idx = [], 0
while True:
    i = body.find(LABEL_NEEDLE, idx)
    if i < 0:
        pieces.append(body[idx:])
        break
    pieces.append(body[idx:i])
    k, depth = i + len(LABEL_NEEDLE), 1
    while depth > 0:
        o = body.find('<span', k)
        c = body.find('</span>', k)
        if c < 0:
            break
        if 0 <= o < c:
            depth += 1; k = o + 5
        else:
            depth -= 1; k = c + 7
    sr = SR.search(body, k, k + 1200)
    if not sr:
        pieces.append(body[i:k]); idx = k; continue
    pieces.append(label_block(sr.group(1).strip()))
    pieces.append(body[k:sr.end()])
    idx = sr.end()
body = ''.join(pieces)

open('body.tmp.html', 'w', encoding='utf-8').write(body)

HEAD = '''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>晓石云 | 智算为中心的 AI 原生云内核 — 成都破晓石科技</title>
<meta name="description" content="专注云原生开源、混合云与 AI 智算平台，为企业提供覆盖容器云、混合云、智算云及 AI 能力的全栈解决方案。">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=Geist+Mono:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link rel="icon" type="image/svg+xml" href="assets/img/icon-mark.svg">
<link rel="stylesheet" href="assets/css/vendor.css">
<link rel="stylesheet" href="assets/css/custom.css">
</head>
<body>
'''
TAIL = '''
<script src="assets/js/main.js"></script>
</body>
</html>
'''
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, 'w', encoding='utf-8').write(HEAD + body + TAIL)

# ------------------------------------------ 6a. leftover brand token guard
# run on the FINAL markup: earlier stages legitimately still hold pipe llm
# urls that a later attribute rewrite is responsible for.
final = HEAD + body + TAIL
for bad in ('PIPELLM', 'PipeLLM', 'pipellm.ai', 'pipellm.com', 'pipellm-assets',
            'Partner with us', 'All Systems Operational'):
    if bad in final:
        MISS.append('leftover token: ' + bad)

# ------------------------------------------------------- 6b. structure guard
# A stray </div> silently reparents later siblings (this is exactly how
# img.tf-footer-grid escaped the footer's overflow:hidden and broke mobile).
opens = len(re.findall(r'<div\b', body))
closes = len(re.findall(r'</div>', body))
if opens != closes:
    MISS.append(f'unbalanced <div>: {opens} open vs {closes} close (delta {opens - closes})')
m = re.search(r'<footer class="tf-reference-footer">[\s\S]*?</footer>', body)
if not m or 'tf-footer-grid' not in m.group(0):
    MISS.append('img.tf-footer-grid is not inside footer.tf-reference-footer')

# ------------------------------------------------------------ 7. vendor css
css = open('pipellm.css', encoding='utf-8').read()
for src, dst in [
    ('/pipellm-assets/dithered-bg-01.webp', '../img/dither-bg-01.webp'),
    ('/pipellm-assets/dithered-bg-03.webp', '../img/dither-bg-03.webp'),
    ('/pipellm-assets/dithered-footer.webp', '../img/dither-footer.webp'),
    ('/pipellm-assets/cta-dithered.webp', '../img/cta-dither.webp'),
    ('/pipellm-assets/product-image-01-1440.webp', '../img/grid-ambient.webp'),
    ('/pipellm-assets/perspective-grid.webp', '../img/perspective-grid.webp'),
]:
    css = css.replace(src, dst)
open('../xiaoshi-cloud/assets/css/vendor.css', 'w', encoding='utf-8').write(css)

print('built', OUT, len(HEAD + body + TAIL))
print('issues:')
for x in MISS:
    print('  ', x)
