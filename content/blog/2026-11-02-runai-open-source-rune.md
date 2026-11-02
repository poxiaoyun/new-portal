---
title: NVIDIA 开源了 Run:ai，机房同事还在对门户和账
slug: 2026-11-02-runai-open-source-rune
date: 2026-11-02
cover: assets/img/news/20261102-twin.webp
tag: 产品观察
summary: 近日 NVIDIA 将 Run:ai 以 Apache 2.0 开源。调度层能改了，智算中心现场仍常卡在门户、配额出账和模型统一入口。破晓石产品线 Rune AI 补的是训推门户、资产仓、网关与运营这条链，与 Run:ai 互补多于对标。
---

近日 NVIDIA 把 Run:ai（也有人写 RunAI）开源了，仓库在 `dsx-ai-factory/run-ai`，许可是 Apache 2.0。群里最先刷的是分数 GPU、配额、多租户调度。代码能翻开看了。

Run:ai 做的事很具体：在 Kubernetes 上排 GPU 和作业，卡怎么切、部门怎么分额度、作业落到哪台节点。它是调度层。开源之后，改调度规则的门槛确实低了。

![NVIDIA Run:ai Overview](assets/img/news/20261102-runai-overview.webp)

![NVIDIA Run:ai Projects](assets/img/news/20261102-runai-projects.webp)

智算中心月底对账时，运营同事面前通常还是三样东西：监控里的卡时、表格里的租户配额、财务要的出账明细。调度开源解决不了这三份数对不齐。开发要在浏览器里选规格、交训练、起推理；业务要调好几家模型，密钥和限流不能散着放，还要留审核记录；数据和内容还得出不了企业边界。这些都不在调度层里。

破晓石的产品线叫 **Rune AI**。开发进 Rune 门户交训推、起开发环境。管理员看资源池容量和节点加速卡，再进 Boss 做开户、配额、计量、出账，月底少翻几张散表。模型、数据集、镜像放 Moha。业务和 Agent 走 AIRouter（也叫 LLMG）的统一入口，选路、审核、调用审计跟着请求走。机房里若还有数字孪生、XCMP，或 NVIDIA 跟昇腾、海光混着跑，也可以收到同一套纳管和维保视图里。

![Rune AI 资源池](assets/img/news/20261102-rune-pool.webp)

![Rune AI 开发服务](assets/img/news/20261102-rune-dev.webp)

![Moha 模型库](assets/img/news/20261102-moha.webp)

![AIRouter 模型广场](assets/img/news/20261102-airouter.webp)

![Rune AI 数字孪生](assets/img/news/20261102-twin.webp)

客户跟我们聊，很少一上来比谁切 GPU 更细。问得更多的是：门户能不能一次交完训推；配额和出账能不能同源导出；模型调用有没有统一出口和审核流水；数据能不能不出域；异构卡能不能进同一套配额。Rune AI 把力气花在这些点上。超限尽量在配额层拦住，不必等任务跑完再补记；调用侧能留下审计，澄清会和等保口径也好交代。

Run:ai 强在调度深度、开源可改、NVIDIA 生态。Rune AI 强在门户、资产、网关、运营收在一条链上，更贴政企私有化现场。两者互补多于对标。一层管卡怎么排；一层管门户怎么用、资产怎么留、模型怎么调、账怎么出。不要把 Run:ai 当成大模型网关来比。

若要对照门户、统一入口和按租户出账，带上租户表头、资源池结构或模型调用清单预约演示：[联系破晓石](https://www.poxiaoshi.cn/contact/)
