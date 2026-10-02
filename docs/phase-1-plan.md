# 项目解读实验室：首阶段开发计划

| 项目 | 内容 |
| --- | --- |
| 文档版本 | v0.23 |
| 文档状态 | M1–M5 本地范围验收完成；M4-T01 当前策略真实兼容通过、M4-T03 独立人工审阅通过；v0.2 进入门槛已满足，后续开发未开始 |
| 更新日期 | 2026-09-30 |
| 适用阶段 | 文档准备及 v0.1 的 M1 至 M5 |
| 本文职责 | 执行依赖、任务范围、退出条件及实际验证记录的权威来源 |

## 1. 当前状态与执行边界

工作台共 37 个 HTTP 操作，M1–M5 的本地范围验收已完成。此前预算缺陷、修复和截断失败记录保留历史；用户随后明确要求“不限制预算和请求限制，只保留请求地址、模型ID和Api key”，当前策略的本地实现与验证已完成。本轮补齐 M4-T01，83项聚焦回归通过，取得新的单次授权后，DeepSeek 的 deepseek-flash 基础非流式请求成功发布有效讲解，真实兼容验收通过；既有 M4-T03 独立人工内容审阅结论保留。v0.1 在标准样例和既有参考环境范围内完成本地验收，不等同于其他模型或容量承诺。当前目录不是 Git 仓库，未初始化；具体命令、结果和限制见第 10 节最新记录。没有修改业务代码、模型配置或进行额外模型调用，数据库与历史保留，原5173–5176实例不受影响。

需求依据为[产品需求文档](requirements.md)，版本边界依据为[总体路线图](roadmap.md)。执行遵守 PLAN → EXECUTE → TEST → DELIVER，每次只处理用户指定的一个任务及其必要测试、文档同步；前置任务缺失时说明阻塞，不自行完成其他编号任务。新会话入口见[任务提示词](codex-task-prompt.md)，项目约束见 [AGENTS.md](../AGENTS.md)。

不采用固定日历日期。下一里程碑开始前，记录上一里程碑验收结果、未解决限制和依赖状态；关键验收失败不得被后续进度覆盖。

v0.2 的 M6–M10 规划、任务状态和验证记录仅见[第二阶段计划](phase-2-plan.md)，本文继续唯一维护 v0.1 的 M1–M5。当前 M4-T01 真实兼容及 M4-T03 独立人工内容审阅均通过，本版交付结论已更新，v0.2 进入门槛已满足；本轮到 M4-T01 停止，只有用户指定新的任务范围后才开始 M6。

## 2. 文档阶段交付与进入 M1 的条件

| 文档交付 | 当前状态 |
| --- | --- |
| 定位、首版范围、FR/NFR 与 AT 用例 | 已建立，见[需求文档](requirements.md) |
| 当前及后续版本边界 | 已建立，见[路线图](roadmap.md) |
| 后端、前端与 API 规则 | 已建立，技术兼容性仍需项目实测 |
| 需求到任务和用例的追踪 | 已建立，见下文 |
| 目录职责、命名与扩展方法 | 已建立，见[项目结构](project-structure.md)；已创建 M1–M5 本地组件，后续目录仍按授权任务创建 |
| API 分类与首版端点归属 | 已建立，见 [API 清单](api-catalog.md)；业务字段仍须编码前细化 |
| 单任务执行与恢复入口 | 已建立，见[任务提示词](codex-task-prompt.md)和根目录项目指令 |

进入 M1 前，应确认任务范围仍符合本基线，选定无敏感内容的样例，并完成必要环境只读检查。文档编写完成不自动授权安装依赖、执行代码或部署。

## 3. 依赖顺序

```mermaid
flowchart LR
    M1[基础与样例] --> M2[导入与后端分析]
    M2 --> M3[前后端关联]
    M3 --> M4[讲解与练习]
    M4 --> M5[实验与交付]
```

每个任务按“设计契约与预期 → 实现 → 聚焦测试 → 文档同步 → 验收记录”推进。同一里程碑默认按编号顺序执行；首个任务以前一里程碑退出条件为前置，M1-T01 以前文的文档与环境核对条件为前置。例外须说明已具备的实际依赖，不自动跳过验收。

[API 清单](api-catalog.md)固定首版方法、路径和归属；业务字段及错误须在对应任务编码前按 [API 规范](api-conventions.md)细化。M1-T02 的最小生成入口与 M1-T03 的独立示例契约，在 M1-T04 统一纳入检查；未实现接口不生成占位产物；M2-T04 完善恢复机制，不意味着此前可以省略基本任务持久化和重复提交保护。

目录只在当前任务需要时按[项目结构](project-structure.md)创建。每个任务结束后核对验收并停止，不自动进入下一任务；已完成任务只核验现状。

## 4. M1：基础与样例

| 任务 | 范围与交付 | 对应需求 | 验证与退出条件 | 当前状态 |
| --- | --- | --- | --- | --- |
| M1-T01 | 核对兼容矩阵、锁定直接依赖与运行环境，记录选型、许可证和必要性；确定本地配置与资源上限 | NFR-04、NFR-06 | 后端与前端基础工具能在参考环境运行；版本记录不再只依赖网页声明 | 已完成 |
| M1-T02 | 最小 React/DRF 工程、PostgreSQL、Redis、Worker 和同源入口；固定基础链路检查及匿名本地写操作的 CSRF/来源校验 | FR-08、NFR-03、NFR-04 | 最小任务能提交、持久化、查询；AT-24；依赖服务故障可见 | 已完成 |
| M1-T03 | 独立任务管理示例：标题提交、校验、持久化及页面更新；人工标注“创建任务”关系 | FR-02、FR-03、FR-06、FR-07 | 正常输入、缺失、空字符串和纯空白标题有真实测试；准备 AT-04、AT-07、AT-16 的基准 | 已完成 |
| M1-T04 | 本阶段接口表、错误处理基线、OpenAPI 导出和前端类型生成入口；建立测试及检查命令 | NFR-02、NFR-06 | 契约、类型与实现一致；命令执行后才记录为已验证 | 已完成 |

学习产出：画出浏览器、API、数据库与 Worker 的数据流，说明 HTTP 校验与数据库约束的职责，记录同源代理与 CSRF 的验证方式。

退出条件：示例独立可运行、正常与非法输入测试完成、基础任务可查询、工具版本及真实命令已记录。不得将生成工程文件本身视为 M1 完成。

## 5. M2：导入与后端分析

| 任务 | 范围与交付 | 对应需求 | 验证与退出条件 | 当前状态 |
| --- | --- | --- | --- | --- |
| M2-T01 | 项目记录、ZIP 边界校验、过滤、暂存及原子发布、不可变快照、导入摘要和受控文件读取 | FR-01、FR-04、FR-08、NFR-01、NFR-06 | AT-01、AT-02、AT-03、AT-21 | 已完成 |
| M2-T02 | Python AST 与 DRF 静态规则、源码引用、覆盖说明及解析诊断 | FR-02、NFR-02 | AT-04、AT-05、AT-06；覆盖标准路由及 Router 规则，不运行导入模块 | 已完成 |
| M2-T03 | 关系存储、BFS/DFS 遍历、循环处理、节点及边的证据来源 | FR-02、FR-04、NFR-02 | 人工标注结果匹配；空图、孤立节点和循环依赖不会导致错误连接或无限遍历 | 已完成 |
| M2-T04 | PostgreSQL 任务记录、发布失败处理、幂等提交、超时核对及迟到结果拒绝 | FR-08、NFR-03 | AT-18、AT-19、AT-20；队列异常不产生永久处理中任务 | 已完成 |

学习产出：解释 AST 能得到什么、不能得到什么；实现并测试图遍历；记录文件发布与任务状态在部分失败时的边界。

退出条件：后端样例可分析、错误有明确分类、快照不被覆盖、Worker 中断能收敛、危险归档和敏感文件不进入有效上下文。

## 6. M3：前后端关联

| 任务 | 范围与交付 | 对应需求 | 验证与退出条件 | 当前状态 |
| --- | --- | --- | --- | --- |
| M3-T01 | 独立 Node 解析工程及 JSON Schema 输入输出协议、TypeScript Compiler API 解析入口、静态请求和可解析本地直接调用 | FR-03、NFR-02 | AT-07、AT-08；受控调用解析器，不加载用户构建插件或安装依赖 | 已完成 |
| M3-T02 | 方法/路径关联及未知基础路径、重复候选的呈现 | FR-03、FR-04、NFR-02 | AT-08；不随意删改路径来获得唯一匹配 | 已完成 |
| M3-T03 | 工作区、快照与接口导航、流程与源码联动、空/部分/失败状态 | FR-04、FR-08、NFR-03、NFR-05 | AT-09、AT-10、AT-23；旧响应不污染新选择 | 已完成 |

学习产出：说明服务端数据、URL 状态与局部交互状态的区别；解释请求取消、迟到响应以及静态关联与实际运行的差异。

退出条件：从示例前端提交入口定位到 DRF 模型，源码点击可用，无法确定的关系可见，键盘能够完成核心浏览操作。

## 7. M4：讲解与练习

| 任务 | 范围与交付 | 对应需求 | 验证与退出条件 | 当前状态 |
| --- | --- | --- | --- | --- |
| M4-T01 | Chat Completions 基础非流式适配、三项配置、返回结构及具体服务兼容检查；模型请求无应用预算/总期限 | FR-05、NFR-03、NFR-06 | AT-12；先用合成响应覆盖错误，真实调用须单次确认，供应商费用及默认限制由用户判断 | 已完成：83项聚焦回归及一次授权的 DeepSeek/deepseek-flash 当前策略真实兼容通过；旧失败记录保留 |
| M4-T02 | 按有界静态图选择完整片段、外发预览和绑定确认、讲解引用验证、模型内容安全展示 | FR-05、NFR-01、NFR-02 | AT-11、AT-13、AT-14；模型不能控制读取范围或执行动作 | 已完成（本地边界验收，模型字节预算按用户要求取消） |
| M4-T03 | 三类固定题、人工核对的知识卡片、答案版本、作答记录与反馈 | FR-06、FR-08、NFR-02 | AT-15、AT-18；每类至少一题，提示与掌握判断分开 | 已完成：实现与自动化验收通过，用户于2026-09-30确认当前版本独立人工内容审阅通过 |

学习产出：解释检索与生成的职责、为什么行号有效不代表解释正确，以及模型调用的失败与潜在重复计费边界。

退出条件：用户可以完成阅读、预测和反馈；外发与引用检查有效；无模型时基础能力仍可使用。仅通过测试替身不能宣称模型服务兼容性已验证。

## 8. M5：实验与交付

| 任务 | 范围与交付 | 对应需求 | 验证与退出条件 | 当前状态 |
| --- | --- | --- | --- | --- |
| M5-T01 | 固定请求校验实验接口、按运行隔离的数据、实际响应和写入观测 | FR-07、NFR-01 | AT-16、AT-17、AT-22；不可用时不显示模拟成功 | 已完成（本地受控示例） |
| M5-T02 | 浏览器完整流程、刷新恢复、并发提交和异常路径回归 | FR-01、FR-04、FR-05、FR-06、FR-07、FR-08、NFR-03、NFR-05 | 聚焦回归 AT-01、AT-09 至 AT-23，涉及的已验证用例只在有变化或风险时重复 | 已完成（本地闭环，讲解使用明确授权的固定替身） |
| M5-T03 | 干净参考环境复现、明确规模的资源与耗时观测、启动与故障说明、演示材料 | NFR-04、NFR-06 | AT-24、AT-25；记录硬件、输入规模、版本和实际限制 | 已完成（空数据卷、固定工具与缓存镜像；本地替身范围） |
| M5-T04 | 完整差异审阅、验收归档、项目文档同步与 v0.1 交付结论 | FR-01、FR-02、FR-03、FR-04、FR-05、FR-06、FR-07、FR-08 | 全部首版用例有通过、失败或阻塞记录；关键阻塞未解决不得宣布首版完成 | 已完成（本地交付；v0.1 当前结论见最新 M4-T01 验收记录） |

学习产出：一次成功和一次失败的实验记录、关键技术取舍说明、能够现场复现的演示，以及需要后续阶段解决的限制。

## 9. 需求追踪汇总

| 需求 | 主要任务 | 验收用例 |
| --- | --- | --- |
| FR-01 | M2-T01、M5-T02 | AT-01、AT-02、AT-03、AT-21 |
| FR-02 | M1-T03、M2-T02、M2-T03 | AT-04、AT-05、AT-06 |
| FR-03 | M1-T03、M3-T01、M3-T02 | AT-07、AT-08 |
| FR-04 | M2-T01、M2-T03、M3-T03 | AT-09、AT-10、AT-23 |
| FR-05 | M4-T01、M4-T02 | AT-11、AT-12、AT-13、AT-14 |
| FR-06 | M1-T03、M4-T03 | AT-15、AT-18 |
| FR-07 | M1-T03、M5-T01 | AT-16、AT-17、AT-22 |
| FR-08 | M1-T02、M2-T01、M2-T04、M3-T03、M4-T03 | AT-18、AT-19、AT-20 |
| NFR-01 | M2-T01、M4-T02、M5-T01 | AT-02、AT-03、AT-11、AT-21、AT-22 |
| NFR-02 | M1-T04、M2-T02、M2-T03、M3-T01、M3-T02、M4-T02、M4-T03 | AT-05、AT-08、AT-09、AT-13、AT-14 |
| NFR-03 | M1-T02、M2-T04、M3-T03、M4-T01、M5-T02 | AT-10、AT-12、AT-18、AT-19、AT-20 |
| NFR-04 | M1-T01、M1-T02、M5-T03 | AT-24 |
| NFR-05 | M3-T03、M5-T02 | AT-23 |
| NFR-06 | M1-T01、M1-T04、M2-T01、M4-T01、M5-T03 | AT-02、AT-20、AT-25 |

## 10. 验证记录与交付规则

各任务表的“当前状态”为单任务进度入口，里程碑表为汇总。M1–M5 状态见上表，当前本地范围验收已完成。后续只在本文更新为进行中、受阻或已完成，并在本节补充对应任务的验证记录；任务进度状态不等同于产品后台任务的四态协议，不另建平行进度文件。

实际记录至少包含：任务编号、文档/样例/实现版本、参考环境、执行目录、完整命令或操作、预期与实际结果、失败分类、证据位置及剩余限制。记录经过脱敏，不能包含秘密、真实用户源码正文或原始敏感日志。

| 里程碑 | 当前状态 | 产品测试状态 |
| --- | --- | --- |
| M1 | 已完成（M1-T01 至 M1-T04） | 本次契约/错误/类型检查通过；保留 AT-24 与基础检查验收；AT-04/07 人工基准和 AT-16 示例输入行为通过，不代表完整解析器、学习或实验验收 |
| M2 | 已完成（M2-T01 至 M2-T04） | 导入/快照、声明静态规则和有界图回归通过；AT-18/19/20 在现有三类任务及 Linux API/Worker 边界通过；不代表前端工作区、作答、模型或实验完成 |
| M3 | 已完成 | AT-07/08/09/10/23 在有限静态规则、隔离 Linux 服务和真实浏览器范围通过；详情见本节 M3 记录 |
| M4 | 已完成（当前模型策略与固定内容范围） | 独立人工内容审阅通过；当前策略 DeepSeek/deepseek-flash 真实兼容通过，单次确认、格式/引用校验和失效恢复保留；旧 MODEL_TRUNCATED 记录保留 |
| M5 | 本地实现、验证与交付完成 | 固定实验、失败/隔离/恢复通过；结合最新 M4-T01 和既有 M4-T03 证据，v0.1 本地交付验收完成 |

测试顺序从当前变更的直接行为开始，再做模块、静态检查、类型、契约与必要集成验证。已通过的检查不因追求数量反复执行；新增变化或未解除风险时才扩大范围。

M1-T01 仅验证工具入口。M1-T02 已验证基础服务、有限 OpenAPI/类型生成及页面提交与刷新；完整产品流程仍待后续任务。命令不可运行时记录原因，不用模拟输出填补证据。

### M1-T01 首次工具基线检查记录（2026-09-28，历史受阻结果）

范围：已授权建立后端/前端各自的依赖与工具工程，使用自建无敏感内容的字段及组件检查样例；无导入源码、业务 API、数据库、Worker、模型调用或 Git 写操作。清单约束直接需要的包，锁文件保存解析结果及完整性信息，二者须与实际运行版本交叉核对。

初始工作目录为 `F:\Program\Fall_Campus_Recruitment`，原有根指令与九份文档，`git status --short --branch` 返回 `not a git repository`。修改前文本与 SHA-256 清单保存在被忽略的 `.runtime/m1-t01-baseline`；不初始化 Git。未发现独立项目记忆，沿用本文作为唯一任务进度。

参考环境：Windows x64（内核版本 10.0.26200），24 个可用逻辑处理器、约 32 GiB 内存；PowerShell 7.6.5。全局 Python 3.13.13、uv 0.11.26、Node 24.14.0/npm 11.9.0 保持原样。目标隔离版本及官方依据见前后端规范，不能用全局旧版本冒充目标环境。

环境准备及已观察的问题：

| 工作目录 | 实际命令或操作 | 观察结果与分类 |
| --- | --- | --- |
| 根目录 | `python -u -X utf8 scripts/prepare_toolchain.py` | 官方下载较慢，首次下载触发 300 秒限制；保留分片后按精确偏移续传，完整 SHA-256 通过才使用。最终固定 uv/Node 分发校验通过，Python 准备完成；分发摘要和实际运行版本另记 |
| 根目录 | `python -X utf8 -m unittest discover -s scripts -p test_prepare_toolchain.py -v` | 最终 7 项通过。首次沙箱系统临时目录访问被拒，提升权限后可执行；新增完整分片复用用例发现 Windows 文件未关闭导致 WinError 32，修复关闭顺序后全通过。测试替身只覆盖下载器，不作为平台兼容证据 |
| 根目录 | `docker desktop start --timeout 120`（实际使用安装目录下的 CLI） | 初次启动未及时就绪，返回 context deadline exceeded；后续用户启动 Desktop 后重新检查成功 |
| 根目录 | `& 'C:/Program Files/Docker/Docker/resources/bin/docker.exe' version --format '{{json .Server}}'` | 初次 Linux 引擎管道不存在；用户启动后返回 Engine 29.4.0、Docker Desktop 4.69.0、Linux amd64、WSL2 内核 5.15.167.4，环境阻塞已解除 |
| 根目录 | PowerShell Parser 解析 `scripts/check-toolchain.ps1`；通过标准输入运行 `python -X utf8 -` 解析 Python/JSON/TOML 并核对文档 | 语法及清单解析通过，80 处本地链接与显式锚点有效；需求、API 清单、API 契约、任务提示词与备份逐字节一致 |

Docker CLI 不在默认 PATH，首次镜像拉取报 `docker-credential-desktop` 不可执行；检查入口只为当前进程补入现有 Docker 工具目录，保留原 PATH 并在结束时恢复，不读取或改写凭据。

补充环境与解析证据：

- Windows 通过项目内 `uv python install 3.13.15 --no-bin` 安装解释器，输出实际耗时 15 分 03 秒；该耗时属于运行时下载准备，不代表依赖安装或产品性能。Node 官方 ZIP 共 37,618,919 字节，完整校验后实际运行 Node 24.21.0、npm 11.19.0。
- 后端在 `backend` 用隔离 uv/Python 执行 `uv lock --managed-python`，46.59 秒解析 24 条包记录（含本工程）；首轮 `uv sync --locked --managed-python` 触发 600 秒限制，已有完整下载保存在工程缓存，未记为安装成功。
- 前端在固定 Node 临时容器 `/work`（仅挂载清单暂存目录）执行 `npm install --package-lock-only --ignore-scripts`，首轮未成功结束；保留 npm 下载缓存后执行 `npm install --package-lock-only --ignore-scripts --prefer-offline`，49 秒成功，npm 报告审计 292 包、0 个已知漏洞。生成的 lockfileVersion 3 共 317 条记录，含不同平台的可选分发；每项直接依赖均与清单一致。这里只解析锁文件，后续 `npm ci` 正常执行必要安装脚本，不使用强制或忽略 peer 冲突参数。
- 已实际拉取 `python:3.13.15-slim-bookworm` 和 `node:24.21.0-bookworm-slim`，对应 digest 分别为 `sha256:2325bb286ec344af3e5898cc224b5844e2707ac6e26b1632516fd3edc84a5e26`、`sha256:0e0ff40c39bc087845bfb27465a0df4ea419520094bc35842ff83dd8cbe6f9b6`。临时容器内实测 Node 24.21.0/npm 11.19.0；资源检查返回 NanoCpus=2000000000、Memory=2147483648、PidsLimit=256、PortBindings={}。
- Linux 首轮经 pip 准备 uv 未成功结束；随后尝试官方 uv 工具镜像也触发 600 秒拉取超时，未采用该镜像。最终入口改为 `python -X utf8 scripts/prepare_toolchain.py --linux-uv`，复用有界续传和完整 SHA-256 校验准备官方 PyPI 的同版本 Linux 分发；安装与检查预算不因此放宽。

前端实际检查（Windows 工作目录 `F:\Program\Fall_Campus_Recruitment\frontend`；Linux 为固定 Node 镜像内的 `/work`，只复制工具文件，重新创建 `node_modules`）：

| 实际命令 | Windows 结果 | Linux 结果 |
| --- | --- | --- |
| `npm ci` | 通过；安装 291 包，约 6 分钟，审计 292 包、0 个已知漏洞 | 通过；安装 291 包，约 2 分钟，审计 292 包、0 个已知漏洞 |
| `npm ls --all` | 退出码 0，完整输出保存在 `.runtime/frontend-windows-dependencies.log` | 退出码 0；未安装项仅为非本平台或未启用功能的 optional 依赖 |
| `npm run verify:versions` | 通过；全部直接依赖、Node/npm、清单和锁文件一致；负向检查识别 ESLint 未定义名称和 TypeScript 类型错误 | 同样通过 |
| `npm run typecheck` | 失败，退出码 2：image 与 picker 的两处 TS2430 | 复现相同两处 TS2430 |
| `npm run lint` | 通过 | 通过 |
| `npm run format:check` | 通过 | 通过 |
| `npm run test -- --run` | 2 项通过，Vitest 总时长 5.93 秒 | 2 项通过，总时长 1.96 秒 |
| `npm run build:tooling` | 通过，Vite 报告 291 ms | 通过，Vite 报告 511 ms |

Windows 上的 npm 均使用 `.runtime/tools/node-v24.21.0-win-x64/node.exe` 执行同目录 `node_modules/npm/bin/npm-cli.js`，并仅为当前进程补充该 Node 的 PATH；没有执行 npm 输出中建议的全局升级。格式准备实际执行 `node node_modules/prettier/bin/prettier.cjs --write .`，只处理新建前端工程文件，`package-lock.json` 未改变。

Linux 独立前端检查日志为 `.runtime/frontend-linux-independent.log`。容器命令保持 `--rm --cpus 2 --memory 2g --pids-limit 256`、无端口映射；工具源码只读挂载至 `/input` 后复制到 `/work`，`timeout 600s npm ci` 后在 `timeout 300s sh -ec` 中逐项执行上表检查。为缩短网络下载，下载缓存从 Windows `_cacache` 复制到 Linux 缓存；`npm ci` 仍执行完整性检查和平台选择，不共享 `node_modules`。因此这不是无缓存网络环境的耗时基准。

前端本机安装文件逻辑大小为 229,754,818 字节（219.11 MiB，含开发工具）；Linux `du -sk node_modules` 为 313,008 KiB（磁盘块口径，不能直接与 Windows 逻辑字节比较）。两个平台工具构建结果同为 1,027.53 kB、gzip 273.09 kB，库构建将 React/React DOM 外置；这不是完整产品构建大小，也不是性能验收。

确定阻塞：`@rc-component/image@1.10.0` 与 `@rc-component/picker@1.12.2` 的声明继承不兼容，详见前端规范 1.3。保留 `strict: true`、`skipLibCheck: false`，不篡改第三方类型或通过忽略检查制造成功；M1-T01 标记受阻。后端另有安装超时阻塞，结果如下。AT-02、AT-20、AT-24、AT-25 未执行，本地配置和预算尚未由产品实现强制执行。

后端与总入口的最终结果：

| 工作目录 | 实际命令 | 观察结果 |
| --- | --- | --- |
| 根目录 | `pwsh -NoProfile -File ./scripts/check-toolchain.ps1 -Platform Windows` | 失败；uv 版本和 `uv lock --check` 通过，`uv sync --locked --managed-python` 在 600.09 秒后被包装器终止，报告内部退出码 -1；锁文件前后哈希相同 |
| 根目录 | `pwsh -NoProfile -File ./scripts/check-toolchain.ps1 -Platform Linux` | 首次退出码 2，`sh: 1: set: Illegal option -`；确认来自 CRLF，统一传给 sh 的换行符后重跑，进入实际安装阶段。重跑在 600.89 秒后返回 124，安装未完成；锁文件前后哈希相同 |
| 根目录 | `./backend/.venv/Scripts/python.exe --version`；固定 Python 镜像内 `python --version`、已校验 Linux uv 的 `--version` | Windows 与 Linux 的 Python 均实际报告 3.13.15；Linux uv 实际报告 0.12.19，Windows uv 同版本已核对 |
| 根目录 | `python --version`、`uv --version`、`node --version`、`npm --version` | 全局版本仍为 3.13.13、0.11.26、24.14.0、11.9.0 |
| 根目录 | `docker ps -a --filter 'name=m1-' --format '{{.Names}} {{.Status}}'`（使用安装目录 CLI） | 无本次临时容器残留 |

Windows 后端安装共尝试三次，均受 600 秒期限限制；第二次实际命令为 `uv sync --locked --managed-python --verbose`，仅为当前进程设置 `UV_HTTP_TIMEOUT=120`、`UV_CONCURRENT_DOWNLOADS=3`，未改变锁定版本。最终 Windows 及 Linux 输出均停留在 Django、mypy、Ruff 的下载阶段，不能宣称已安装或兼容通过；未放宽总期限、未忽略错误。后端虚拟环境为未完成状态，不把磁盘占用当成有效安装体积。

因此以下后端检查**未执行/未验证**（工作目录为 `backend` 或 Linux `/work`）：`uv pip check`、`uv run --locked python tooling/check_versions.py`、`uv run --locked ruff check .`、`uv run --locked ruff format --check .`、`uv run --locked mypy tooling tests`、`uv run --locked pytest -q`。脚本在安装失败后停止；前端结果来自前述独立检查，不能误记为总入口通过。Python 语法与 7 项标准库下载器测试通过，不替代这些依赖工具检查。

脱敏证据：Windows 总入口为 `.runtime/toolchain-windows-f194d39616eb4cfda03dbe1d28ddf7e7/result.json`；Linux 最终入口为 `.runtime/toolchain-linux-087785f30b0647dc90256dfce3a79868/result.json`，均含实际参数、工作目录、退出码、耗时和锁文件前后摘要，`succeeded` 均为 false。CRLF 失败保存在 `.runtime/toolchain-linux-d1073b896b6c4936b514288b6dcaae95`。这些是可清理的本地验证产物，长期结论仍只维护在本文。

首次验收时的锁文件 SHA-256（历史记录；修复后的摘要见下节）：

| 文件 | SHA-256 |
| --- | --- |
| backend/uv.lock | 4f6179825a927d9651299cece7ec38abddd6503ef8a3bfb28e7beb178e07d12b |
| frontend/package-lock.json | e113fbd1be7cafdc1ec9d1ddc644d54f732a42ae3b33cd2fc979cbbcdb39911b |

工具分发摘要：Windows uv wheel 为 `dcbc531a96762569bbfe9639b4f45f00aabff51f427540711f63e7c23f225fdf`；Linux uv wheel 为 `a63d18a0aa38ee9f21a5406afbbaeb41303bcd954be9d6b7c1b95ac275e53958`；Windows Node ZIP 为 `158f7685b44de51f6c0df1d153526cbcd3e1bc739a8dfc607721cef75de9e541`，均与官方记录比对后才使用。Python 由固定 uv 的受管解释器机制准备，另行运行核对实际版本，没有将解释器安装消息直接当作框架测试结果。

首次验收的恢复条件是解决声明兼容问题和下载阻塞，再重跑两端完整入口。用户随后明确选择最小声明补丁，以及单独计时的官方 wheel 下载准备；缓存安装预算仍为 600 秒。修复进展见下节，首次失败记录不作为当前通过证据。

最终审阅在根目录通过标准输入执行 `python -X utf8 -`：核对 35 个工程文件（25 个新增、6 个原有文件修改、4 个原文档保留）、UTF-8、Python 语法、Markdown 表格/围栏、80 处本地链接、直接依赖与锁文件、配置名称/安全占位值/预算、18 个任务状态及失败报告的前后哈希；检查通过。再次运行 `git status --short --branch` 仍返回 `not a git repository`，这是原有环境事实。下载器最终 7 项测试通过；后端 Ruff/mypy/pytest 仍未验证。

最终检查入口把上述已实测 Python/Node 镜像 digest 固定为引用；分别执行 `docker pull --platform linux/amd64 python@sha256:2325bb286ec344af3e5898cc224b5844e2707ac6e26b1632516fd3edc84a5e26` 和 `docker pull --platform linux/amd64 node@sha256:0e0ff40c39bc087845bfb27465a0df4ea419520094bc35842ff83dd8cbe6f9b6`，均确认本地镜像已是该内容。此项只核对不可变镜像引用，不重复或冒称依赖安装检查通过。

最终同步范围为根指令、阶段计划、前后端规范、结构及路线图；产品需求、API 清单、API 契约和任务提示词逐字节保留。没有新增平行进度或独立记忆系统，M1-T02 至 M5 的其余 17 个任务保持未开始。

### M1-T01 阻断修复验收（2026-09-28）

用户明确选择最小类型补丁及单独计时的官方 wheel 缓存准备。保留 React、Ant Design、TypeScript、Python、Django 及所有依赖版本；npm 锁只增加根包 `hasInstallScript` 标记。补丁清单按项目规则使用 snake_case，记录四个声明文件的原始与修复后摘要；不改变 JavaScript 运行逻辑、严格检查设置或产品配置预算。

修复期间实际检查：

| 工作目录 | 实际命令或操作 | 观察结果 |
| --- | --- | --- |
| 根目录 | `python -X utf8 -m unittest discover -s scripts -p test_prepare*.py -v` | 18 项通过；覆盖来源、重试期限、大小、截断、续传、摘要及缓存复用 |
| frontend | `node --test --test-concurrency=1 tooling/*.test.mjs`；总入口执行等价 `npm run test:tooling` | 10 项通过；合法与非法声明输入、首次/重复应用、未知版本/摘要/文件、目标摘要及路径拒绝 |
| frontend | 固定 Node 执行 `node_modules/typescript/bin/tsc --noEmit` | 实际原工程严格类型检查通过；不是内存替换或关闭声明检查 |
| frontend | 固定 Node/npm 执行 `npm ci` | 新建 node_modules 后安装钩子自动修复四处声明，安装 291 包；无新增依赖 |
| 根目录 | 新建临时虚拟环境，用固定 uv 执行 `pip sync --no-index --offline --find-links … --require-hashes --only-binary :all: …` | 缺失 wheel 与修改过的 wheel 均返回 1；后者明确 `Hash mismatch`，没有联网回退 |
| 根目录 | 从锁定且已校验的 Ruff wheel 提取同版本工具，执行 `ruff check backend`、`ruff format --check backend`、`ruff check --config backend/pyproject.toml scripts`、`ruff format --check --config backend/pyproject.toml scripts` | 后端样例与本次脚本的 lint/格式检查通过 |

Windows 最终总入口为 `pwsh -NoProfile -File ./scripts/check-toolchain.ps1 -Platform Windows -BackendInstallSource Wheelhouse`，工作目录是项目根目录。结果文件 `.runtime/toolchain-windows-36c26faccfcf43b4a163fbb6678c9ce0/result.json` 的 `succeeded` 为 true；其中后端子命令在 `backend` 执行，前端子命令在 `frontend` 执行：

- `uv lock --check`、新虚拟环境创建、带哈希 requirements 导出、离线 `uv pip sync`、`uv sync --locked --offline`、`uv pip check` 及真实版本核对全部通过。后端准备和安装子步骤合计约 2.32 秒；复用了已校验下载文件及 uv 本地缓存，不是冷缓存联网基准。
- `uv run --locked ruff check .`、`uv run --locked ruff format --check .`、`uv run --locked mypy tooling tests`、`uv run --locked pytest -q` 全部通过；mypy 检查 5 个源文件，pytest 8 项通过，包含真实 Django/DRF 字段边界和工具负向检查。
- `npm ci`、`npm ls --all`、`npm run verify:versions`、`npm run typecheck`、`npm run lint`、`npm run format:check`、`npm run test -- --run`、`npm run test:tooling`、`npm run build:tooling` 全部通过；分别 2 项组件测试和 10 项工具测试。npm ci 用时 17.49 秒，Vite 构建报告 300 ms。
- 新后端虚拟环境逻辑大小 106,827,946 字节，前端 node_modules 为 229,754,894 字节，工具构建输出 1,027,534 字节；不包含下载缓存，不代表未来产品部署体积。

开发过程中，类型回归样例最初因 Windows 路径形式和未公开的包内子路径而失败，修正为明确的声明文件引用后通过；未放宽类型约束。一次受限权限下版本检查返回 `EPERM`，以正常权限重跑通过。补丁异常包装补充 `cause` 后通过 ESLint；首次完整 Windows 验收通过后，为统一补丁清单字段命名再次运行上述最终入口。安装缺包/损坏拒绝证据位于 `.runtime/wheel-integrity-probe-1ca1e80a84f4412daad0dd8f37ac9c60/result.json`。

Linux 最终总入口为 `pwsh -NoProfile -File ./scripts/check-toolchain.ps1 -Platform Linux -BackendInstallSource Wheelhouse`，同样从项目根目录执行；容器内工作目录均为 `/work`。结果文件 `.runtime/toolchain-linux-7df2871d4c184cb8bbca2daf0fc0369a/result.json` 的 `succeeded` 为 true：

- 后端在固定 Python 镜像的新环境中离线安装 21 个包（Windows 为 23 个，差异来自 colorama/tzdata 的平台条件），完成相同版本、依赖、Ruff、mypy 和 8 项 pytest 检查。安装与检查合计 55.607 秒；uv 报告准备包 33.35 秒、安装 14.34 秒。虚拟环境磁盘块占用 147,656 KiB，不能与 Windows 逻辑字节数直接比较。
- 前端在固定 Node 镜像中全新 `npm ci`，安装钩子成功修复四处声明，全部版本及严格类型、lint、格式、2 项组件测试、10 项工具测试和构建通过。安装与检查合计 28.907 秒，npm 报告安装约 6 秒、审计 292 包且当时未报告已知漏洞；Vite 构建报告 444 ms。node_modules 磁盘块占用 313,008 KiB，工具构建输出与 Windows 一致。
- 对本次后端容器实际执行 `docker inspect`，返回 NanoCpus=2000000000、Memory=2147483648、PidsLimit=256、NetworkMode=none、PortBindings={}。缓存只读挂载；检查完成后 `docker ps -a --filter name=m1- --format '{{.Names}} {{.Status}}'` 无残留。

根目录实际执行 `python -u -X utf8 scripts/prepare_backend_wheels.py --platform all`，27 个唯一官方 wheel 全部校验完成，首次下载准备耗时 1313.8 秒（约 21 分 54 秒），在 1800 秒整轮预算内；部分大包通过第二次有界续传完成。Windows 文件齐备时另执行 `--platform windows`，校验缓存耗时 1.84 秒。最终脚本再次执行 `--platform all`，完整缓存复核耗时 2.68 秒。Windows 和 Linux 的参考解释器均实际报告 Python 3.13.15；全部缓存只由当前锁文件派生。原下载日志个别子进程中文因 Windows 编码显示异常，已显式使用 UTF-8 修复，最终缓存复核日志正常；摘要与退出码记录不受影响。

两端总入口检查前后，下列摘要一致；后端锁与修复前相同，前端锁的差异仅为根包安装脚本标记：

| 文件 | 修复后 SHA-256 |
| --- | --- |
| backend/uv.lock | 4f6179825a927d9651299cece7ec38abddd6503ef8a3bfb28e7beb178e07d12b |
| frontend/package-lock.json | 4f0fee2094bbca044643afd18aa05053142ed07ff45bdba24ae7a9c1061ea5c9 |
| frontend/tooling/type-patches.json | 3eedb7bb8bb20512d9ea2edce89bc46cb6379ee52891ded9f9fe851b69e15b7c |

验收结论：M1-T01 已完成，兼容范围为已记录的 Windows x64 与 Linux amd64 工具环境、受控声明补丁及官方 wheel 缓存安装流程。下载准备与安装分别计时，不宣称冷缓存联网安装能在 600 秒内完成；底层网络缓慢原因未单独定位。后续依赖升级必须重新验证补丁，Django 类型存根仍仅声明部分支持；工具用例不代表完整 ORM 或浏览器产品兼容性。AT-02、AT-20、AT-24、AT-25 仍未执行，资源配置只固定基线，产品强制执行留给所属任务。

最终全局 Python/uv/Node/npm 仍为 3.13.13/0.11.26/24.14.0/11.9.0；没有全局安装或升级，没有初始化 Git。共新增 6 个文件、修改 10 个文件，原 35 个文件均保留；需求、API 清单、API 契约、任务提示词、根指令及路线图保持不变。通过修改前快照逐项审阅差异与新增源码，最终文件、命令、依赖和文档一致；M1-T02 及其他任务未开始。

### M1-T02 基础工程验收（2026-09-29）

本次以实际目录、根 AGENTS、九份项目文档和依赖配置重新核验，未沿用上一会话结论。M1-T01 的锁文件、类型补丁和既有工具文件均在；当前目录仍不是 Git 仓库。修改前 41 个工程文件的文本与摘要保存在被忽略的 `.runtime/m1-t02-baseline`，没有初始化仓库、覆盖用户文件或删除原文件。

范围澄清：原 API 清单只有任务查询入口，却要求 M1-T02 能提交最小任务。用户明确选择“固定链路检查接口与页面按钮”。据此增加 API-36 `POST /api/v1/system-checks/` 和 API-37 `GET /api/v1/system-checks/{check_id}/`；仅接收空 JSON 对象，不接受命令、源码或业务字段，不提供通用任务创建。连同 CSRF、任务列表和任务详情共实现 5 个 HTTP 操作。本任务所需 Schema 导出和类型生成是遵守契约来源规则的最小入口，不代表完成 M1-T04。

实现与取舍：PostgreSQL 保存任务、幂等键和固定检查结果，Redis 只负责投递。事务提交后发布，Worker 原子领取，结果与成功状态同事务保存；独立核对进程每 5 秒处理期限，拒绝失效领取的迟到结果。发布失败留痕，未知提交复用原键，不自动重投。默认单 Worker 槽位、排队和执行各 300 秒。标准 Django CSRF 检查显式覆盖匿名 DRF 写请求，并校验精确 Host/Origin；只有前端 Nginx 发布 `127.0.0.1:5173`。凭据仅由初始化容器生成到私有卷，验收未读取、输出或记录其内容。

依赖只增加本任务所需的 Celery、PostgreSQL 驱动、Gunicorn、drf-spectacular、TanStack Query 和本地类型生成器。最终生成器为 `@hey-api/openapi-ts@0.99.0`，仅对其解析器子树将 `js-yaml` 固定为已修复版本 4.3.2。逐包比较前后锁文件，所有原有包版本保持不变，原类型补丁文件逐字节不变。用途、许可证、维护来源及兼容边界分别同步前后端规范；没有全局安装或升级。

参考环境为 Windows x64、PowerShell、Docker Desktop Linux amd64 引擎；实测 Engine 29.4.0、Compose 5.1.1，Python 3.13.15、uv 0.12.19、Node 24.21.0、npm 11.19.0。基础镜像固定摘要，应用服务仅在本地 Compose 项目 `learning-lab` 运行；没有发布镜像、部署远程环境、运行导入代码或模型外发。工作目录及命令如下，表中的根目录均为 `F:\Program\Fall_Campus_Recruitment`：

| 工作目录 | 实际命令或操作 | 最终观察结果 |
| --- | --- | --- |
| 根目录 | `git status --short --branch` | `fatal: not a git repository`；为原有事实，不初始化 Git |
| 根目录 | `docker compose up -d --build --wait --wait-timeout 90` | 镜像构建、初始化、迁移和启动通过；前端容器全新 `npm ci` 自动应用原四处声明补丁，构建通过 |
| 根目录 | `docker compose run --rm --no-deps api python -m pytest apps/jobs/tests tests --ds=config.settings.local -q -p no:cacheprovider` | 真实 PostgreSQL：65 项通过，最终一次 3.94 秒；覆盖提交/重放/冲突、并发、发布失败、领取、超时、迟到结果、分页、来源/CSRF、输入、配置和契约 |
| 根目录 | `docker compose exec -T api python manage.py check` | 0 个问题 |
| backend | `python -m ruff check .`；`python -m ruff format --check .` | lint 通过；36 个文件格式通过 |
| backend | `python -m mypy config common apps tests --no-incremental` | 31 个源文件通过；保留严格检查，仅对无类型元数据的 Celery/Kombu 导入设置有限边界 |
| backend | `python manage.py makemigrations --check --dry-run --settings config.settings.test` | `No changes detected` |
| backend | `python manage.py spectacular --settings config.settings.test --file ../contracts/openapi.yaml --validate --fail-on-warn` | 无警告通过；重新生成前后 SHA-256 相同，5 个操作与实现一致 |
| frontend | `npm run api:types`；`node tooling/generate-api-types.mjs` | 本地 Schema 生成声明通过；最终重新生成前后 SHA-256 相同 |
| frontend | `npm run verify:versions`、`npm run typecheck`、`npm run lint`、`npm run format:check` | 全部通过，严格 TypeScript 与 `skipLibCheck: false` 保持原样 |
| frontend | `npm run test -- --run`；`npm run test:tooling` | 4 个文件共 9 项组件/请求测试通过；原声明补丁工具 10 项通过 |
| frontend | `npm run build`；`npm audit` | 构建通过，主要 JS 437.21 kB / gzip 143.62 kB；当次审计 0 个已知漏洞，不作为未来无漏洞保证 |
| 根目录 | `python -X utf8 scripts/check_local_stack.py` | 18 项真实 HTTP/网络检查通过；非回环连接拒绝，合法匿名提交完成，缺失/错误 CSRF、缺失/跨站/不同端口 Origin、非法 Host、伪造转发头拒绝，同键重放和结果恢复通过 |
| 根目录 | `docker compose -f compose.yaml -f infra/docker/compose.verify.yaml up -d --wait --wait-timeout 90`；`python -X utf8 scripts/check_local_stack.py --faults` | 27 项检查通过；真实停止 Redis 后返回 503 并留痕，重复键不重投；停止 Worker 后独立核对终结排队，恢复后迟到执行不覆盖；停止 PostgreSQL 后返回可读 503；整组重启后结果仍在 |
| 根目录 | `docker compose up -d --build --wait --wait-timeout 90`；`docker compose exec -T api python -c 'import django; django.setup(); from django.conf import settings; print("Task budgets:",settings.JOB_QUEUE_TIMEOUT_SECONDS,settings.JOB_EXECUTION_TIMEOUT_SECONDS)'` | 故障验收结束后恢复正常配置，实际输出 `Task budgets: 300 300`，并完成表中的最终后端/HTTP复验 |
| 浏览器 | 在 `http://127.0.0.1:5173/` 点击“开始基础检查”、查看结果、刷新页面 | 真实任务完成，结果可读，刷新后记录保留；最终页面显示成功与故障历史，没有浏览器错误日志。截图 `.runtime/m1-t02-browser.png` |

上述 backend 质量命令的 `python` 实际为 `.runtime/m1-t02-venv/Scripts/python.exe`；npm/node 实际为 `.runtime/tools/node-v24.21.0-win-x64/node.exe` 及其同目录 npm 入口，仅为当前进程补入 Node/Docker PATH。根目录的标准库 HTTP 脚本使用现有宿主 Python，不安装第三方包。新增验收脚本和凭据初始化脚本另经 Ruff lint/格式检查通过。

最终 Linux 复制白名单修复的独立验证：在根目录用 PowerShell Parser 解析 `scripts/check-toolchain.ps1`，从 AST 读取两份实际名单并按相同后缀规则建立 `.runtime/m1-t02-copy-verification`，后端 39 个文件、前端 30 个文件，无秘密/缓存。两个临时容器均使用 `--rm --cpus 2 --memory 2g --pids-limit 256`、只读输入挂载、无宿主端口，完成后自动删除；此项没有重跑完整 wheel 下载准备总入口。

- 后端使用已构建 `learning-lab-backend:m1-t02`，另加 `--network none --read-only --tmpfs /tmp`，副本工作目录 `/tmp/work`。实际依次运行 `python -m ruff check .`、`python -m ruff format --check .`、`python -m mypy tooling tests --no-incremental`、`python -m pytest tests --ds=tooling.settings -q -p no:cacheprovider`；36 个文件格式通过、6 个源文件类型通过、27 项测试通过（与上述 65 项中的工具/配置用例重叠）。
- 前端使用已固定摘要的 Node 24.21.0 镜像，副本工作目录 `/work`。实际依次运行 `npm ci`、`npm run verify:versions`、`npm run typecheck`、`npm run lint`、`npm run format:check`、`npm run test -- --run`、`npm run test:tooling`、`npm run build:tooling`、`npm run build`、`npm run format:check`；全部通过。新安装 337 个包、审计 338 个包，原四处补丁自动应用；组件/请求 9 项、补丁工具 10 项通过，构建产物与 Windows 一致。
- 本地前端以 `docker compose up -d --build --no-deps --wait --wait-timeout 90 frontend` 更新，浏览器再次读取已有任务结果；后端与数据库保持运行。

开发中的失败及处理保留如下，不用最终成功覆盖失败事实：

- 受限权限下 npm 缓存缺包、Vitest `spawn EPERM`、Docker 管道访问受限；使用正常权限与项目隔离依赖后通过。Docker CLI/凭据助手不在 PATH，通过当前进程 PATH 修正；没有修改凭据或全局配置。
- 首次数据库套件 7 项失败、54 项通过：6 项来源用例的测试客户端默认头覆盖了单次请求头，修正测试构造后验证真实拒绝；1 项原工具负向检查因只读镜像缓存位置不可写失败，将 mypy 缓存放到 `/tmp` 后通过。未弱化断言或类型约束。
- 新契约测试发现空对象请求在生成器默认行为下未标记必填；为固定检查添加有限 Schema 扩展，之后 65 项全部通过，Schema 零警告。首次锁文件格式检查失败，仅格式化本次已变动的锁文件后通过。
- 类型生成器选型期间发现新增解析器的 YAML 传递漏洞，限定该新子树的修复版本；最终审计通过，既有依赖版本未改变。没有对无关依赖执行自动修复或升级。
- 最终审阅修复了数组形式状态被字符串转换接受的问题，新增非法数组输入断言后 9 项前端测试通过。构建后格式检查误扫 `dist`，新增前端 `.prettierignore` 排除构建/覆盖率产物；没有修改生成产物来满足检查。旧 Linux 工具脚本的复制白名单会漏掉新增配置和源码，已仅补齐本任务必要文件与 CSS 后缀；未改下载、安装、预算或检查顺序。

脱敏证据为 `.runtime/m1-t02-http-faults.json`（27 项故障验收全部为 true）、`.runtime/m1-t02-http-verification.json`（18 项最终复验，`succeeded: true`）、`.runtime/m1-t02-browser.png` 与 `.runtime/m1-t02-result.png` 页面截图及修改前快照。这些是可清理本地验收产物，任务进度与长期结论只维护在本文。故障测试创建的成功/失败检查历史保留，数据卷未删除；交付时本地服务运行中。

验收结论：M1-T02 已完成，AT-24 及固定检查所需的 FR-08/NFR-03 行为已验证。技术知识点是“持久化事实与投递通道分工”、事务外投递的故障窗口、幂等领取与迟到结果约束，以及匿名同源访问仍需 CSRF。手工复核可点击“开始基础检查”，等待完成、查看结果再刷新，检查同一任务标识及结果仍在。完整业务重试、快照/分析恢复、教学示例、全阶段契约和容量基准属于后续任务，本次没有将完整 AT-18 至 AT-20、AT-23、AT-25 标记通过。验证范围为 Windows x64 宿主与 Linux amd64 容器，未验证 ARM、公开网络部署或生产容量。

本次文件范围（共 55 个新增、17 个修改，无删除；下列路径均相对项目根目录）：

| 变更 | 文件 | 用途 |
| --- | --- | --- |
| 新增 | `README.md`、`.dockerignore`、`compose.yaml` | 启动/验收入口、构建上下文和本地服务组合 |
| 新增 | `backend/manage.py`；`backend/config/celery.py`、`environment.py`、`urls.py`、`wsgi.py`；`backend/config/settings/base.py`、`local.py`、`test.py` | Django/Celery 入口、配置校验及隔离测试配置 |
| 新增 | `backend/common/errors.py`、`middleware.py` | 统一错误、匿名来源/CSRF 保护 |
| 新增 | `backend/apps/jobs/models.py`、`services.py`、`tasks.py`、`api/schema.py`、`api/serializers.py`、`api/views.py`、`management/commands/reconcile_jobs.py`、`migrations/0001_initial.py` | 固定任务契约、持久化、执行、期限核对与初始迁移 |
| 新增 | `backend/apps/jobs/tests/test_jobs.py`、`test_contract.py`；`backend/tests/test_environment.py` | 真实数据库、并发、错误、安全与配置/契约回归 |
| 新增 | `backend/apps/__init__.py`、`backend/apps/jobs/__init__.py`、`backend/apps/jobs/api/__init__.py`、`backend/apps/jobs/management/__init__.py`、`backend/apps/jobs/management/commands/__init__.py`、`backend/apps/jobs/migrations/__init__.py`、`backend/apps/jobs/tests/__init__.py`、`backend/common/__init__.py`、`backend/config/__init__.py`、`backend/config/settings/__init__.py` | 必要 Python 包边界 |
| 新增 | `contracts/openapi.yaml`；`frontend/tooling/generate-api-types.mjs`；`frontend/src/shared/api/generated/schema.d.ts` | 本任务有限契约及可重复的本地声明生成 |
| 新增 | `frontend/.prettierignore`、`index.html`、`vite.config.ts`、`src/vite-env.d.ts`、`src/app/main.tsx`、`src/app/global.css`、`src/features/jobs/JobsPage.tsx`、`src/features/jobs/api/jobs-api.ts`、`src/shared/api/client.ts` | 页面、类型化请求、轮询、未知提交恢复及构建产物格式排除 |
| 新增 | `frontend/src/features/jobs/JobsPage.test.tsx`、`frontend/src/features/jobs/api/jobs-api.test.ts`、`frontend/src/shared/api/client.test.ts` | 页面及请求边界测试 |
| 新增 | `infra/docker/backend.Dockerfile`、`frontend.Dockerfile`、`compose.verify.yaml`、`initialize-secrets.py`；`infra/nginx/default.conf.template`；`scripts/check_local_stack.py` | 固定镜像构建、私有凭据初始化、同源代理与真实故障验收 |
| 修改 | `backend/pyproject.toml`、`backend/uv.lock`；`frontend/package.json`、`package-lock.json`、`tsconfig.json`、`vitest.config.ts`；`.env.example` | 必要依赖、类型/测试覆盖及安全配置说明 |
| 修改 | `scripts/check-toolchain.ps1` | 补齐本任务新增配置、模块、页面和 CSS 的 Linux 验收复制白名单 |
| 修改 | `AGENTS.md`；`docs/requirements.md`、`phase-1-plan.md`、`roadmap.md`、`project-structure.md`、`api-catalog.md`、`api-conventions.md`、`backend-guidelines.md`、`frontend-guidelines.md` | 同步实际结构、当前边界、固定检查契约、依赖、命令和验收记录 |

项目记忆核对：未发现独立记忆文件，沿用九份文档及 AGENTS。修正了 API 提交缺口、只描述工具工程的当前结构/运行状态，以及仅覆盖工具样例的类型检查描述；原历史验收记录原样保留，不当作本次证据。`docs/codex-task-prompt.md`、原类型补丁和下载准备脚本未修改。M1-T03 及其后的 16 个任务保持未开始，当前任务结束后停止。

最终文档/范围检查在根目录通过标准输入执行 `python -X utf8 -`：41 个原文件均保留，55 个新增、17 个修改、0 个删除；UTF-8、Python/JSON/TOML 语法、Markdown 围栏/表格、90 处本地链接与显式锚点、18 个任务状态通过；原有包版本全部一致。再次运行 `git status --short --branch` 仍返回非 Git 仓库。检查只读取工程文件，排除依赖、缓存、运行数据及敏感配置。

### M1-T03 独立教学示例验收（2026-09-29）

范围及前置：重新读取根 AGENTS、需求、阶段计划、结构、API 清单/规范、前后端规范及路线图。当前目录仍不是 Git 仓库；`examples/task-board` 起初不存在，文档“示例未开始”与文件相符。实际核验工作台 API、PostgreSQL、Redis、Worker、核对进程均运行；隔离 Python 3.13.15、Django 5.2.17、DRF 3.18.1、Node 24.21.0 与前置记录一致。没有重复实施 M1-T01/02、初始化 Git 或推进 M1-T04。

示例版本 `task-board/1.0.0` 是教学内容版本，不是工作台产品版本。仅提供独立 CSRF、任务列表及创建三个操作；源代码唯一位于 `examples/task-board`。独立清单/锁、PostgreSQL 数据与秘密卷、网络和回环 5174 入口保证与工作台隔离。根 Compose 中 profile 默认不启用，通过明确指定 `task-board-frontend` 启动其必要依赖。代码不执行导入项目、不外发模型、不创建实验接口。

主要取舍：保留简单的 View/Serializer/service/ORM 和 React feature 边界；不引入队列或额外框架。复用已验证版本与镜像摘要，示例后端去掉 Celery/Redis，示例前端将已有 Vite 8.3.1 显式列为直接构建依赖并保留原声明补丁。既有工作台清单、锁、代码与契约逐字节未变；示例共享包版本与原锁一致。新的重复配置只为独立工程服务，不在运行期导入工作台模块。

标题先规范化再校验，HTTP 校验给出字段错误，数据库非空白约束与幂等唯一键负责存储完整性。新建 201，同键同标题返回 200/原记录，同键不同标题 409；不同键允许同名任务。Cookie 按主机而非端口隔离，故示例使用独立 Cookie 名，同时保持 Host/Origin/标准 Django CSRF。未知提交不自动重发，只保存随机会话键；刷新后重填原标题，恢复校验失败或冲突不丢弃原键。

人工基准 `testdata/analysis/task-board-create.json` 共 12 个节点、12 条关系，含版本、文件 SHA-256、行号和锚点。源码事实、静态 HTTP 匹配、框架回调/ORM 推导分开，框架行为不伪造示例源码位置。标注由编码代理逐项维护核对，不声称用户独立复核或解析器识别成功；当前无真实导入快照。引用检查覆盖摘要漂移、越界路径、行号越界、悬空关系和缺失框架依据。

参考环境：Windows x64、Docker Desktop Linux amd64；沿用固定 Python/Node/数据库/代理镜像。下表“根目录”为 `F:\Program\Fall_Campus_Recruitment`，“示例后端”为其 `examples/task-board/backend`，“示例前端”为其 `examples/task-board/frontend`。质量检查 `python` 为根 `.runtime/m1-t02-venv/Scripts/python.exe`，Node/npm 为 `.runtime/tools/node-v24.21.0-win-x64`；只修改当前进程 PATH，未安装全局工具。

| 工作目录 | 实际命令或操作 | 观察结果 |
| --- | --- | --- |
| 根目录 | `Get-Location`；`git status --short`；`git rev-parse --show-toplevel` | 路径正确；两个 Git 命令均返回 `not a git repository`，未初始化 |
| 根目录 | `docker compose ps --format '{{.Service}} {{.State}} {{.Health}}'`；隔离解释器版本检查 | 前置服务健康、工具版本一致；最终工作台和示例均运行 |
| 根目录 | `uv lock --offline --project examples/task-board/backend --python .runtime/m1-t02-venv/Scripts/python.exe --cache-dir .runtime/uv-cache` | 示例独立锁解析 36 个包；去掉无关队列依赖，保留共用包版本 |
| 示例前端 | `npm install --package-lock-only --offline --ignore-scripts --no-audit`；`npm ci --offline --no-audit` | 独立锁与安装成功，337 个包，四处原声明补丁通过；未改工作台依赖 |
| 根目录 | `docker compose --profile task-board config --quiet`；`docker compose build task-board-api task-board-frontend`；`docker compose up -d --wait --wait-timeout 90 task-board-frontend` | 配置、构建、迁移、独立示例启动通过。修正锁路径后重新构建前端，容器 npm ci 审计当次为 0 个已知漏洞 |
| 根目录 | `docker compose run --rm --no-deps task-board-api python -m pytest -q -p no:cacheprovider` | 真实 PostgreSQL 40 项通过；包含正常/缺失/空/纯空白、Unicode、非法类型/字段/长度、重放/冲突/并发、数据库约束、分页、来源与契约 |
| 根目录 | `docker compose exec -T task-board-api python manage.py check` | 0 个问题 |
| 示例后端 | `python -m ruff check .`；`python -m ruff format --check .`；`python -m mypy config common apps --no-incremental` | lint、24 个 Python 文件格式及 23 个源文件严格类型检查通过 |
| 示例后端 | `python manage.py makemigrations --check --dry-run --settings config.settings.test`；`python manage.py spectacular --settings config.settings.test --file ../contracts/openapi.yaml --validate --fail-on-warn`；`uv lock --check --offline --python F:/Program/Fall_Campus_Recruitment/.runtime/m1-t02-venv/Scripts/python.exe --cache-dir F:/Program/Fall_Campus_Recruitment/.runtime/uv-cache` | 无迁移漂移；三个操作 Schema 无警告，重新导出 SHA-256 相同；锁检查通过 |
| 示例前端 | `npm run api:types`；`npm ls --all --depth=0` | 类型生成通过，前后 SHA-256 相同；直接依赖完整、版本与清单一致 |
| 示例前端 | `npm run typecheck`；`npm run lint`；`npm run format:check`；`npm run test -- --run`；`npm run test:tooling`；`npm run build` | 严格类型/lint/格式通过；最终组件与请求 15 项通过，补丁工具 10 项通过；构建通过，JS 688.01 kB / gzip 222.85 kB，有大包提示 |
| 根目录 | `python -X utf8 scripts/check_task_board.py --restart` | 最终 15 项真实 HTTP 检查通过；四种输入实际响应/写入差值、重放、冲突、来源拒绝及示例 API/数据库重启持久化均通过 |
| 根目录 | `python -X utf8 scripts/check_task_board_annotations.py`；`python -X utf8 -m unittest discover -s scripts -p test_check_task_board_annotations.py -v` | 12 个节点/12 条关系引用一致；6 项引用完整性测试通过，不代表关系分析器准确率 |
| 根目录 | `python -m ruff check --config backend/pyproject.toml scripts/check_task_board.py scripts/check_task_board_annotations.py scripts/test_check_task_board_annotations.py`；相同文件的 `ruff format --check` | 3 个本任务脚本 lint/格式通过 |
| 浏览器 | 访问 5174，以键盘提交正常标题、空标题、纯空白标题，刷新；检查窄屏与控制台 | 正常输入显示真实记录；空/空白出现错误且数量不增加；刷新后记录保持。窄屏实际 DOM 宽度 375，与内容宽度相同，无横向溢出；控制台无 warn/error |
| 根目录 | `docker compose build task-board-frontend`；`docker compose up -d --no-deps --wait --wait-timeout 90 task-board-frontend` | 最终恢复修复已更新到示例服务，浏览器刷新使用最终构建；工作台未重建或重启 |

过程中出现的失败及修复：

- 首次 Docker 只读检查因沙箱管道权限失败；正常权限检查通过，没有调整服务权限或关闭安全检查。
- 初次前端类型检查缺少 Vite CSS 模块声明；补齐示例 `vite-env.d.ts` 后通过。初次后端类型检查发现 Serializer 的 Any 返回和无类型第三方生成入口；显式声明结果类型，仅对该第三方调用作精确例外，保留业务严格检查。格式问题只修复新增示例文件。
- 首轮 7 项组件测试因 jsdom 缺少 ResizeObserver 失败；补标准浏览器 API 的测试替身后通过，真实浏览器另外验证。请求测试使用替身覆盖异常，不冒充真实持久化证据。
- 构建审阅发现示例 Dockerfile 引用了工作台锁路径，修正为示例独立锁后重建通过；工作台原文件未修改。
- 第一次 HTTP 重启检查遇到代理暂时返回 HTML，JSON 解析失败；仅在重启的有界恢复窗口等待该临时响应，最终重跑通过，未伪造结果。
- 最终审阅发现恢复请求参数被拒绝时不能据此清除旧键；修复后新增 400/409 恢复回归，最终 15 项前端测试通过。

证据：修改前 96 个非敏感工程文件的基线和摘要位于 `.runtime/m1-t03-baseline`；HTTP 实际响应与差值位于 `.runtime/m1-t03-http-verification.json`，桌面/窄屏截图为 `.runtime/m1-t03-browser.png`、`.runtime/m1-t03-browser-narrow.png`。这些是可清理的本地证据，不是平行进度或业务事实来源。验收创建的 3 条无敏感示例任务保留；未清理数据卷、运行导入代码、模型外发或执行 Git 写操作。

结论：M1-T03 退出条件满足。AT-04/07 仅准备 path/include/as_view、fetch/本地调用基准；Router、axios、实际分析器与完整识别验收仍待 M2/M3。AT-16 的示例输入/真实响应/写入差值已验证，工作台实验编排、预测界面和按运行隔离属于 M5，未标记完整 AT-16/22 或 M1 里程碑完成。JS 大包提示保留，未做性能重构；不声称完成 ARM、公网、多用户、容量或干净环境全流程验收。

知识与手工复核：HTTP 校验和数据库约束分工、唯一键下的幂等并发、Cookie 与 Origin 的不同隔离维度、静态关系和真实观测的区别。可在任务簿创建一条正常标题，刷新核对相同 ID；再提交纯空格确认报错且列表数量不变。

项目记忆同步：未发现独立记忆文件，沿用原文档，未建立新进度系统。初始文档与已核验实现无冲突；新增示例后更新 AGENTS、README、结构、API 清单/规范、前后端规范和路线图的现状说明，任务状态只改本文。需求边界未变，`requirements.md` 和提示词无需改动。其他 15 个编号任务保持未开始，当前任务结束后停止。

本次文件范围：62 个新增、11 个修改、0 个删除。下列路径均相对项目根目录；依赖安装、构建目录及 `.runtime` 审计证据不作为源码交付。

- 新增示例后端：`examples/task-board/backend/.dockerignore`、`examples/task-board/backend/.python-version`、`examples/task-board/backend/apps/__init__.py`、`examples/task-board/backend/apps/tasks/__init__.py`、`examples/task-board/backend/apps/tasks/api/__init__.py`、`examples/task-board/backend/apps/tasks/api/serializers.py`、`examples/task-board/backend/apps/tasks/api/urls.py`、`examples/task-board/backend/apps/tasks/api/views.py`、`examples/task-board/backend/apps/tasks/migrations/0001_initial.py`、`examples/task-board/backend/apps/tasks/migrations/__init__.py`、`examples/task-board/backend/apps/tasks/models.py`、`examples/task-board/backend/apps/tasks/services.py`、`examples/task-board/backend/apps/tasks/tests/__init__.py`、`examples/task-board/backend/apps/tasks/tests/test_contract.py`、`examples/task-board/backend/apps/tasks/tests/test_tasks.py`、`examples/task-board/backend/common/__init__.py`、`examples/task-board/backend/common/errors.py`、`examples/task-board/backend/common/middleware.py`、`examples/task-board/backend/config/__init__.py`、`examples/task-board/backend/config/settings/__init__.py`、`examples/task-board/backend/config/settings/base.py`、`examples/task-board/backend/config/settings/local.py`、`examples/task-board/backend/config/settings/test.py`、`examples/task-board/backend/config/urls.py`、`examples/task-board/backend/config/wsgi.py`、`examples/task-board/backend/manage.py`、`examples/task-board/backend/pyproject.toml`、`examples/task-board/backend/uv.lock`。

- 新增示例前端：`examples/task-board/frontend/.node-version`、`examples/task-board/frontend/.npmrc`、`examples/task-board/frontend/.prettierignore`、`examples/task-board/frontend/eslint.config.js`、`examples/task-board/frontend/index.html`、`examples/task-board/frontend/package-lock.json`、`examples/task-board/frontend/package.json`、`examples/task-board/frontend/prettier.config.mjs`、`examples/task-board/frontend/src/app/global.css`、`examples/task-board/frontend/src/app/main.tsx`、`examples/task-board/frontend/src/features/tasks/TaskBoard.test.tsx`、`examples/task-board/frontend/src/features/tasks/TaskBoard.tsx`、`examples/task-board/frontend/src/features/tasks/api/tasks-api.test.ts`、`examples/task-board/frontend/src/features/tasks/api/tasks-api.ts`、`examples/task-board/frontend/src/shared/api/client.ts`、`examples/task-board/frontend/src/shared/api/generated/schema.d.ts`、`examples/task-board/frontend/src/vite-env.d.ts`、`examples/task-board/frontend/tooling/apply-type-patches.mjs`、`examples/task-board/frontend/tooling/dependency-types.test.mjs`、`examples/task-board/frontend/tooling/generate-api-types.mjs`、`examples/task-board/frontend/tooling/type-patches.json`、`examples/task-board/frontend/tooling/type-patches.test.mjs`、`examples/task-board/frontend/tsconfig.json`、`examples/task-board/frontend/vite.config.ts`、`examples/task-board/frontend/vitest.config.ts`。

- 新增契约与说明：`examples/task-board/README.md`、`examples/task-board/contracts/openapi.yaml`。

- 新增标注、脚本与服务配置：`infra/docker/task-board-backend.Dockerfile`、`infra/docker/task-board-frontend.Dockerfile`、`infra/nginx/task-board.conf.template`、`scripts/check_task_board.py`、`scripts/check_task_board_annotations.py`、`scripts/test_check_task_board_annotations.py`、`testdata/analysis/task-board-create.json`。

- 修改现有文件：`.dockerignore`、`AGENTS.md`、`README.md`、`compose.yaml`、`docs/api-catalog.md`、`docs/api-conventions.md`、`docs/backend-guidelines.md`、`docs/frontend-guidelines.md`、`docs/phase-1-plan.md`、`docs/project-structure.md`、`docs/roadmap.md`。

最终审阅：在根目录以标准输入执行 `python -X utf8 -`，对照修改前摘要逐文件核对，96 个原工程文件全部保留，变更仅在上述范围。UTF-8、Python/JSON/TOML 语法、Markdown 围栏、103 处本地链接及 18 个任务状态通过；前后端共用依赖版本和工作台源码/契约摘要未变。最后 `git status --short --branch` 仍返回非 Git 仓库。完整文件审计与既有文件差异分别保存于 `.runtime/m1-t03-file-review.json`、`.runtime/m1-t03-existing.diff`，不建立平行任务状态。

<a id="m1-t04-verification"></a>
### M1-T04 全阶段契约与检查基线验收（2026-09-29）

范围与前置：重新核对根 AGENTS、九份项目文档、实际源文件和服务；`Get-Location` 为 `F:\Program\Fall_Campus_Recruitment`，`git status --short` 与最终 `git status --short --branch` 均返回 `not a git repository`。只读 Docker 状态显示工作台和示例前置服务健康，隔离 Python 3.13.15、Node 24.21.0 与已有工具记录一致。保留全部 158 个原工程文件，修改前非敏感基线位于 `.runtime/m1-t04-baseline`，未初始化 Git。

交付：API 清单 4.7 明确现有 8 个操作及 NFR/AT 边界；两服务的 Schema 补齐分页范围、UUID 操作键、公共响应头和 406/500 错误，示例补齐 title 额外字段拒绝声明。前端保留合法机器码、明细和请求标识，畸形响应不伪造服务端错误。新增只检查生成类型模式及根目录总检查，缺失/漂移非零退出且不覆盖原产物。HTTP 路径、DTO 主体、幂等、快照、外发与业务流程不扩展；没有新增依赖或改动锁文件。

查证及修复：示例原 URLconf 缺少统一路由错误处理，通过源码与 APIClient 确认后补齐；406 原被归为 INTERNAL_ERROR，改为 NOT_ACCEPTABLE。其余 Schema 缺失项是文档声明不完整，按既有运行规则补足。新会话模板的“契约脚本尚未建立”与当前文件不符，改为按实际文件及本次命令判断。示例 URLconf/View 只改变导入、Schema 配置及错误处理，原创建关系仍成立；逐项复核锚点后把人工标注修订为 1.0.1，更新受影响行号/摘要，示例教学版本保持 1.0.0。

技术取舍：延续 Serializer/View → OpenAPI → TypeScript 单一生成链；两工程独立，不建立运行时跨工程依赖。生成成功只证明工具能产出文件，因此另外核对接口表、真实 HTTP 错误、PostgreSQL 响应和漂移拒绝。复用锁中已有 jsonschema/PyYAML；第三方未提供的类型声明采用精确 import/call 例外，未放宽业务严格检查。

参考环境：Windows x64 宿主、Docker Desktop Linux amd64。下表 Python 为根 `.runtime/m1-t02-venv/Scripts/python.exe`，Node/npm 为 `.runtime/tools/node-v24.21.0-win-x64`，Docker 为 `C:/Program Files/Docker/Docker/resources/bin/docker.exe`；只临时调整当前进程 PATH。`根目录` 为项目根；两个后端/前端分别为根 `backend`/`frontend` 和 `examples/task-board/backend`/`frontend`。

| 工作目录 | 实际命令 | 观察结果 |
| --- | --- | --- |
| 根目录 | `docker compose ps --format '{{.Service}} {{.State}} {{.Health}}'` | 工作台及示例服务运行，数据库/API/Redis 健康；只读检查 |
| 两个后端各自目录 | `python manage.py spectacular --settings config.settings.test --file ../contracts/openapi.yaml --validate --fail-on-warn` | 无警告导出 5/3 个操作 |
| 两个前端各自目录 | `npm run api:types` | 从各自 Schema 生成声明成功，无远程生成调用 |
| 根目录 | `python -X utf8 scripts/check_contracts.py --node .runtime/tools/node-v24.21.0-win-x64/node.exe` | 两份实现导出、已保存 Schema、接口表一致；各 11 项无数据库契约测试；类型漂移检查、tsc 严格检查通过；检查模式未覆盖产物 |
| 根目录 | `docker compose run --rm --no-deps -v F:/Program/Fall_Campus_Recruitment/backend:/workspace:ro -w /workspace api /app/backend/.venv/bin/python -m pytest apps/jobs/tests tests --ds=config.settings.local -q -p no:cacheprovider` | 77 项通过；当前代码只读挂载，现有镜像依赖，真实 PostgreSQL 临时测试库；队列投递失败用替身注入 |
| 根目录 | `docker compose run --rm --no-deps -v F:/Program/Fall_Campus_Recruitment/examples/task-board/backend:/workspace:ro -w /workspace task-board-api /app/backend/.venv/bin/python -m pytest -q -p no:cacheprovider` | 51 项通过；示例独立 PostgreSQL 临时测试库；创建/重放/冲突/列表与 Schema 一致 |
| 工作台后端 | `python -m ruff check .`；`python -m ruff format --check .`；`python -m mypy config common apps tests --no-incremental` | 全通过；38 个 Python 文件格式，33 个源文件类型检查 |
| 示例后端 | `python -m ruff check .`；`python -m ruff format --check .`；`python -m mypy config common apps --no-incremental` | 全通过；27 个 Python 文件格式，26 个源文件类型检查 |
| 两个前端各自目录 | `npm run typecheck`；`npm run lint`；`npm run format:check`；`npm run test:tooling`；`npm run test -- --run`；`npm run build` | 静态及构建全部通过；工具各 11 项，工作台组件/请求 17 项、示例 23 项。生成工具真实验证缺失/漂移拒绝且不覆写；示例保留大包提示 |
| 根目录 | `python -X utf8 scripts/check_task_board_annotations.py`；`python -X utf8 -m unittest discover -s scripts -p test_check*.py -v` | 12 个节点、12 条关系引用通过；检查脚本/引用完整性共 9 项通过 |
| 根目录 | `python -m ruff check --config backend/pyproject.toml scripts/check_contracts.py scripts/test_check_contracts.py`；相同配置及文件的 `ruff format --check` | 两个新增检查脚本 lint/格式通过 |

过程失败与分类：

- 首次 Docker 只读检查因沙箱管道权限拒绝，正常权限复查通过。前端工具测试的 `spawn EPERM` 和总检查临时目录的 `PermissionError`/`WinError 5` 同属环境限制，以正常权限执行原命令通过，未改变检查标准。
- 初轮故障测试替换 View.get 时移除了 Schema 注解，测试内重新导出失败；先取得未打补丁的真实 Schema 再注入异常后，各 11 项通过。mypy 发现 JSON 返回 Any 和第三方缺失声明，补明确返回类型及精确第三方例外后通过；Ruff 的新增测试 import/格式问题已修正。
- 人工标注首次按原区间长度定位失败，因为新增 Schema 配置使 View 引用多一行；未写入半更新标注。人工核对原起止锚点和完整创建方法后同步，引用及负向测试全部通过。

知识与手工复核：Schema 是实现的可检查契约，类型生成不能替代运行时校验；HTTP 提交 503 与读取 failed 任务的 200 表达不同事件。可在根目录重跑上表总检查，确认成功且两份 OpenAPI/生成类型文件内容保持不变；生成器负向测试会在临时副本制造漂移，确认非零退出而保留原内容。

项目记忆：未发现独立记忆文件，沿用九份项目文档，不另建进度系统。更新 API 清单/规范、结构、前后端规范、两个 README、任务提示词及本文，同步契约、命令、错误和证据边界。根 AGENTS、需求及路线图的范围仍准确，无需修改；旧验收历史原样保留。当前任务退出条件满足，M1 汇总完成，M2–M5 的 14 个任务仍未开始。

限制：本次不重建或重启已有长期运行容器，它们仍使用原镜像；当前源码通过一次性容器及临时测试数据库验证。没有执行新的浏览器视觉/完整流程、真实队列故障演练、干净环境重装、ARM、公网或容量验收；M1-T02/03 的历史记录不冒充本次证据。示例 JS 为 688.32 kB（gzip 222.96 kB），保留已有大包警告，不作无关性能重构。未执行导入代码、模型调用、发布、部署或 Git 写操作。

最终审阅：根目录以标准输入运行 `python -X utf8 -`，核对 UTF-8、Python/JSON/TOML 语法、Markdown 围栏和 107 处本地引用、18 个任务状态及锁文件摘要，全部通过。完整差异与文件清单保存于 `.runtime/m1-t04-existing.diff`、`.runtime/m1-t04-file-review.json`；受阻检查遗留的本次空临时目录已清理。

最终文件范围：新增 10 个、修改 31 个、删除 0 个；路径相对根目录。全部原工程文件与锁文件保留；`.runtime` 基线、差异与审阅清单仅为可清理的本地证据。

| 文件 | 操作 | 作用 |
| --- | --- | --- |
| `README.md` | 修改 | 同步契约、开发命令或任务验收说明 |
| `backend/apps/jobs/api/schema.py` | 修改 | 补齐既有公共或业务契约声明 |
| `backend/apps/jobs/api/serializers.py` | 修改 | 声明列表 count 非负约束 |
| `backend/apps/jobs/tests/test_contract.py` | 修改 | 增加契约、错误边界或漂移拒绝回归验证 |
| `backend/apps/jobs/tests/test_contract_responses.py` | 新增 | 增加契约、错误边界或漂移拒绝回归验证 |
| `backend/common/errors.py` | 修改 | 明确 406 NOT_ACCEPTABLE 错误 |
| `backend/common/schema.py` | 新增 | 补齐既有公共或业务契约声明 |
| `backend/config/settings/base.py` | 修改 | 接入公共 Schema 并标明生成来源 |
| `contracts/openapi.yaml` | 修改 | 从已实现契约重新生成并核对 |
| `docs/api-catalog.md` | 修改 | 同步契约、开发命令或任务验收说明 |
| `docs/api-conventions.md` | 修改 | 同步契约、开发命令或任务验收说明 |
| `docs/backend-guidelines.md` | 修改 | 同步契约、开发命令或任务验收说明 |
| `docs/codex-task-prompt.md` | 修改 | 同步契约、开发命令或任务验收说明 |
| `docs/frontend-guidelines.md` | 修改 | 同步契约、开发命令或任务验收说明 |
| `docs/phase-1-plan.md` | 修改 | 同步契约、开发命令或任务验收说明 |
| `docs/project-structure.md` | 修改 | 同步契约、开发命令或任务验收说明 |
| `examples/task-board/README.md` | 修改 | 同步契约、开发命令或任务验收说明 |
| `examples/task-board/backend/apps/tasks/api/schema.py` | 新增 | 补齐既有公共或业务契约声明 |
| `examples/task-board/backend/apps/tasks/api/views.py` | 修改 | 接入示例严格输入 Schema |
| `examples/task-board/backend/apps/tasks/tests/test_contract.py` | 修改 | 增加契约、错误边界或漂移拒绝回归验证 |
| `examples/task-board/backend/apps/tasks/tests/test_contract_responses.py` | 新增 | 增加契约、错误边界或漂移拒绝回归验证 |
| `examples/task-board/backend/common/errors.py` | 修改 | 明确 406 NOT_ACCEPTABLE 错误 |
| `examples/task-board/backend/common/schema.py` | 新增 | 补齐既有公共或业务契约声明 |
| `examples/task-board/backend/config/settings/base.py` | 修改 | 接入公共 Schema 并标明生成来源 |
| `examples/task-board/backend/config/urls.py` | 修改 | 统一示例路由 404/500 错误 |
| `examples/task-board/contracts/openapi.yaml` | 修改 | 从已实现契约重新生成并核对 |
| `examples/task-board/frontend/package.json` | 修改 | 增加 api:types:check 脚本；依赖不变 |
| `examples/task-board/frontend/src/shared/api/client.test.ts` | 新增 | 增加契约、错误边界或漂移拒绝回归验证 |
| `examples/task-board/frontend/src/shared/api/client.ts` | 修改 | 校验错误形状并保留机器码和明细 |
| `examples/task-board/frontend/src/shared/api/generated/schema.d.ts` | 修改 | 从已实现契约重新生成并核对 |
| `examples/task-board/frontend/tooling/generate-api-types.mjs` | 修改 | 增加不覆盖已有声明的只检查模式 |
| `examples/task-board/frontend/tooling/generate-api-types.test.mjs` | 新增 | 增加契约、错误边界或漂移拒绝回归验证 |
| `frontend/package.json` | 修改 | 增加 api:types:check 脚本；依赖不变 |
| `frontend/src/shared/api/client.test.ts` | 修改 | 增加契约、错误边界或漂移拒绝回归验证 |
| `frontend/src/shared/api/client.ts` | 修改 | 校验错误形状并保留机器码和明细 |
| `frontend/src/shared/api/generated/schema.d.ts` | 修改 | 从已实现契约重新生成并核对 |
| `frontend/tooling/generate-api-types.mjs` | 修改 | 增加不覆盖已有声明的只检查模式 |
| `frontend/tooling/generate-api-types.test.mjs` | 新增 | 增加契约、错误边界或漂移拒绝回归验证 |
| `scripts/check_contracts.py` | 新增 | 串联实现导出、接口表、保存产物及类型检查 |
| `scripts/test_check_contracts.py` | 新增 | 增加契约、错误边界或漂移拒绝回归验证 |
| `testdata/analysis/task-board-create.json` | 修改 | 同步原有人工引用的行号、摘要和标注修订 |



### 文档基线 v0.2 检查记录

2026-09-28，在项目根目录通过 PowerShell 标准输入运行 `python -X utf8 -` 文档静态检查，校验文件范围、UTF-8、版本与修订记录、Markdown 表格和围栏、本地链接及显式锚点、需求/任务编号、API 方法路径与归属、契约生成路径及提示词边界。

检查结果：80 处本地链接与锚点有效，35 个 HTTP 操作与确认清单一致，其中 26 个读取、4 个同步创建、5 个异步提交；18 个开发任务均未开始，M1 至 M5 产品测试均未执行。首轮检查发现结构正文未写全内部解析协议路径，补齐后复检通过。既有文档改动已与修改前内容比较，新文档已逐项审阅；目录仍只有文档及项目指令。

这只是文档检查记录，没有执行构建、依赖安装、接口调用或产品验收用例。提示词场景采用静态审阅，没有启动开发会话。当前目录不是 Git 仓库，`git status --short` 无法提供差异；使用修改前文本及文件清单核对，未初始化仓库。

### M2-T01 项目导入与不可变快照验收（2026-09-29）

范围及前置：重新读取根 AGENTS、阶段计划、需求 FR-01/04/08、NFR-01/06、AT-01/02/03/21、结构/API/前后端规范和路线图；工作目录为 `F:\Program\Fall_Campus_Recruitment`，`git status --short` 返回非仓库，未初始化。只有根 AGENTS 适用，无独立项目记忆文件。Docker 只读状态确认既有 API、Worker、核对进程、PostgreSQL、Redis 和独立示例运行，数据库/API/Redis 健康；实际文件与 M1 文档前置一致。修改前 167 个非敏感工程文件及摘要保留在忽略目录 `.runtime/m2-t01-baseline`，未读取实际秘密文件。

实现：API-02 至 API-09 覆盖项目创建/列表/详情、multipart 导入、快照列表/详情、文件清单与分段读取。ZIP 安全检查覆盖所有条目；UTF-8 源码按 LF 规范化，生成文件摘要与每 128 行的稀疏索引。排除文件只保留原因计数；上传原包在成功或失败清理后不再保留。项目创建按规范化名称幂等，导入按项目和 ZIP 原始字节摘要幂等，新键生成新快照。延续现有四态、CSRF/来源保护、事务外投递与期限核对，不实现 API-17 或其他编号任务。

技术取舍：文件系统和数据库没有共同事务，采用完整暂存、fsync/完整性标识、同卷原子发布、数据库可见记录及恢复扫描。先释放上传锁再投递；有效领取在发布前后检查，旧 Worker 不能覆盖终态。未知提交结果核对数据库后再清理，避免删掉已成功快照。源码文件以服务端 file_id 存储，路径仅在清单中；读取验证归属与摘要，不执行导入代码。没有新增依赖、修改锁文件、模型外发或 Git 写操作。现有任务页增加 import 兼容，否则导入记录会使整个历史列表解析失败；未建立上传表单或工作区。

参考环境沿用已核验的 Windows x64 宿主及 Linux amd64 容器。下表 Python 是 `.runtime/m1-t02-venv/Scripts/python.exe`，Node 为 `.runtime/tools/node-v24.21.0-win-x64/node.exe`，Docker 为 `C:/Program Files/Docker/Docker/resources/bin/docker.exe`；均使用已有锁定依赖。`根目录` 指上述项目根。容器测试挂载当前源码只读，使用 PostgreSQL 临时测试库、`/tmp` 暂存和唯一 Redis 测试队列，不迁移或重启现有业务服务。

| 工作目录 | 实际命令 | 观察结果 |
| --- | --- | --- |
| 根目录 | `Get-Location`；`git status --short`；`rg --files -g AGENTS.md -g '!node_modules' -g '!.venv' -g '!dist' -g '!build'` | 当前目录正确，非 Git 仓库，只有根指令 |
| 根目录 | `docker compose ps --format '{{.Service}} {{.State}} {{.Health}}'` | 已有前置服务运行；首次沙箱管道权限不足，正常权限只读查询成功 |
| backend | `python manage.py makemigrations jobs projects --settings config.settings.test --no-header` | 生成 jobs 增量迁移及 projects 初始迁移，未应用于现有业务库 |
| 根目录 | `docker compose run --rm --no-deps -v F:/Program/Fall_Campus_Recruitment/backend:/workspace/backend:ro -v F:/Program/Fall_Campus_Recruitment/examples/task-board/backend/apps/tasks:/workspace/examples/task-board/backend/apps/tasks:ro -v F:/Program/Fall_Campus_Recruitment/examples/task-board/frontend/src:/workspace/examples/task-board/frontend/src:ro -w /workspace/backend api /app/backend/.venv/bin/python -m pytest apps/projects/tests apps/jobs/tests tests --ds=config.settings.local -q -p no:cacheprovider --tb=short --maxfail=3` | 最终 150 项通过，10.96 秒；真实 PostgreSQL 迁移/事务、幂等并发、API 响应、标准样例、真实 Redis/Celery 与进程退出恢复 |
| backend | `python -m ruff check . ../scripts/check_contracts.py`；`python -m ruff format --check . ../scripts/check_contracts.py` | 全通过，60 个 Python 文件格式一致 |
| backend | `python -m mypy config common apps tests --platform linux --no-incremental` | 严格检查 54 个源文件通过；Linux 是既定存储运行平台 |
| backend | `python manage.py check --settings config.settings.test`；`python manage.py makemigrations --check --dry-run --settings config.settings.test` | 0 个系统问题；No changes detected |
| backend | `python manage.py spectacular --settings config.settings.test --file ../contracts/openapi.yaml --validate --fail-on-warn` | 零警告导出工作台 13 个操作 |
| frontend | `node tooling/generate-api-types.mjs` | 从本地 Schema 生成声明，未手工编辑类型 |
| 根目录 | `python -X utf8 scripts/check_contracts.py --node .runtime/tools/node-v24.21.0-win-x64/node.exe` | 工作台 13/示例 3 个操作、保存 Schema、文档接口表和类型一致；工作台 11+2、示例 11 项无数据库契约测试通过，两端 tsc 通过 |
| 根目录 | `python -X utf8 -m unittest discover -s scripts -p test_check_contracts.py -v` | 3 项检查脚本回归通过 |
| frontend | `node node_modules/vitest/vitest.mjs run` | 4 个文件、19 项通过，含导入历史不误取检查结果及快照归属校验 |
| frontend | `node node_modules/eslint/bin/eslint.js . --max-warnings 0`；`node node_modules/prettier/bin/prettier.cjs --check .`；`node node_modules/typescript/bin/tsc --noEmit`；`node node_modules/vite/bin/vite.js build` | lint、格式、类型、构建通过，主 JS 438.06 kB / gzip 143.87 kB |
| 根目录 | `docker compose config --quiet` | 配置通过，不输出解析后的配置或凭据 |
| 根目录 | `docker run --rm --network none --cpus 0.5 --memory 128m --pids-limit 64 -e APP_AUTHORITY=127.0.0.1:5173 -v F:/Program/Fall_Campus_Recruitment/infra/nginx/default.conf.template:/etc/nginx/templates/default.conf.template:ro learning-lab-frontend:m1-t02 nginx -t` | 无网络、无端口临时容器内，新上传路径配置语法通过 |

用例证据在 `backend/apps/projects/tests/test_archive.py`、`test_projects.py`、`test_contract.py`：标准教学源码两次导入生成独立快照、旧引用保持；空/坏包、路径穿越、链接/特殊文件、Unicode/大小写/文件目录冲突、假条目数、伪造展开长度、CRC/加密/超限均拒绝；过滤内容不进入清单和已发布存储。磁盘写入/rename/发布后数据库失败用可控异常注入验证，真实子进程分别在写入及 rename 后以 `os._exit(23)` 中断，期限核对后遗留清理、旧快照完整。另验证立即投递与上传锁竞态、并发幂等、发布过期、提交确认失败但数据库已成功、符号链接/缺失/篡改文件读取拒绝。真实 Redis 测试使用独立队列及 Celery 测试 Worker，不以模拟结果代替执行。

开发期间的问题：Windows 归档测试 15 项通过、27 项因系统临时目录 WinError 5 受阻，未将该次记为通过；完整行为改在规定的 Linux 平台运行。Windows 默认 mypy 不认识 Linux 专用 flock/O_NOFOLLOW，改为显式 Linux 目标并通过；修复 UploadedFile 运行时泛型求值和测试类型错误。前端 Vitest 首次因 spawn EPERM 无法启动，正常权限后 19 项通过；契约总检查首次临时目录 ACL 拒绝，正常权限后通过。早期格式检查未通过的本次改动已格式化并复检。人工并发审阅发现上传锁释放晚于投递的竞态，增加立即执行用例后修复；超时单独映射 EXECUTION_TIMEOUT，任务异常不向 Celery 传播原始数据库/文件异常正文。

验收结论：M2-T01 已完成，AT-01、AT-02、AT-03、AT-21 在上述 API/服务和 Linux 测试边界通过；M2-T02 至 M2-T04 及后续任务仍未开始。手工复核观察点：用不同操作键重复上传同一无敏感 ZIP，观察两个 snapshot_id；再次按第一个文件标识读取，内容与哈希仍一致。完整工作区、模型外发、显式任务重试、整机断电/真实磁盘耗尽、容量和 ARM 平台未验收；没有把故障注入写成真实磁盘耗尽。Nginx 做配置检查，未将当前运行服务替换成新版本，因此未声称已有浏览器入口已提供新接口。

最终 ZIP 支持范围复核：使用上表相同 Docker 挂载前缀，执行 `python -m pytest apps/projects/tests/test_archive.py --ds=config.settings.local -q -p no:cacheprovider --tb=short`，46 项通过（0.56 秒），新增拒绝 ZIP64 与自解压前缀回归；此前全套 150 项记录保留。最终 `ruff check .`、`ruff format --check .` 通过。再次只读查询 Compose，现有服务仍运行，数据库/API/Redis 健康。

项目记忆同步：沿用九份项目文档与 AGENTS，没有创建平行进度/记忆系统。更新 AGENTS、README、API 清单/规范、前后端规范、结构及路线图的现状与协议；本节唯一记录任务状态。需求和新会话提示词无需修改。原文档“导入未实现”和“工作台仅 5 个操作”在本次实现后变为过期描述，依据实际模块、路由、生成 Schema 与测试修正，保留 M1 历史记录。最终文件清单及差异审阅结果见下表与忽略目录 `.runtime/m2-t01-file-review.json`、`.runtime/m2-t01-existing.diff`；依赖/锁文件及独立示例源码保持原样。

本次工程变更为 21 个新增、29 个修改、0 个删除；原 167 个工程文件全部保留。运行基线和审阅证据位于忽略目录，不是第二套项目进度。

| 变更 | 文件 | 用途 |
| --- | --- | --- |
| 新增 | `backend/apps/jobs/migrations/0002_job_result_url_job_scope_job_snapshot_id_and_more.py` | 既有任务增加作用域及快照结果，保留原记录 |
| 新增 | `backend/apps/projects/__init__.py` | 必要 Python 包边界 |
| 新增 | `backend/apps/projects/api/__init__.py` | 必要 Python 包边界 |
| 新增 | `backend/apps/projects/api/schema.py` | 额外字段拒绝契约 |
| 新增 | `backend/apps/projects/api/serializers.py` | 请求/响应及快照结果 DTO |
| 新增 | `backend/apps/projects/api/urls.py` | 项目模块路由接入 |
| 新增 | `backend/apps/projects/api/views.py` | 项目、上传和受控读取 HTTP 边界 |
| 新增 | `backend/apps/projects/archive.py` | 全条目归档安全、实际展开计数和文本过滤 |
| 新增 | `backend/apps/projects/exceptions.py` | 稳定且无内容回显的领域错误 |
| 新增 | `backend/apps/projects/migrations/0001_initial.py` | 项目/导入/快照/文件初始迁移 |
| 新增 | `backend/apps/projects/migrations/__init__.py` | 必要 Python 包边界 |
| 新增 | `backend/apps/projects/models.py` | 持久化资源与数据库约束 |
| 新增 | `backend/apps/projects/services.py` | 领域流程、资格核对与失败恢复 |
| 新增 | `backend/apps/projects/storage.py` | Linux 文件锁、持久写入、原子发布及受控读取 |
| 新增 | `backend/apps/projects/tasks.py` | Celery 导入入口 |
| 新增 | `backend/apps/projects/tests/__init__.py` | 必要 Python 包边界 |
| 新增 | `backend/apps/projects/tests/test_archive.py` | 归档攻击、过滤、预算与 ZIP 支持范围验证 |
| 新增 | `backend/apps/projects/tests/test_contract.py` | 接口形状与资源配置回归 |
| 新增 | `backend/apps/projects/tests/test_projects.py` | 数据库/API、并发、真实队列与进程中断验证 |
| 新增 | `backend/apps/projects/types.py` | 有界输入与导入结果结构 |
| 新增 | `backend/apps/projects/uploads.py` | multipart 接收限制 |
| 修改 | `AGENTS.md` | 同步当前实现边界 |
| 修改 | `README.md` | 运行、接口边界及复验命令 |
| 修改 | `backend/apps/jobs/api/serializers.py` | 请求/响应及快照结果 DTO |
| 修改 | `backend/apps/jobs/management/commands/reconcile_jobs.py` | 期限核对后扫描导入遗留 |
| 修改 | `backend/apps/jobs/models.py` | 持久化资源与数据库约束 |
| 修改 | `backend/apps/jobs/services.py` | 领域流程、资格核对与失败恢复 |
| 修改 | `backend/apps/jobs/tests/test_contract.py` | 接口形状与资源配置回归 |
| 修改 | `backend/common/errors.py` | 项目错误统一映射 |
| 修改 | `backend/common/middleware.py` | 上传解析限制的统一错误响应 |
| 修改 | `backend/config/environment.py` | 有界导入配置加载 |
| 修改 | `backend/config/settings/base.py` | 注册项目模块、上传中间件与资源默认值 |
| 修改 | `backend/config/settings/local.py` | 读取实际导入限制 |
| 修改 | `backend/config/urls.py` | 项目模块路由接入 |
| 修改 | `compose.yaml` | 私有导入卷及权限初始化依赖 |
| 修改 | `contracts/openapi.yaml` | 从实现生成的 13 操作契约 |
| 修改 | `docs/api-catalog.md` | 同步本任务协议、职责、边界与实测记录 |
| 修改 | `docs/api-conventions.md` | 同步本任务协议、职责、边界与实测记录 |
| 修改 | `docs/backend-guidelines.md` | 同步本任务协议、职责、边界与实测记录 |
| 修改 | `docs/frontend-guidelines.md` | 同步本任务协议、职责、边界与实测记录 |
| 修改 | `docs/phase-1-plan.md` | 同步本任务协议、职责、边界与实测记录 |
| 修改 | `docs/project-structure.md` | 同步本任务协议、职责、边界与实测记录 |
| 修改 | `docs/roadmap.md` | 同步本任务协议、职责、边界与实测记录 |
| 修改 | `frontend/src/features/jobs/JobsPage.test.tsx` | 导入历史的显示与查询隔离测试 |
| 修改 | `frontend/src/features/jobs/JobsPage.tsx` | 现有任务页显示导入记录与快照 |
| 修改 | `frontend/src/features/jobs/api/jobs-api.test.ts` | 导入任务响应边界回归 |
| 修改 | `frontend/src/features/jobs/api/jobs-api.ts` | 导入任务和快照归属运行时校验 |
| 修改 | `frontend/src/shared/api/generated/schema.d.ts` | 从 OpenAPI 生成的 TypeScript 声明 |
| 修改 | `infra/nginx/default.conf.template` | 仅导入路径允许有界 multipart 正文 |
| 修改 | `scripts/check_contracts.py` | 将新增契约用例纳入既有检查 |

### M2-T02 后端静态分析验收（2026-09-29）

范围和前置：工作目录 `F:\Program\Fall_Campus_Recruitment`，重新核对根 AGENTS、阶段计划、FR-02/NFR-02 与 AT-04/05/06、项目结构、API 清单/规范、前后端规范和路线图；根目录是唯一适用指令位置，没有独立项目记忆。`Get-Location` 正确，`git status --short` 和 `git rev-parse --show-toplevel` 均返回 `not a git repository`，未初始化。实际 M1/M2-T01 代码、生成入口、人工基准及服务与文档相符；只读 Compose 确认现有服务运行且 API/PostgreSQL/Redis 健康。修改前 177 个非敏感工程文件与 SHA-256 留在忽略目录 `.runtime/m2-t02-baseline`，不读取秘密文件。

实施：新增 analysis 模块及 API-10/11/12/14。显式 root_urlconf 避免猜测入口；经 projects 受控服务读取并校验快照，Python AST 索引与 DRF 规则不依赖 HTTP。识别标准路由/Router、固定序列化器/模型，区分事实、静态推断与框架规则。隔离进程有输入、AST、结果、内存和时间上限；父进程验证结构、计数、快照与行范围后才持久化。AnalysisRequest/Analysis 保存提交及结果；结果与任务终态原子提交。复用 jobs 的作用域幂等、唯一领取、期限核对，拒绝重复领取与迟到提交，不实现 M2-T03 图或 M2-T04 显式重试。分页和操作键公共函数从 projects API 移到 common/api，行为不变；任务历史增加 analysis 兼容，未建设工作区。

技术取舍与关键知识：AST 只说明静态代码结构，不给出执行轨迹；Router 隐式动作来自锁定框架规则，注册位置是源码证据，框架方法没有伪造的用户行号。导入别名只在唯一候选下解析；动态或有歧义的关系保留诊断。结果以有界 JSON 文档保存，避免提前创建图存储和遍历；新增迁移只在临时测试数据库应用。没有新增依赖、改动锁文件、执行导入模块、模型外发、Git 写操作或更新现有业务服务。

参考环境：Windows x64 宿主和项目既有 Linux amd64 镜像，Python 3.13.15、既有 DRF 3.18.1，前端固定 Node 24.21.0；均使用既有锁定依赖。下表 `python` 指 `.runtime/m1-t02-venv/Scripts/python.exe`，`node` 指 `.runtime/tools/node-v24.21.0-win-x64/node.exe`，`docker` 指 `C:/Program Files/Docker/Docker/resources/bin/docker.exe`；按工作目录使用对应相对路径。Docker 测试采用下列完整固定前缀，加表中实际子命令，源码与人工基准只读挂载，使用 PostgreSQL 临时测试库、临时存储和唯一 Redis 测试队列：

```text
docker compose run --rm --no-deps -v F:/Program/Fall_Campus_Recruitment/backend:/workspace/backend:ro -v F:/Program/Fall_Campus_Recruitment/testdata:/workspace/testdata:ro -v F:/Program/Fall_Campus_Recruitment/examples/task-board/backend/apps:/workspace/examples/task-board/backend/apps:ro -v F:/Program/Fall_Campus_Recruitment/examples/task-board/backend/config:/workspace/examples/task-board/backend/config:ro -v F:/Program/Fall_Campus_Recruitment/examples/task-board/frontend/src:/workspace/examples/task-board/frontend/src:ro -w /workspace/backend api /app/backend/.venv/bin/python
```

| 工作目录 | 实际命令 | 观察结果 |
| --- | --- | --- |
| 根目录 | `Get-Location`；`rg --files -g AGENTS.md -g '*MEMORY*' -g '*memory*' -g '!node_modules' -g '!.venv' -g '!vendor'`；`git status --short`；`git rev-parse --show-toplevel` | 目录正确，仅根指令；非 Git 仓库，无独立记忆 |
| 根目录 | `docker compose ps --format '{{.Service}} {{.State}} {{.Health}}'` | 前置服务运行；最初沙箱管道权限不足，正常权限查询成功 |
| backend | `python manage.py makemigrations analysis --settings config.settings.test --no-header` | 生成 analysis 初始迁移，未应用现有业务库 |
| 根目录 | 上述 Docker 前缀 + `-m pytest apps/analysis/tests apps/projects/tests apps/jobs/tests tests --ds=config.settings.local -q -p no:cacheprovider --tb=short --maxfail=5` | 191 项通过，17.06 秒；覆盖 PostgreSQL、导入/任务回归、真实队列和本任务隔离解析 |
| 根目录 | 上述 Docker 前缀 + `-m pytest apps/analysis/tests --ds=config.settings.local -q -p no:cacheprovider --tb=short --maxfail=3` | 最终 44 项通过，7.68 秒；含后续补充的真实进程超时/退出、根路由故障、HEAD 限制和重复 basename 用例；与 191 项重叠，不累加为独立用例数 |
| backend | `python -m ruff check . ../scripts/check_contracts.py`；`python -m ruff format --check . ../scripts/check_contracts.py` | 通过；83 个 Python 文件格式一致 |
| backend | `python -m mypy config common apps tests --platform linux --no-incremental` | 严格类型检查 77 个源文件通过 |
| backend | `python manage.py check --settings config.settings.test`；`python manage.py makemigrations --check --dry-run --settings config.settings.test` | 0 个系统问题；No changes detected |
| backend | `python manage.py spectacular --settings config.settings.test --file ../contracts/openapi.yaml --validate --fail-on-warn` | 导出工作台 17 个操作，无警告 |
| frontend | `node tooling/generate-api-types.mjs` | 从本地 Schema 生成声明，没有手改生成类型 |
| 根目录 | `python -X utf8 scripts/check_contracts.py --node .runtime/tools/node-v24.21.0-win-x64/node.exe` | 工作台 17/示例 3 操作与文档、保存 Schema、生成类型一致；工作台 11+12 和示例 11 项无数据库契约检查通过，两端 tsc 通过 |
| 根目录 | `python -X utf8 -m unittest discover -s scripts -p test_check_contracts.py -v` | 3 项通过 |
| frontend | `node node_modules/vitest/vitest.mjs run` | 4 个文件、21 项通过，含分析历史展示与错误快照/结果拒绝 |
| frontend | `node node_modules/eslint/bin/eslint.js . --max-warnings 0`；`node node_modules/prettier/bin/prettier.cjs --check .`；`node node_modules/typescript/bin/tsc --noEmit` | lint、格式和类型检查通过 |
| frontend | `node node_modules/vite/bin/vite.js build` | 通过，主 JS 438.58 kB / gzip 143.98 kB |

最终文档及文件核对：根目录通过标准输入执行 `python -X utf8 -`，对非敏感工程清单计算 SHA-256 并与修改前副本比较，检查 UTF-8、行尾空白、冲突标记、Markdown 链接/围栏、任务状态及交付文件表；全部通过，29 新增/22 修改/0 删除。随后 `git status --short` 仍返回非仓库，这是环境事实，不作为 Git 检查通过。最终再次执行上表 Compose 只读状态命令，原有服务仍运行，API/PostgreSQL/Redis 健康，一次性测试容器已退出。

测试证据：`test_parser.py` 将既有 task-board 人工标注的后端子集与实际分析逐项对照；新增 drf-static 人工基准检查标准 Router 六动作及注册/类/序列化器/模型位置，框架动作 source_ref=null。覆盖别名/相对导入、ReadOnly/DefaultRouter、mixin、直接 as_view、转换器/格式后缀/尾斜杠、歧义、缺失引用、动态序列化器/模型、条件覆盖、模块遮蔽、循环包含、空结果及预算。`test_analysis.py` 覆盖真实 ZIP 快照至隔离解析/API 读取、重放/冲突/并发、损坏快照、结果写入失败、迟到结果、真实 Redis/Celery 和真实受控子进程超时/exit(23)；这些子进程是固定测试程序，导入代码始终只解析。`test_contract.py` 及前端回归验证结构与来源保护。

开发期间问题如实保留：Windows 解析首轮 15 项通过、1 项临时目录 WinError 5 阻塞；随后本地运行不涉及临时文件的 29 项通过、1 项未选中，完整用例已在 Linux 通过。首次 Linux 聚焦 35 项通过、1 项失败，原因是测试客户端将 None 发成无媒体类型空请求，修正为显式 JSON null 后通过，未降低输入校验。mypy 首轮暴露引用整数收窄及测试可空值访问，已修正并复检。前端首次测试/构建 spawn EPERM、契约总检查临时目录 ACL 拒绝；正常本地权限下同命令通过。最终审阅补齐条件属性、正则前缀、HEAD 限制及重复 basename 的保守处理，聚焦复验通过。

验收结论：M2-T02 已完成，AT-04/05/06 在声明规则及 Linux API/Worker 边界通过，M2-T03/M2-T04 及后续任务保持未开始。手工复核观察点：导入 drf-static 样例并指定 root_urls.py，检查 POST 对应 create 的注册引用指向 router_urls.py 第 6 行，框架 create 的 source_ref 为 null；把 get_serializer_class 改为动态选择后重新导入，应显示 DYNAMIC_SERIALIZER 并保留空关联。该观察点可通过 API 复核，当前没有分析工作区页面。

限制：未更新运行中的镜像或业务数据库；新接口需按 README 正常重建本地服务后启用。没有把 Nginx/浏览器完整分析流程、任意框架版本、容量极限、真实内存耗尽、整机断电或跨平台解析器验收写成通过。Linux 受控进程为当前支持平台；标准规则之外的动态行为仍明确不支持。

项目记忆同步：读过本节列出的八份相关项目文档及 AGENTS/README；更新 AGENTS、README、API 清单/规范、结构、前后端规范、路线图和本阶段计划。初始未发现前置状态冲突；实现后“分析未实现/只有 13 操作”的现状描述已过期，依据当前模块、17 操作 Schema 和测试修正；历史任务记录保留。需求基线与新会话提示词不受影响，未修改，没有另建记忆或进度系统。

最终变更清单如下；29 个新增、22 个修改、0 个删除，原 177 个工程文件全部保留。未改依赖/锁文件、Compose、独立教学应用或导入存储。基线摘要与差异审阅保存在忽略目录 `.runtime/m2-t02-file-review.json`、`.runtime/m2-t02-existing.diff`，它们仅是本次审阅证据。

| 变更 | 文件 | 说明 |
| --- | --- | --- |
| 新增 | `backend/apps/analysis/__init__.py` | 必要 Python 包边界 |
| 新增 | `backend/apps/analysis/api/__init__.py` | 必要 Python 包边界 |
| 新增 | `backend/apps/analysis/api/schema.py` | 四个分析操作的请求/响应及 Schema |
| 新增 | `backend/apps/analysis/api/serializers.py` | 四个分析操作的请求/响应及 Schema |
| 新增 | `backend/apps/analysis/api/urls.py` | 四个分析操作的请求/响应及 Schema |
| 新增 | `backend/apps/analysis/api/views.py` | 四个分析操作的请求/响应及 Schema |
| 新增 | `backend/apps/analysis/drf_rules.py` | AST 索引、静态路由与 DRF 规则 |
| 新增 | `backend/apps/analysis/migrations/0001_initial.py` | 分析请求与结果持久化 |
| 新增 | `backend/apps/analysis/migrations/__init__.py` | 必要 Python 包边界 |
| 新增 | `backend/apps/analysis/models.py` | 分析请求与结果持久化 |
| 新增 | `backend/apps/analysis/parser.py` | AST 索引、静态路由与 DRF 规则 |
| 新增 | `backend/apps/analysis/protocol.py` | 受限解析进程、内部类型和结果验证 |
| 新增 | `backend/apps/analysis/python_index.py` | AST 索引、静态路由与 DRF 规则 |
| 新增 | `backend/apps/analysis/runner.py` | 受限解析进程、内部类型和结果验证 |
| 新增 | `backend/apps/analysis/services.py` | 连接快照、任务与原子分析结果 |
| 新增 | `backend/apps/analysis/tasks.py` | 连接快照、任务与原子分析结果 |
| 新增 | `backend/apps/analysis/tests/__init__.py` | 必要 Python 包边界 |
| 新增 | `backend/apps/analysis/tests/test_analysis.py` | 静态解析、进程/API/任务或契约验收 |
| 新增 | `backend/apps/analysis/tests/test_contract.py` | 静态解析、进程/API/任务或契约验收 |
| 新增 | `backend/apps/analysis/tests/test_parser.py` | 静态解析、进程/API/任务或契约验收 |
| 新增 | `backend/apps/analysis/types.py` | 受限解析进程、内部类型和结果验证 |
| 新增 | `backend/apps/analysis/worker.py` | 受限解析进程、内部类型和结果验证 |
| 新增 | `backend/common/api.py` | 复用既有操作键、分页和参数校验 |
| 新增 | `testdata/analysis/drf-static-expected.json` | 小型 Router 静态样例或人工预期 |
| 新增 | `testdata/analysis/drf-static/models.py` | 小型 Router 静态样例或人工预期 |
| 新增 | `testdata/analysis/drf-static/root_urls.py` | 小型 Router 静态样例或人工预期 |
| 新增 | `testdata/analysis/drf-static/router_urls.py` | 小型 Router 静态样例或人工预期 |
| 新增 | `testdata/analysis/drf-static/serializers.py` | 小型 Router 静态样例或人工预期 |
| 新增 | `testdata/analysis/drf-static/views.py` | 小型 Router 静态样例或人工预期 |
| 修改 | `AGENTS.md` | 同步本任务现状、边界、契约或验证记录 |
| 修改 | `README.md` | 同步本任务现状、边界、契约或验证记录 |
| 修改 | `backend/apps/jobs/api/serializers.py` | 分析任务资格、结果引用及契约兼容 |
| 修改 | `backend/apps/jobs/services.py` | 分析任务资格、结果引用及契约兼容 |
| 修改 | `backend/apps/jobs/tests/test_contract.py` | 分析任务资格、结果引用及契约兼容 |
| 修改 | `backend/apps/projects/api/views.py` | 复用既有操作键、分页和参数校验 |
| 修改 | `backend/config/settings/base.py` | 注册 analysis 及其四个路由 |
| 修改 | `backend/config/urls.py` | 注册 analysis 及其四个路由 |
| 修改 | `contracts/openapi.yaml` | 从实现生成的 17 操作契约或类型 |
| 修改 | `docs/api-catalog.md` | 同步本任务现状、边界、契约或验证记录 |
| 修改 | `docs/api-conventions.md` | 同步本任务现状、边界、契约或验证记录 |
| 修改 | `docs/backend-guidelines.md` | 同步本任务现状、边界、契约或验证记录 |
| 修改 | `docs/frontend-guidelines.md` | 同步本任务现状、边界、契约或验证记录 |
| 修改 | `docs/phase-1-plan.md` | 同步本任务现状、边界、契约或验证记录 |
| 修改 | `docs/project-structure.md` | 同步本任务现状、边界、契约或验证记录 |
| 修改 | `docs/roadmap.md` | 同步本任务现状、边界、契约或验证记录 |
| 修改 | `frontend/src/features/jobs/JobsPage.test.tsx` | 分析任务历史兼容及回归 |
| 修改 | `frontend/src/features/jobs/JobsPage.tsx` | 分析任务历史兼容及回归 |
| 修改 | `frontend/src/features/jobs/api/jobs-api.test.ts` | 分析任务历史兼容及回归 |
| 修改 | `frontend/src/features/jobs/api/jobs-api.ts` | 分析任务历史兼容及回归 |
| 修改 | `frontend/src/shared/api/generated/schema.d.ts` | 从实现生成的 17 操作契约或类型 |
| 修改 | `scripts/check_contracts.py` | 将分析契约纳入既有检查 |

### M2-T03 关系图存储与有界遍历验收（2026-09-29）

范围与前置：执行目录 `F:\Program\Fall_Campus_Recruitment`，重新核对根 AGENTS、任务/前置状态、FR-02/04/NFR-02 与 AT-04/05/06/09、结构、API 清单/规范、前后端规范、路线图及 README。只有根指令，无独立项目记忆；Git 返回非仓库，未初始化。用户选择只投影现有解析范围，旧分析不回填，通过新操作键重新分析原快照生成新图；未扩展 service/ORM、前端解析或 M2-T04。

实施与取舍：新增纯 graph 模块和内部类型；AnalysisGraph 一对一保存图版本与有界 JSON，查询时建立邻接表。仅包含 endpoint/view/serializer/model 及三类有证据的关系；包含链与框架动作保留证据，不伪造方法源码。共享符号去重，重复接口候选保留独立 ID。图在发布事务前构建/校验，和 Analysis、成功任务原子发布；失败回滚，过期领取不可发布。API-13 支持 BFS/DFS、根节点和预算；空图、历史无图、根不存在、截断、损坏和依赖故障分别响应。没有修改解析规则、任务实现、依赖或锁文件。

参考环境：Windows x64 宿主、已有 Linux amd64 API 镜像与真实 PostgreSQL/Redis。下表 `python` 指 `.runtime/m1-t02-venv/Scripts/python.exe`（Python 3.13.15），`node` 指 `.runtime/tools/node-v24.21.0-win-x64/node.exe`（Node 24.21.0），`docker` 指 `C:/Program Files/Docker/Docker/resources/bin/docker.exe`，按工作目录调整工具相对路径。Linux 命令使用以下完整前缀，源码只读，临时测试库/存储及唯一 Redis 测试队列；不更新业务数据库或运行镜像：

```text
docker compose run --rm --no-deps -v F:/Program/Fall_Campus_Recruitment/backend:/workspace/backend:ro -v F:/Program/Fall_Campus_Recruitment/testdata:/workspace/testdata:ro -v F:/Program/Fall_Campus_Recruitment/examples/task-board/backend/apps:/workspace/examples/task-board/backend/apps:ro -v F:/Program/Fall_Campus_Recruitment/examples/task-board/backend/config:/workspace/examples/task-board/backend/config:ro -v F:/Program/Fall_Campus_Recruitment/examples/task-board/frontend/src:/workspace/examples/task-board/frontend/src:ro -w /workspace/backend api /app/backend/.venv/bin/python
```

| 工作目录 | 实际命令或操作 | 观察结果 |
| --- | --- | --- |
| 根目录 | `Get-Location`；`git status --short`；规划时另执行 `git rev-parse --show-toplevel` | 路径正确；Git 返回 not a git repository，未初始化 |
| 根目录 | `rg --files --hidden -g AGENTS.md -g '!node_modules' -g '!.venv' -g '!.runtime' -g '!.pytest_cache'` | 只有根指令；首次未排除缓存时遇 ACL 拒绝，排除无关缓存后完成 |
| 根目录 | `docker compose ps --format '{{.Service}} {{.State}} {{.Health}}'` | 规划及最终正常权限只读查询通过，原有服务运行，API/PostgreSQL/Redis 健康；沙箱管道权限拒绝不作为服务故障 |
| backend | 规划核验：`python -B -m pytest apps/analysis/tests/test_parser.py apps/analysis/tests/test_contract.py --ds=config.settings.test -q -p no:cacheprovider -k 'not imported_code_is_never_executed'` | 31 通过、1 未选中；临时目录用例随后在 Linux 全集通过 |
| 根目录 | `python -B -X utf8 scripts/check_task_board_annotations.py` | 既有人工基准 12 节点、12 关系引用通过 |
| backend | `python manage.py makemigrations analysis --settings config.settings.test --no-header` | 生成 0002_analysisgraph，无历史回填 |
| backend | `python -m pytest apps/analysis/tests/test_graph.py --ds=config.settings.test -q -p no:cacheprovider` | 首轮纯图 21 项通过 |
| backend | `python -m pytest apps/analysis/tests/test_graph.py apps/analysis/tests/test_contract.py apps/jobs/tests/test_contract.py --ds=config.settings.test -q -p no:cacheprovider --tb=short` | 空 UUID 修复后 58 项通过；后加三个空白参数用例进入最终 Linux 全集和契约总检查 |
| backend | `python -m pytest apps/analysis/tests/test_contract.py apps/jobs/tests/test_contract.py --ds=config.settings.test -q -p no:cacheprovider --tb=short` | 最终补充旧枚举名回归后 40 项通过；只涉及 Schema 命名，无业务行为变化 |
| 根目录 | 上述 Docker 前缀 + `-m pytest apps/analysis/tests --ds=config.settings.local -q -p no:cacheprovider --tb=short --maxfail=5` | 首轮 89 通过、1 测试请求头构造失败；见下文 |
| 根目录 | 上述 Docker 前缀 + `-m pytest apps/analysis/tests apps/projects/tests apps/jobs/tests tests --ds=config.settings.local -q -p no:cacheprovider --tb=short --maxfail=5` | 最终 244 项通过，22.96 秒；含真实 PostgreSQL、迁移/事务、导入/任务回归、受控解析与 Redis/Celery 图发布 |
| backend | `python -m ruff check .`；`python -m ruff format --check .` | 通过；86 个 Python 文件格式一致，开发时只对本任务文件执行 --fix/format |
| backend | `python -m mypy config common apps tests --platform linux --no-incremental` | 81 个源文件严格检查通过 |
| backend | `python manage.py check --settings config.settings.test`；`python manage.py makemigrations --check --dry-run --settings config.settings.test` | 0 个系统问题；No changes detected |
| backend | `python manage.py spectacular --settings config.settings.test --file ../contracts/openapi.yaml --validate --fail-on-warn` | 导出工作台 18 个操作，无警告 |
| frontend | `node tooling/generate-api-types.mjs`；`node node_modules/typescript/bin/tsc --noEmit` | 本地 Schema 生成及类型检查通过 |
| 根目录 | `python -X utf8 scripts/check_contracts.py --node .runtime/tools/node-v24.21.0-win-x64/node.exe` | 正常权限下通过；工作台 18/示例 3 操作与文档、保存 Schema、类型一致；工作台 11+31、示例 11 项契约检查及两端 tsc 通过 |
| 根目录 | 经标准输入执行 `python -B -X utf8 -` 比较修改前摘要、当前文件与声明清单，并逐项比较旧 OpenAPI | 5 新增、20 修改、0 删除；UTF-8、Python/JSON 语法、空白、冲突标记、文档链接/围栏及任务状态通过；仅新增 graph 路径，原有路径与 Schema 组件逐项相同 |

覆盖证据：人工投影逐项核对 task-board 后端引用和 drf-static 注册/框架动作，不将人工基准的 validation 运行含义改称静态事实。真实空 urlpatterns 发布空图；DefaultRouter API 根保持孤立节点。合成邻接图覆盖多分量、菱形共享、自环/多节点环、BFS/DFS 次序、精确预算和不悬空边。校验拒绝重复 ID、无证据、跨快照、缺失文件、越界及保存超限。API 覆盖历史 409、节点 404、只读无任务副作用、跨分析隔离、失败回滚、迟到结果、损坏 500、依赖 503 和来源保护；迁移往返只在临时库验证旧 Analysis 内容不变且不回填。

开发失败与修复：首轮无数据库测试 57 通过、1 失败，空 root_node_id 被 DRF 可选 HTML 字段当作缺省；在请求边界显式拒绝空值并补充空白参数用例。mypy 发现 TypedDict 动态键、新加的冗余 ignore 及 Serializer 的 label 属性冲突，改用明确关系类型、移除忽略并将节点展示字段命名为 name，最终通过。Linux 首轮 Host 用例的攻击头被 APIClient.credentials 覆盖，按既有测试方式设置实际非法头，确认既有 403 ORIGIN_REJECTED；未降低保护。契约检查首次遇 Windows 临时目录 ACL 拒绝，正常权限重跑同命令通过，未修改工具来绕过检查。最终基线比对还发现生成器因新增 kind 自动把旧 KindEnum 改名，故仅在既有 Schema 配置固定原证据枚举名并加回归断言，重新生成和验证；不修改运行保护、依赖或锁文件。

结论与学习：M2-T03 在现有静态解析及 Linux API/Worker 边界完成；不代表 service/ORM、前端展示、完整 AT-09/10/23 或 M2-T04 完成。访问集合保证有限遍历，图可达性不是运行调用；独立图版本与分析绑定防止历史引用漂移。手工复核点：启用新版本后分析 drf-static/root_urls.py，选取 POST/create 的 root_node_id，应返回四节点三关系；注册位置为 router_urls.py 第 6 行，隐式 create 没有伪造方法行号。动态序列化器场景应保留诊断且不生成对应连接。

项目记忆同步：读过上述项目文档及 AGENTS/README；更新 AGENTS、README、API 清单/规范、后端规范、项目结构、路线图及本阶段计划。依据模型、18 操作 Schema 和真实测试修正“图未实现/17 操作”现状描述，以及阶段计划停留于 M2-T01 的目录摘要；历史验收记录保留。需求、前端规范和任务提示词没有受影响的持久规则，未修改；未建立独立记忆或平行进度。

限制与审阅：没有新依赖、Git 写操作、模型外发或导入源码执行。现有业务镜像/数据库未更新，需要启用新接口时按 README 正常重建且保留数据卷。未验证浏览器图工作区、容量极限、原生 Windows Worker 或全机故障。修改前 217 个工程文件副本/摘要位于忽略目录 `.runtime/m2-t03-baseline`；最终审阅证据为 `.runtime/m2-t03-file-review.json` 与 `.runtime/m2-t03-review.diff`。期间出现的 `.idea` 文件不是本任务创建，原样保留并排除交付改动。

本任务新增 5 个、修改 20 个文件、无删除；详细清单如下。

| 变更 | 文件 | 说明 |
| --- | --- | --- |
| 新增 | `backend/apps/analysis/graph.py` | 纯图投影、校验与 BFS/DFS |
| 新增 | `backend/apps/analysis/migrations/0002_analysisgraph.py` | 独立图存储，无历史回填 |
| 新增 | `backend/apps/analysis/tests/test_graph.py` | 人工投影、证据及算法边界 |
| 新增 | `backend/apps/analysis/tests/test_graph_api.py` | API、原子性、迁移与隔离 |
| 新增 | `testdata/analysis/graph-expected.json` | 人工后端投影预期 |
| 修改 | `backend/apps/analysis/types.py` | 图类型、版本与预算 |
| 修改 | `backend/apps/analysis/models.py` | 一对一 AnalysisGraph |
| 修改 | `backend/apps/analysis/services.py` | 图发布和查询 |
| 修改 | `backend/apps/analysis/api/serializers.py` | 图查询和响应契约 |
| 修改 | `backend/apps/analysis/api/views.py` | API-13 请求边界 |
| 修改 | `backend/apps/analysis/api/urls.py` | 图路由 |
| 修改 | `backend/apps/analysis/tests/test_analysis.py` | 真实 Worker 图发布断言 |
| 修改 | `backend/apps/analysis/tests/test_contract.py` | Schema 与非法查询参数 |
| 修改 | `backend/apps/jobs/tests/test_contract.py` | 已实现路由清单 |
| 修改 | `backend/config/settings/base.py` | 固定原有证据枚举的 Schema 名称，保持生成类型兼容 |
| 修改 | `contracts/openapi.yaml` | 实现导出的 18 操作契约 |
| 修改 | `frontend/src/shared/api/generated/schema.d.ts` | 本地 Schema 生成类型 |
| 修改 | `AGENTS.md` | 当前能力边界 |
| 修改 | `README.md` | 图使用与历史兼容说明 |
| 修改 | `docs/api-catalog.md` | API-13 字段、查询及错误 |
| 修改 | `docs/api-conventions.md` | 图版本、引用和历史语义 |
| 修改 | `docs/backend-guidelines.md` | 存储、预算、遍历和事务边界 |
| 修改 | `docs/project-structure.md` | 图模块与测试职责 |
| 修改 | `docs/roadmap.md` | 同步现状，不启动下一阶段 |
| 修改 | `docs/phase-1-plan.md` | 本任务状态、证据与限制 |

### M2-T04 任务重试与故障恢复验收（2026-09-29）

范围：仅 M2-T04、必要前端历史兼容、测试与文档。前置核验覆盖根 AGENTS、阶段计划、需求 FR-08/NFR-03 与 AT-18/19/20、项目结构、API 清单/契约、前后端规范、路线图及 README，并核对 jobs/projects/analysis 实现、配置、迁移和测试。只有根 AGENTS 适用，没有独立项目记忆；Git 仍返回 not a git repository。现有服务均运行，未重建、停止或迁移业务服务。

实现：新增 API-17 和 Job.previous_job 可空 PROTECT 关联；失败任务使用新键另建尝试，同键只恢复原任务。jobs/retries 协调原请求，业务请求仍由原模块服务在任务事务内创建。基础检查接受空 JSON，分析复用原快照/root_urlconf；导入必须重新上传原 ZIP 并核对摘要，复用过滤、预算及暂存清理。重试生成独立存储标识，旧失败记录、快照和分析结果保持不变。统一投递错误处理只终结 queued，不覆盖已经 running/succeeded 的任务；三类原提交接口均明确提示“投递未确认，请查询任务状态”，不把确认丢失误报为任务执行失败；没有自动重新投递。基础检查补齐结果写入后的期限核对与数据库错误脱敏。

必要兼容修复：既有前端运行时校验强制 previous_job_id=null，新增重试会导致整个历史列表拒绝响应；因此只补 UUID/非自引用校验及“重试自任务”展示，并验证重新挂载恢复，不实现重试表单或 M3 工作区。没有新增依赖、修改锁文件、执行导入源码、模型调用或 Git 写操作。

参考环境：现有 Windows x64、固定 Python 3.13.15/Node 24.21.0，真实 Linux 容器 PostgreSQL/Redis 依赖。后端持久化使用自动创建/销毁的临时测试库，导入使用临时存储，真实 Worker 使用独立队列。完整应用服务和数据库整体重启未在本次重复执行；AT-18 用新 API 客户端、前端重新挂载和独立读取进程验证已持久化任务、快照、分析和图，未把此范围扩展到未来记录类型。

以下命令中，根目录为 `F:\Program\Fall_Campus_Recruitment`。`python` 使用根下 `.runtime/m1-t02-venv/Scripts/python.exe`，`node` 使用 `.runtime/tools/node-v24.21.0-win-x64/node.exe`，Docker 使用 `C:/Program Files/Docker/Docker/resources/bin/docker.exe`；实际均通过 PowerShell `&` 调用固定可执行文件。Docker 后端命令公共前缀如下（只读挂载当前源码，避免误测旧镜像）：

```text
docker compose run --rm --no-deps -v F:/Program/Fall_Campus_Recruitment/backend:/workspace/backend:ro -v F:/Program/Fall_Campus_Recruitment/testdata:/workspace/testdata:ro -v F:/Program/Fall_Campus_Recruitment/examples/task-board/backend/apps:/workspace/examples/task-board/backend/apps:ro -v F:/Program/Fall_Campus_Recruitment/examples/task-board/backend/config:/workspace/examples/task-board/backend/config:ro -v F:/Program/Fall_Campus_Recruitment/examples/task-board/frontend/src:/workspace/examples/task-board/frontend/src:ro -w /workspace/backend api /app/backend/.venv/bin/python
```

| 工作目录 | 实际命令或操作 | 观察结果 |
| --- | --- | --- |
| 根目录 | `Get-Location`；`git status --short`；`git rev-parse --show-toplevel` | 路径正确；非 Git 仓库，未初始化 |
| 根目录 | `rg --files --hidden -g AGENTS.md -g '*MEMORY*' -g '*memory*' -g '!node_modules' -g '!.venv' -g '!.runtime' -g '!.pytest_cache' -g '!.ruff_cache' -g '!.mypy_cache'` | 仅根 AGENTS，无独立记忆文件 |
| 根目录 | `docker compose ps --format '{{.Service}} {{.State}} {{.Health}}'` | 正常权限下现有服务运行，API/数据库/Redis 健康；沙箱管道拒绝不是服务故障 |
| backend | `python manage.py makemigrations jobs --settings config.settings.test --no-header` | 生成 0003_job_previous_job，只添加可空关联；首轮类型注解加载错误修复后成功 |
| 根目录 | Docker 前缀 + `-m pytest apps/jobs/tests/test_retries.py apps/jobs/tests/test_jobs.py --ds=config.settings.local -q -p no:cacheprovider --tb=short --maxfail=4` | 57 通过，4.18 秒 |
| 根目录 | Docker 前缀 + `-m pytest apps/jobs/tests/test_recovery.py --ds=config.settings.local -q -p no:cacheprovider --tb=short --maxfail=3` | 首轮 10 通过；补充真实连接失败及脱敏用例、修正故障目标隔离后 14 通过，10.00 秒；最终补正三类提交提示并验证 HTTP 503/Location 后再次 14 通过，9.93 秒 |
| 根目录 | Docker 前缀 + `-m pytest apps/jobs/tests apps/projects/tests apps/analysis/tests tests --ds=config.settings.local -q -p no:cacheprovider --tb=short --maxfail=4` | 首轮 275 通过、3 个故障目标配置用例失败；最终 278 通过，33.54 秒 |
| backend | `python -m ruff check .`；`python -m ruff format --check .` | 通过；90 个 Python 文件格式一致，实际格式修复仅针对本任务文件 |
| backend | `python -m mypy config common apps tests --platform linux --no-incremental` | 85 个源文件严格检查通过；新增测试的可空/请求头类型已修正 |
| backend | `python manage.py check --settings config.settings.test`；`python manage.py makemigrations --check --dry-run --settings config.settings.test` | 无系统问题；No changes detected |
| backend | `python manage.py spectacular --settings config.settings.test --file ../contracts/openapi.yaml --validate --fail-on-warn` | 生成包含 19 个操作的 Schema，无警告 |
| frontend | `node tooling/generate-api-types.mjs`；`node node_modules/typescript/bin/tsc --noEmit` | 生成及类型检查通过 |
| frontend | `node node_modules/vitest/vitest.mjs run src/features/jobs` | 正常权限下 2 个文件、10 项通过；包括非空关联和重新挂载恢复 |
| frontend | `node node_modules/eslint/bin/eslint.js . --max-warnings 0`；`node node_modules/prettier/bin/prettier.cjs --check .` | 均通过 |
| frontend | `node node_modules/vite/bin/vite.js build` | 构建通过，1525 个模块；产物在忽略的 dist，不计入源码交付 |
| 根目录 | `python -X utf8 scripts/check_contracts.py --node .runtime/tools/node-v24.21.0-win-x64/node.exe` | 正常权限下通过；工作台 19/示例 3 个操作、文档表、保存 Schema 与类型一致，11+31+11 项契约测试及两端 TypeScript 通过 |
| 根目录 | `docker compose run --rm --no-deps -v F:/Program/Fall_Campus_Recruitment/infra/nginx/default.conf.template:/etc/nginx/templates/default.conf.template:ro frontend nginx -t` | 新重试上传路径配置语法通过；一次性容器无宿主端口 |

故障证据：三种任务的提交进程真实退出于事务提交后、投递之前；独立核对进程按实际短期限将其标记 QUEUE_TIMEOUT，导入暂存被清理。真实 Redis 投递后的 Celery Worker 在取得分析执行资格后退出；独立核对形成 EXECUTION_TIMEOUT，旧资格无法完成；显式新尝试由新 Worker 完成，另一进程能读取结果、图和旧快照。受控本地不可监听端口真实触发 broker 连接失败，三种任务均有界失败留痕。发布确认丢失使用故障注入验证已成功结果不回退；数据库暂不可用使用替身验证核对循环继续及诊断不泄露。基础检查的结果写入越过期限用受控时钟验证事务回滚；原有导入进程中断、分析提交回滚和迟到写入回归均通过。真实整机断电、磁盘耗尽和数据库停服未在此次执行，不将故障注入等同真实停服。

开发失败与修复：最初 UploadedFile 泛型注解在运行期不支持下标，增加延迟注解后迁移生成成功；mypy 的三项测试标注错误通过显式可空断言和请求头类型解决。首轮新增 broker 故障测试被容器 CELERY_BROKER_URL 覆盖，未触发预期连接失败，因此三项失败；检查已安装 Celery 的配置优先级后改成显式 Connection 和独立测试队列，不降低断言，最终全回归通过。首轮曾向既有 broker 投递只存在于临时测试库的随机测试标识；没有执行业务库迁移或清理命令，最终测试固定隔离。前端 Vitest 首次遇沙箱 spawn EPERM，契约总检查首次遇 Windows 临时目录 WinError 5；均以正常权限执行原命令后通过，没有改测试或关闭检查。

项目文档同步：更新 AGENTS、README、API 清单/规范、后端规范、前端规范、项目结构、路线图及本计划。通过源码/生成 Schema 核对，发现 API 清单当前摘要遗漏已经实现的 API-13、结构文档操作数未计入图接口，以及前端拒绝非空 previous_job_id；前两处已纠正为当前 19 个操作，后者以运行时兼容和测试修复。需求及任务提示词不涉及持久规则变化，保持原文；历史验收记录不改写，不建立平行记忆或进度系统。

结论与学习：M2-T04 完成；M2 退出条件在现有静态分析及 Linux 后端范围满足。关键知识是数据库事实与队列投递分离、事务外故障窗口、唯一键幂等和领取资格约束。选择超时失败留痕加人工新尝试，不引入自动重发；导入重传原 ZIP 避免长期保存未过滤输入。手工复核点：启用新版本后针对 failed 任务用新键重试，应得到新 id 和旧 previous_job_id；相同键再次提交返回同一 id，刷新历史仍显示原任务关联且旧错误保留。

剩余限制：仅 API/Worker、现有历史页面和受控 Linux 运行边界；没有重试操作表单、M3 工作区、模型或实验；不承诺任意项目兼容、容量极限、ARM 或原生 Windows Worker。未重建当前业务镜像/迁移业务库，启用需按 README 正常构建启动，同时更新前后端并保留命名卷。数据库与核对进程均可用时才有期限收敛保证。修改前 222 个工程文件副本/摘要位于忽略目录 `.runtime/m2-t04-baseline`，审阅差异与清单分别为 `.runtime/m2-t04-review.diff`、`.runtime/m2-t04-file-review.json`；这些只是修改审计，不是任务进度来源。

最终审阅以标准输入执行 `python -B -X utf8 -`：核对修改前摘要和完整差异，UTF-8、Python 语法、空白、冲突标记、86 处本地 Markdown 链接及 18 个任务状态通过；旧 18 操作及所有原 Schema 组件逐项不变，仅新增 retries。依赖/锁文件、独立示例和人工测试数据摘要保持不变；后续任务均未开始。再次 Git 检查仍为非仓库。

本任务新增 4 个、修改 27 个文件，无删除。下列清单均相对项目根目录：

| 变更 | 文件 | 说明 |
| --- | --- | --- |
| 新增 | `backend/apps/jobs/retries.py` | 三类任务的重试协调 |
| 新增 | `backend/apps/jobs/migrations/0003_job_previous_job.py` | 可空原任务关联 |
| 新增 | `backend/apps/jobs/tests/test_retries.py` | API、幂等、并发、输入和历史验证 |
| 新增 | `backend/apps/jobs/tests/test_recovery.py` | 真实进程、队列故障、期限和迁移验证 |
| 修改 | `backend/apps/jobs/models.py` | 保存原任务关联 |
| 修改 | `backend/apps/jobs/services.py` | 重试幂等、统一投递故障、期限和脱敏 |
| 修改 | `backend/apps/jobs/api/views.py` | API-17 请求响应边界 |
| 修改 | `backend/apps/jobs/api/serializers.py` | 输出原任务 UUID |
| 修改 | `backend/apps/jobs/tests/test_contract.py` | 已实现路由清单 |
| 修改 | `backend/apps/projects/services.py` | 导入重试复用原提交流程 |
| 修改 | `backend/apps/projects/uploads.py` | 重试 multipart 有界接收 |
| 修改 | `backend/apps/projects/api/views.py` | 投递未确认提示与实际任务状态一致 |
| 修改 | `backend/apps/analysis/services.py` | 分析重试复用原提交流程 |
| 修改 | `backend/apps/analysis/api/views.py` | 投递未确认提示与实际任务状态一致 |
| 修改 | `backend/config/urls.py` | 注册重试路由 |
| 修改 | `infra/nginx/default.conf.template` | 重试上传代理上限 |
| 修改 | `frontend/src/features/jobs/api/jobs-api.ts` | 原任务关联运行时校验 |
| 修改 | `frontend/src/features/jobs/api/jobs-api.test.ts` | UUID 和自引用边界 |
| 修改 | `frontend/src/features/jobs/JobsPage.tsx` | 历史关联展示 |
| 修改 | `frontend/src/features/jobs/JobsPage.test.tsx` | 重新挂载恢复 |
| 修改 | `contracts/openapi.yaml` | 19 操作生成契约 |
| 修改 | `frontend/src/shared/api/generated/schema.d.ts` | 生成客户端类型 |
| 修改 | `AGENTS.md` | 当前能力边界 |
| 修改 | `README.md` | 重试使用、启用和验证说明 |
| 修改 | `docs/api-catalog.md` | API-17 细化及操作计数 |
| 修改 | `docs/api-conventions.md` | 重试与投递未确认语义 |
| 修改 | `docs/backend-guidelines.md` | 恢复职责与期限约束 |
| 修改 | `docs/frontend-guidelines.md` | 历史兼容边界 |
| 修改 | `docs/project-structure.md` | 重试模块与测试职责 |
| 修改 | `docs/roadmap.md` | 同步现状，保留后续边界 |
| 修改 | `docs/phase-1-plan.md` | 唯一任务进度和验收记录 |

### M3-T01 / M3-T02 / M3-T03 验收记录（2026-09-29）

范围与前置：按用户确认计划完成整个 M3，实施前重新检查根目录、适用 AGENTS、实际 M1/M2 源码、服务、Git 状态及需求/结构/API/前后端规范/路线图。仅根指令适用；目录不是 Git 仓库，没有初始化或进行 Git 写操作。未发现独立记忆文件，继续沿用项目文档。修改前 227 个工程文件保存于忽略目录 `.runtime/m3-baseline/files`，摘要为同目录 `manifest.json`；本次审阅不把既有 IDE 配置计入任务修改。

实现与取舍：独立 TypeScript 6.0.3 工程通过内存 CompilerHost 解析受控文本，固定 CLI 和版本协议，不执行导入项目。fetch、axios 固定配置、相对导入、直接调用与有限 React/Ant Design/TanStack 回调各自保留来源；源码包含与执行分派分别命名。后端按方法和完整路径保守关联，未知基础地址或重复目标仅作候选，动态请求保留断点。复用同一次分析、领取资格及事务发布，增加可空 frontend 和图 v2，历史 v1/未分析前端仍可读取且不回填。接口视角只回溯前端并展开后端下游；原 root_node_id 出边查询保留。新增依赖仅为独立解析器的 TypeScript/@types/node 和后端已有锁定 jsonschema 的直接声明，没有升级原应用依赖。

工作区已接通创建项目、ZIP 导入、显式根路由、分析、历史和失败重试；服务端数据由 Query 管理，选择由 History API/URL 管理，不新增路由、图或编辑器依赖。资源切换卸载旧请求并验证归属；迟到写结果不导航回旧工作区。未知提交只保存操作 UUID 与内容摘要，同输入恢复原操作，不自动重发。来源按当前快照清单及文件标识/摘要/行数核对，源码按 200 行分段读取。学习、模型和实验未实现。

环境与命令说明：根目录为 `F:/Program/Fall_Campus_Recruitment`；下表相对工作目录均在该根下。`python` 实际使用 `.runtime/m1-t02-venv/Scripts/python.exe`（3.13.15），`node` 为 `.runtime/tools/node-v24.21.0-win-x64/node.exe`（24.21.0），`npm` 由该 Node 执行同目录 `node_modules/npm/bin/npm-cli.js`（11.19.0），`docker` 为 `C:/Program Files/Docker/Docker/resources/bin/docker.exe`。只为当前进程补充 PATH。Linux 镜像以锁文件安装，验收项目固定 `learning-lab-m3-verify`，使用独立 PostgreSQL/Redis、卷、网络和回环 5175；原 5173/5174 服务未升级或重启。

| 工作目录 | 实际命令/检查 | 观察结果 |
| --- | --- | --- |
| 根目录 | `Get-Location`；`git status --short`；`git rev-parse --show-toplevel` | 路径正确；两项 Git 命令均报告 not a git repository；最终复查相同 |
| analyzers/typescript | `npm run typecheck`；`npm test`（包含 `npm run build`） | 最终 12 项通过；真实 CLI、别名/遮蔽、配置及客户端逃逸、axios 实例默认方法/自定义传输、重复 JSX 绑定、fetch/axios、人工示例链路、动态/外部目标、相对导入、语法失败、不执行源码、Unicode/LF 行号及 AST 超限 |
| analyzers/typescript | `node ../../frontend/node_modules/prettier/bin/prettier.cjs --check src tests package.json tsconfig.json --config ../../frontend/prettier.config.mjs` | 通过；仅格式化本次新增 package.json，没有重生成应用锁文件 |
| 根目录 | `docker build -f infra/docker/backend.Dockerfile -t learning-lab-backend:m3-verify .`；对应 frontend.Dockerfile/learning-lab-frontend:m3-verify 构建 | 两镜像构建成功，可信 Node/解析器进入后端镜像 |
| 根目录 | `docker compose -p learning-lab-m3-verify -f compose.yaml -f infra/docker/compose.m3-verify.yaml up -d --no-build --wait --wait-timeout 90 api worker reconciler frontend` | 独立服务健康，新增迁移成功；后续修订镜像再构建并在同一独立实例验证 |
| 根目录 | 下方完整 PostgreSQL pytest 命令 | 初次完整回归 286 项通过；最终解析规则及兼容回归加入后 287 项通过，38.89 秒；包括快照、迁移、幂等、图、故障恢复与事务回滚 |
| 根目录 | 同一下方命令，将测试路径改为 `apps/analysis/tests` | LF/协议完整性修订后 101 项通过；补充契约回归后 102 项通过，18.59 秒；旧图投影断言保持，未降低验收 |
| backend | `python -B -m pytest apps/analysis/tests/test_frontend.py::test_frontend_schema_preserves_job_status_enum --ds=config.settings.test -q -p no:cacheprovider --tb=short` | 最终契约兼容补充回归 1 项通过；保留原 StatusEnum 及 Job 引用，同时独立生成 FrontendMatchStatusEnum |
| backend | `python -m ruff check .`；`python -m ruff format --check .` | 通过，96 个文件符合格式 |
| backend | `python -m mypy config common apps tests --platform linux --no-incremental` | 91 个源文件通过；平台参数对应现有 Linux 存储/Worker 支持边界 |
| backend | `python -B manage.py check --settings config.settings.test`；`python -B manage.py makemigrations --check --dry-run --settings config.settings.test` | 0 个系统问题；No changes detected |
| backend | `python manage.py spectacular --settings config.settings.test --file ../contracts/openapi.yaml --validate --fail-on-warn` | 重新生成 19 个 HTTP 操作的契约；无新 HTTP 服务或端点 |
| frontend | `node tooling/generate-api-types.mjs`；`node node_modules/typescript/bin/tsc --noEmit` | 生成类型及类型检查通过 |
| frontend | `node node_modules/vitest/vitest.mjs run` | 7 个文件、33 项通过；入口、未知提交同键恢复、旧历史、候选/截断、跨快照来源、分段读取、轮询清理、迟到 GET/POST 与刷新恢复 |
| frontend | `node node_modules/vitest/vitest.mjs run src/app/WorkspacePage.test.tsx src/features/projects/SourceViewer.test.tsx` | 最终源码定位滚动修订后 8 项通过 |
| frontend | `node --test --test-concurrency=1 tooling/*.test.mjs` | 正常权限复跑后 11 项通过；类型补丁、生成漂移/缺失及不覆盖行为 |
| frontend | `node node_modules/eslint/bin/eslint.js . --max-warnings 0`；`node node_modules/prettier/bin/prettier.cjs --check .`；`node node_modules/vite/bin/vite.js build` | lint、格式和生产构建通过；最终 JS 473.82 kB / gzip 153.93 kB |
| 根目录 | `python -X utf8 scripts/check_contracts.py --node .runtime/tools/node-v24.21.0-win-x64/node.exe` | 工作台 19/示例 3 操作、文档表、保存 Schema、两端类型一致；11+31+11 项契约测试及两端 TypeScript 通过 |
| 根目录 | `python -B -X utf8 scripts/check_m3_workspace.py --project-id fb8caf4a-d6ac-4a29-8dc9-3cb9f0e5795c`；最终镜像再执行 `python -B -X utf8 scripts/check_m3_workspace.py` | 两次真实 HTTP 导入/分析同键重放、快照归属、模型源码均通过；6 确认、1 候选、2 未匹配、1 语法失败；POST 接口视图 12 节点/12 边且没有扩散到其他接口 |
| 根目录 | `python -m ruff check scripts/check_m3_workspace.py` | 通过；脚本仅使用标准库、固定独立回环实例，Cookie/令牌不输出、不持久化 |

本次实际执行的数据库测试命令（PowerShell，根目录）：

```powershell
& 'C:/Program Files/Docker/Docker/resources/bin/docker.exe' compose -p learning-lab-m3-verify -f compose.yaml -f infra/docker/compose.m3-verify.yaml run --rm --no-deps -e APP_PORT=5173 -e APP_ORIGIN=http://127.0.0.1:5173 -e PYTHONPYCACHEPREFIX=/tmp/m3-pycache -v 'F:/Program/Fall_Campus_Recruitment/backend:/workspace/backend:ro' -v 'F:/Program/Fall_Campus_Recruitment/contracts:/workspace/contracts:ro' -v 'F:/Program/Fall_Campus_Recruitment/analyzers:/workspace/analyzers:ro' -v 'F:/Program/Fall_Campus_Recruitment/examples:/workspace/examples:ro' -v 'F:/Program/Fall_Campus_Recruitment/testdata:/workspace/testdata:ro' -w /workspace/backend api python -B -m pytest apps tests --ds=config.settings.local -q -p no:cacheprovider --tb=short --maxfail=3
```

该命令只读挂载当前源码，测试库和 Redis 队列隔离。APP_PORT/APP_ORIGIN 仅覆盖一次性测试容器，使既有 APIClient 用例沿用其来源基线，不修改服务配置。前端解析测试实际运行可信 Node；导入 ZIP 中的源码只被解析，不运行其应用。

真实浏览器（内置浏览器、5175）：实际通过表单创建项目、文件选择器上传教学 ZIP、提交导入、打开快照、选择 backend/config/urls.py、提交分析及打开结果。选择 POST /api/v1/tasks/ 后可从 handleSubmit 的 Ant Design 入口证据，经 TanStack mutationFn、createTask、请求、DRF 接口/视图、TaskSerializer 到 Task；节点、关系和源码行号可逐项检查。刷新后保留模型来源，前进/后退恢复节点；Enter 激活接口/模型按钮、Tab 焦点轮廓可见。390×844 窗口 documentWidth=375，没有整页横向溢出。连续切换两个快照时旧源码立即消失，最终内容和 URL 归属新快照。另验证未知基础地址只显示候选、单文件语法失败显示部分结果、越界行号明确报错；最终镜像提交 empty_urls.py 成功显示无后端接口，同时保留前端与诊断。最终浏览器控制台无 error。

验收对应：AT-07 覆盖静态请求及样例链路，AT-08 覆盖未知基础地址/动态配置/重复目标与明确候选，AT-09 覆盖关系来源、源码位置及失效引用。AT-10 由组件测试的受控迟到 GET/POST 与真实浏览器的快照切换/返回旧结果共同验证，不包含未来讲解请求。AT-23 覆盖键盘/状态/焦点/窄窗口。失败任务重试、非法归属、旧图/旧分析、延迟响应与取消的更多分支由后端集成及前端行为测试验证；不把模拟延迟或故障注入写成真实停服。现有整机断电、磁盘耗尽、任意导入框架版本、ARM、生产容量及公网使用未验收。

失败与修复：最初 Docker 回归缺少 testdata 只读挂载，出现 63 项失败/196 项通过；第一次纠正误用了不存在的根 tests 目录，核对实际文件后改为 testdata，最终全量通过。Docker 由错误 bind 路径创建的空 tests 目录经确认为空后移除，未删除已有内容。Windows 默认 mypy 平台对既有 POSIX API 报错，使用项目支持的 linux 平台并修正新增测试类型后通过。沙箱下 pytest 临时目录权限和 Vitest/Node spawn EPERM 通过正常权限原命令复跑解决，没有放宽测试。新增前端测试的重复任务标识和 jsdom 文件表单提交方式按真实语义修正；AST 超限用例初始数据未到上限，增加测试输入后验证原限制生效。格式检查曾引用不存在的配置路径，查实 prettier.config.mjs 后检查并修正新增清单格式。全页截图工具失败，改用实际可见区域截图；不影响页面功能验收。

最终契约审阅还发现自动生成器把旧 StatusEnum 重命名为 JobStatusEnum。依据已安装 drf-spectacular 的选择值/标签哈希规则，枚举覆盖直接引用现有 Job.Status，重新生成后保留旧组件与 Job 结构不变。补充契约回归初始误放在数据库标记模块、使用了错误的只读引用形状及未注解的生成器调用；移到纯测试模块，复用既有 contract_schema 导出，并按原 allOf 引用验证后通过。最终 mypy、Ruff、Schema/前端类型和两套契约检查再次通过。源码审阅补齐 axios 实例默认方法、实例级自定义传输/客户端逃逸，以及 fetch 别名和重复 JSX 绑定边界；新增反例与最终 287 项后端回归通过，没有改动教学样例。

审计证据：修改前副本、当前文件摘要 `changes.json` 与完整文本差异 `review.diff` 位于 `.runtime/m3-baseline`，真实 HTTP 摘要为 `.runtime/m3-http-verification.json`，浏览器截图为 `.runtime/m3-workspace.png` 和 `.runtime/m3-workspace-narrow.png`。这些均为忽略的本地验证产物，不是第二套进度系统。经标准输入执行 `python -B -X utf8 -` 核对全部修改：36 新增、29 修改、0 删除；73 个保护文件摘要、87 处本地 Markdown 链接、18 个任务状态、UTF-8/Python/JSON 语法、空白及冲突标记通过。原 HTTP 路径/操作标识和所有旧 Schema 组件名称保留，仅六个已有图/分析相关组件扩展。独立示例、人工标注、前端依赖及其锁文件保持原内容；没有更改秘密文件。

项目记忆同步：读取阶段计划、需求、结构、API 清单/规范、前后端规范、路线图、README 与 AGENTS。更新本计划及 AGENTS、README、结构、API 清单/规范、前后端规范和路线图，统一 M3 职责、协议、图版本、历史兼容、源码和隔离验证命令。查实前端规范原 React Router 为目标设想，实际没有依赖；按已批准方案记录 History API。README 的“只有后端图/没有表单”已与源码及浏览器证据核对后修正。需求和任务提示词的边界未改变，保留原文和历史验收记录，不另建记忆文件。

结论：M3 三项完成，未启动 M4/M5。关键知识是静态证据不等于运行轨迹、词法包含不等于调用、快照归属与行号必须同时校验，以及未知写结果需要保留原幂等操作。取舍是有限 AST/框架规则、候选显式保留、可空历史字段和原生 History API，以控制误报与依赖成本。手工复核点：在 5175 选择 POST /api/v1/tasks/，核对 handleSubmit 的框架回调来源及 Task 模型第 6–19 行，再切换快照观察旧来源立即清除。独立验收实例保留供复核；日常 5173 工作台仍为原镜像，本次未执行其升级或部署。

本任务工程文件共 65 个：36 个新增、29 个修改、无删除。以下路径相对项目根目录；运行缓存、镜像和截图不计入源码清单。

| 变更 | 文件 | 说明 |
| --- | --- | --- |
| 修改 | `.dockerignore` | 仅允许可信解析工程及协议进入镜像上下文 |
| 修改 | `AGENTS.md` | 同步 M3 实际能力与后续边界 |
| 修改 | `README.md` | 工作区入口、隔离验收及实际运行说明 |
| 新增 | `analyzers/typescript/package-lock.json` | 锁定独立解析器依赖 |
| 新增 | `analyzers/typescript/package.json` | 解析器清单及类型/测试/构建入口 |
| 新增 | `analyzers/typescript/src/cli.ts` | 有界 JSON 输入输出及固定失败协议 |
| 新增 | `analyzers/typescript/src/parse-source.ts` | 内存 AST、作用域、请求和有限框架关系 |
| 新增 | `analyzers/typescript/src/protocol.ts` | 版本化协议、预算与输入输出校验 |
| 新增 | `analyzers/typescript/tests/parse-source.test.mjs` | 解析、反例、样例关系及不执行输入测试 |
| 新增 | `analyzers/typescript/tsconfig.json` | 独立严格 NodeNext 类型配置 |
| 修改 | `backend/apps/analysis/api/serializers.py` | 前端摘要、关系字段及查询校验 |
| 修改 | `backend/apps/analysis/api/views.py` | 端点关联摘要和接口视角 API |
| 新增 | `backend/apps/analysis/associations.py` | 有界方法/路径关联、候选及扩图 |
| 新增 | `backend/apps/analysis/frontend_runner.py` | 固定 Node 调用、超限回收与协议完整性 |
| 新增 | `backend/apps/analysis/frontend_types.py` | 内部前端结果及关联类型 |
| 修改 | `backend/apps/analysis/graph.py` | 图 v1/v2 校验及指定接口上下游查询 |
| 新增 | `backend/apps/analysis/migrations/0003_analysis_frontend.py` | 可空前端结果，不回填历史 |
| 修改 | `backend/apps/analysis/models.py` | 保存前端解析及关联结果 |
| 修改 | `backend/apps/analysis/services.py` | 顺序分析、原子发布及历史只读验证 |
| 新增 | `backend/apps/analysis/tests/test_frontend.py` | 跨进程协议、关联、图范围和枚举兼容测试 |
| 新增 | `backend/apps/analysis/tests/test_frontend_api.py` | 持久化、历史、分页筛选及失败重试测试 |
| 修改 | `backend/apps/analysis/tests/test_graph_api.py` | 保留旧数据断言并恢复到新增迁移 |
| 修改 | `backend/apps/analysis/types.py` | 新图版本与前端节点/关系类型 |
| 修改 | `backend/apps/jobs/api/views.py` | 可选 kind/snapshot_id 筛选及分页保留 |
| 修改 | `backend/config/settings/base.py` | 稳定原枚举名称与新增匹配枚举 |
| 修改 | `backend/pyproject.toml` | 声明实际使用的既有 jsonschema 直接依赖 |
| 修改 | `backend/uv.lock` | 仅同步直接依赖元数据，不升级版本 |
| 修改 | `contracts/openapi.yaml` | 重新生成 M3 扩展契约 |
| 新增 | `contracts/typescript-analysis.schema.json` | 版本化跨进程 JSON Schema |
| 修改 | `docs/api-catalog.md` | 已实现字段、查询与版本追踪 |
| 修改 | `docs/api-conventions.md` | M3 来源、历史和兼容语义 |
| 修改 | `docs/backend-guidelines.md` | 受控解析、资源预算和保守规则 |
| 修改 | `docs/frontend-guidelines.md` | URL/Query/操作恢复和源码边界 |
| 修改 | `docs/phase-1-plan.md` | 唯一状态、验收记录及逐文件清单 |
| 修改 | `docs/project-structure.md` | 实际组件、职责及依赖方向 |
| 修改 | `docs/roadmap.md` | 当前 M3 能力和 M4/M5 边界 |
| 修改 | `frontend/index.html` | 工作区页面标题 |
| 新增 | `frontend/src/app/WorkspacePage.test.tsx` | 入口、刷新、切换及迟到响应行为测试 |
| 新增 | `frontend/src/app/WorkspacePage.tsx` | 项目/快照工作区编排及归属隔离 |
| 修改 | `frontend/src/app/main.tsx` | 启用工作区入口 |
| 新增 | `frontend/src/app/workspace-location.ts` | History API、URL 校验和选择恢复 |
| 新增 | `frontend/src/app/workspace.css` | 工作区布局、焦点与窄窗口样式 |
| 新增 | `frontend/src/features/analysis/AnalysisBrowser.tsx` | 关系、候选、覆盖和来源诊断 |
| 新增 | `frontend/src/features/analysis/AnalysisNavigator.tsx` | 根路由提交与服务端分析历史 |
| 新增 | `frontend/src/features/analysis/api/analysis-api.ts` | 分析/端点/图/诊断请求及运行时校验 |
| 新增 | `frontend/src/features/analysis/index.ts` | analysis 模块公开入口 |
| 新增 | `frontend/src/features/jobs/JobStatus.test.tsx` | 轮询清理和导入重试行为测试 |
| 新增 | `frontend/src/features/jobs/JobStatus.tsx` | 任务查询、结果及显式失败重试 |
| 修改 | `frontend/src/features/jobs/JobsPage.tsx` | 保留系统任务历史分页地址 |
| 修改 | `frontend/src/features/jobs/api/jobs-api.ts` | 任务详情、筛选和重试请求 |
| 新增 | `frontend/src/features/jobs/index.ts` | jobs 模块公开入口 |
| 新增 | `frontend/src/features/projects/ProjectNavigator.tsx` | 项目创建、快照导航与 ZIP 导入 |
| 新增 | `frontend/src/features/projects/SourceViewer.test.tsx` | 源码归属、摘要和分段边界测试 |
| 新增 | `frontend/src/features/projects/SourceViewer.tsx` | 只读源码定位、拒绝失效引用及分段 |
| 新增 | `frontend/src/features/projects/api/projects-api.ts` | 项目/导入/文件清单/内容请求及校验 |
| 新增 | `frontend/src/features/projects/index.ts` | projects 模块公开入口 |
| 修改 | `frontend/src/shared/api/client.ts` | JSON/multipart 写请求和取消传递 |
| 修改 | `frontend/src/shared/api/generated/schema.d.ts` | 从新契约生成客户端类型 |
| 新增 | `frontend/src/shared/api/validation.ts` | 共享结构、分页与来源运行时校验 |
| 新增 | `frontend/src/shared/components/Feedback.tsx` | 可见错误与显式读取重试 |
| 新增 | `frontend/src/shared/components/PageControls.tsx` | 有界分页操作 |
| 新增 | `frontend/src/shared/hooks/useIdempotentOperation.ts` | 未知写结果的原操作恢复和卸载保护 |
| 修改 | `infra/docker/backend.Dockerfile` | 构建并固定可信 Node 解析器 |
| 新增 | `infra/docker/compose.m3-verify.yaml` | 独立 5175 镜像、服务和运行入口 |
| 新增 | `scripts/check_m3_workspace.py` | 独立回环 HTTP 集成验收及安全摘要 |

### M4 本地讲解与固定练习记录（2026-09-29）

范围：M4-T01/T02/T03 及必要契约、测试、打包和文档同步。先重新核对目录、根 AGENTS、需求、计划、结构、API、前后端规范、路线图和实际源码；根目录 `git status --short` 仍返回 `not a git repository`。无独立项目记忆，进度只在本文维护。未安装依赖、未改锁文件、未执行导入项目代码、未进行 Git 写操作或真实模型调用。修改前非敏感工程文件副本与 SHA-256 基线位于 `.runtime/m4-baseline`。

实现与取舍：标准库 Chat Completions 单次非流式请求，子进程保证最多 60 秒总期限并回收，有界响应 262,144 字节；完整消息默认 65,536 字节、最多 4,096 输出 token，参数只能显式配置且不失败换参重发。精确消息、配置、片段、模板和来源随预览保存，服务端单次确认与任务同事务消费；配置失效、跨快照或非法引用明确拒绝。`explanation` 复用原任务四态、原子发布、期限核对和显式重试；新确认不消除供应商可能已计费的不确定性。纯文本结构化展示避免新增 Markdown/HTML 执行面。

学习内容为 5 张卡片和 3 类固定题，绑定 `task-board/1.0.0` 的 9 个规范化源码摘要及创建任务接口。内容通过显式 `load_learning_content` 幂等导入；同版本内容漂移拒绝，作答追加保存且答案只在提交反馈中返回。服务端同时校验快照、分析、接口、题目版本和类型化答案；提示使用单独记录。知识卡片和答案由本轮实现者逐项对照源码、现有人工关系基准及行为测试，不将此称为用户或其他人员的独立人工审阅。FR-06 的该审阅边界仍待完成，不宣称学习效果或掌握程度已经验证。

参考环境沿用现有固定 Python 3.13.15、Node 24.21.0、锁定依赖及 Linux Docker。下表中 `P` 表示 `F:/Program/Fall_Campus_Recruitment/.runtime/m1-t02-venv/Scripts/python.exe`，`N` 表示 `F:/Program/Fall_Campus_Recruitment/.runtime/tools/node-v24.21.0-win-x64/node.exe`；命令通过 PowerShell 调用该完整路径。Docker 使用 `C:/Program Files/Docker/Docker/resources/bin/docker.exe`。

| 工作目录 | 实际命令或操作 | 观察结果 |
| --- | --- | --- |
| backend | `P -B -m pytest apps/explanations/tests/test_adapter.py --ds=config.settings.test -q -p no:cacheprovider --tb=short` | 37 项本地 HTTP/配置/结构/引用与安全用例通过；无真实服务请求 |
| backend（隔离容器） | `python -B -m pytest apps/explanations/tests apps/learning/tests apps/jobs/tests apps/projects/tests apps/analysis/tests --ds=config.settings.local -q -p no:cacheprovider --tb=short` | 317 项通过，最终 55.66 秒（上一轮 55.91 秒）；真实 PostgreSQL、Redis 和 Worker，见下方只读挂载入口 |
| backend（隔离容器） | `python -B -m pytest apps/learning/tests/test_learning.py --ds=config.settings.local -q -p no:cacheprovider --tb=short` | 最后补充快照与分析不匹配的拒绝断言后，4 项通过，6.21 秒 |
| backend | `P -m ruff check .`；`P -m ruff format --check .` | 通过；133 个文件格式符合要求 |
| backend | `P -m mypy config common apps tests --platform linux --no-incremental` | 严格类型检查通过，128 个源文件；按产品 Linux 平台检查既有 POSIX API |
| backend | `P -B manage.py makemigrations --check --dry-run --settings=config.settings.test` | No changes detected；新增两个应用迁移已在独立库执行 |
| backend | `P -m ruff check apps/learning/tests/test_learning.py ../scripts/check_m4_workspace.py`；对应 `ruff format --check` | 最后补充测试及验收脚本检查通过 |
| 根目录 | `P -B scripts/check_contracts.py --node .runtime/tools/node-v24.21.0-win-x64/node.exe` | 两套 OpenAPI 无漂移，11+36+11 项契约检查及两套前端生成类型/TypeScript 通过 |
| frontend | `N node_modules/vitest/vitest.mjs run` | 9 个文件、42 项通过，29.41 秒 |
| frontend | `N node_modules/eslint/bin/eslint.js . --max-warnings 0`；`N node_modules/prettier/bin/prettier.cjs --check .` | 通过 |
| 根目录 | `docker compose -p learning-lab-m4-verify -f compose.yaml -f infra/docker/compose.m4-verify.yaml build api frontend` | 后端/前端生产镜像构建通过；沿用缓存中的锁定依赖，包含 TypeScript/Vite 构建 |
| 根目录 | `P -B -X utf8 scripts/check_m4_workspace.py` | 模型关闭时三类题、幂等、历史通过；预览返回 MODEL_NOT_CONFIGURED |
| 根目录 | `P -B -X utf8 scripts/check_m4_workspace.py --model-double` | 5176 固定模型替身完整 HTTP 流程通过：拒绝和保存确认不创建讲解任务、单次提交重放返回原任务、结果可读取 |
| 根目录 | `docker compose -p learning-lab-m4-verify -f compose.yaml -f infra/docker/compose.m4-verify.yaml -f infra/docker/compose.m4-double.yaml restart postgres redis api worker reconciler frontend`；随后 `P -B -X utf8 scripts/check_m4_workspace.py --verify-history` | 实际重启六个服务后，6 条历史资源仍可读取，包含快照、分析、3 次作答和讲解 |
| 根目录 | `docker compose -p learning-lab-m4-verify -f compose.yaml -f infra/docker/compose.m4-verify.yaml up -d --no-build --wait` | 验收后恢复默认模型关闭配置，保留数据；所有服务健康 |
| 根目录 | `P -B -X utf8 scripts/check_task_board_annotations.py` | 12 个节点、12 条关系引用检查通过 |
| 根目录 | `docker exec learning-lab-m4-verify-frontend-1 sh -c 'if grep -R -l -F "TaskSerializer 要求 title 为非空白字符串" /usr/share/nginx/html; then exit 1; else printf "固定答案文本未进入前端构建产物\n"; fi'` | 指定标准答案文本未打包；题目 API 不泄漏答案另有结构和实际响应测试 |
| 根目录 | `docker ps --format '{{.Names}} \| {{.Status}} \| {{.Ports}}'` | 独立 5176 为回环入口；原 5173/5174/5175 运行时长未重置 |

后端集成使用下列 Compose 入口：仅新建临时测试容器和测试库，挂载源码为只读，Redis 测试队列随机隔离。应用的内部依赖运行于 `learning-lab-m4-verify` 独立项目和数据卷，不复用已有工作台数据。聚焦学习测试不需要 testdata 挂载，其余保持相同。

```powershell
& 'C:/Program Files/Docker/Docker/resources/bin/docker.exe' compose -p learning-lab-m4-verify -f compose.yaml -f infra/docker/compose.m4-verify.yaml run --rm --no-deps -e APP_PORT=5173 -e APP_ORIGIN=http://127.0.0.1:5173 -e PYTHONPYCACHEPREFIX=/tmp/m4-pycache -v 'F:/Program/Fall_Campus_Recruitment/backend:/workspace/backend:ro' -v 'F:/Program/Fall_Campus_Recruitment/contracts:/workspace/contracts:ro' -v 'F:/Program/Fall_Campus_Recruitment/content:/workspace/content:ro' -v 'F:/Program/Fall_Campus_Recruitment/analyzers:/workspace/analyzers:ro' -v 'F:/Program/Fall_Campus_Recruitment/examples:/workspace/examples:ro' -v 'F:/Program/Fall_Campus_Recruitment/testdata:/workspace/testdata:ro' -w /workspace/backend api python -B -m pytest apps/explanations/tests apps/learning/tests apps/jobs/tests apps/projects/tests apps/analysis/tests --ds=config.settings.local -q -p no:cacheprovider --tb=short
```

真实浏览器验证（内置浏览器、5176）：键盘准备预览，显示目标、模型、全部模板与片段；拒绝后可继续练习。错误预测提交错误答案后显示固定反馈，刷新恢复所选作答及版本。保存确认与提交分别操作，本地替身任务成功后五段讲解可读，引用按钮定位 `backend/apps/tasks/api/serializers.py` 第 8–30 行；用量缺失显示未知，替身内容明确标注没有真实模型调用。恢复模型关闭后，新预览明确提示未启用，旧讲解仍可读取。切换项目后 URL 只保留新项目，旧讲解/作答/源码清除。390×844 下面板可切换、键盘核心操作可用，页面宽度 375，无整页横向溢出。截图 `.runtime/m4-workspace.png`、`.runtime/m4-workspace-narrow.png` 为本地验收证据。

AT 对应：AT-11 的预览内容、单次确认、拒绝零外发及配置变化；AT-12 的未配置、错误分类、总期限与不自动重发；AT-13 的跨快照、虚构/越界/未预览引用和缺失依据；AT-14 的不可信输入、非法结构、HTML/危险链接/工具调用，均经本地替身和边界测试。AT-15 覆盖三类题的正确/错误/非法答案、内容/答案版本和摘要不匹配。M4 相关 AT-10/18/19/20/23 覆盖迟到响应、取消、历史重启、并发幂等、投递失败、真实 Worker 进程中断、期限核对、迟到发布和新确认重试；不包含 M5 实验验收或真实供应商兼容/提示注入抵抗效果。

失败与修复：首次较广回归 311 通过、1 失败，旧测试将新实现的 explanation 当作未知任务，改用 unsupported_kind 后保留原 409 断言，最终 317 通过。浏览器首次历史查询因原 4 个参数上限返回 500；新增历史需要三个筛选加两个分页字段，调整到 5 并将超限明确映射 400，补充分页和六参数反例。补充测试第一次漏挂载 analyzers，4 个 fixture 失败；补齐只读挂载后全部通过。Windows 沙箱临时目录 WinError 5 与 Vitest spawn EPERM 使用相同命令在正常权限复跑；未减弱检查。Ruff 从根目录显式指定配置时把 common 识别为外部模块，回到规定 backend 工作目录通过，不因此重排业务导入。查询覆盖文件时两次使用错误相对路径/PowerShell 通配参数，按实际 `infra/docker` 路径纠正，只读错误未改动文件。

审阅与记忆同步：基线遗漏了两份既有 `.prettierignore`，其修改时间早于基线，且 M3 文档已记载；这两份文件未修改，不计入 M4 新增。比较确认 81 个保护文件（教学示例、人工基准、解析器、依赖清单/锁文件、需求/任务提示词等）摘要不变，原有 19 个 HTTP 操作标识、旧 Schema 名称与 KindEnum/StatusEnum/FrontendMatchStatusEnum/Job 保持兼容。9 个内容源摘要及引用行号、87 处文档本地链接、修订表、UTF-8、Python/JSON 语法、空白和冲突标记检查通过；新增内容未发现所检疑似密钥模式。完整差异与清单位于 `.runtime/m4-baseline/review.diff`、`changes.json`，HTTP 摘要位于 `.runtime/m4-http-verification.json`，均为本地审计产物，非平行项目记忆。

更新本文、AGENTS、README、结构、API 清单/规范、前后端规范与路线图，统一已实现组件、32 个操作、配置、版本内容维护、隔离运行和未验收边界；保留旧任务记录作为历史，不改需求或任务模板语义。README 原 25 MiB 上传说明与后端 20 MiB 默认限制不一致是已有范围外观察，本次不调整导入行为。未发现新增秘密、临时调试代码、依赖或导入示例改动。

结论：本地实现和必要验证交付；M4-T02 完成，T01/T03 保留上述未验收项，M4 整体不标全部完成。关键知识是单次确认与事务幂等、引用有效性与结论正确性的区别、静态预期与实验观测的区别，以及版本化内容和追加历史。手工复核点：打开 5176 的创建任务接口，查看错误预测固定反馈并刷新；确认版本、提示标志和旧记录保留。下一步如需真实供应商验证，应另行明确服务、模型、凭据准备和调用预算；不自动调用或推进 M5。

本任务工程文件共 90 个：51 新增、39 修改、0 删除。两份既有 `.prettierignore` 未改动，不在清单中。

| 变更 | 文件 | 说明 |
| --- | --- | --- |
| 新增 | `backend/apps/explanations/__init__.py` | 当前任务所需 Python 包入口 |
| 新增 | `backend/apps/explanations/adapter.py` | 讲解预览、单次确认、模型或引用边界 |
| 新增 | `backend/apps/explanations/api/__init__.py` | 当前任务所需 Python 包入口 |
| 新增 | `backend/apps/explanations/api/serializers.py` | 讲解预览、单次确认、模型或引用边界 |
| 新增 | `backend/apps/explanations/api/urls.py` | 讲解预览、单次确认、模型或引用边界 |
| 新增 | `backend/apps/explanations/api/views.py` | 讲解预览、单次确认、模型或引用边界 |
| 新增 | `backend/apps/explanations/configuration.py` | 讲解预览、单次确认、模型或引用边界 |
| 新增 | `backend/apps/explanations/context.py` | 讲解预览、单次确认、模型或引用边界 |
| 新增 | `backend/apps/explanations/migrations/0001_initial.py` | 新增当前模块数据表及唯一约束迁移 |
| 新增 | `backend/apps/explanations/migrations/__init__.py` | 当前任务所需 Python 包入口 |
| 新增 | `backend/apps/explanations/models.py` | 讲解预览、单次确认、模型或引用边界 |
| 新增 | `backend/apps/explanations/services.py` | 讲解预览、单次确认、模型或引用边界 |
| 新增 | `backend/apps/explanations/tasks.py` | 讲解预览、单次确认、模型或引用边界 |
| 新增 | `backend/apps/explanations/tests/__init__.py` | 当前任务所需 Python 包入口 |
| 新增 | `backend/apps/explanations/tests/double_worker.py` | 当前模块边界、故障和交互回归 |
| 新增 | `backend/apps/explanations/tests/test_adapter.py` | 当前模块边界、故障和交互回归 |
| 新增 | `backend/apps/explanations/tests/test_contract.py` | 当前模块边界、故障和交互回归 |
| 新增 | `backend/apps/explanations/tests/test_explanations.py` | 当前模块边界、故障和交互回归 |
| 新增 | `backend/apps/explanations/tests/test_recovery.py` | 当前模块边界、故障和交互回归 |
| 新增 | `backend/apps/explanations/transport_worker.py` | 讲解预览、单次确认、模型或引用边界 |
| 新增 | `backend/apps/explanations/validation.py` | 讲解预览、单次确认、模型或引用边界 |
| 新增 | `backend/apps/learning/__init__.py` | 当前任务所需 Python 包入口 |
| 新增 | `backend/apps/learning/api/__init__.py` | 当前任务所需 Python 包入口 |
| 新增 | `backend/apps/learning/api/serializers.py` | 版本化教学内容、适用性或作答持久化 |
| 新增 | `backend/apps/learning/api/urls.py` | 版本化教学内容、适用性或作答持久化 |
| 新增 | `backend/apps/learning/api/views.py` | 版本化教学内容、适用性或作答持久化 |
| 新增 | `backend/apps/learning/content.py` | 版本化教学内容、适用性或作答持久化 |
| 新增 | `backend/apps/learning/management/__init__.py` | 当前任务所需 Python 包入口 |
| 新增 | `backend/apps/learning/management/commands/__init__.py` | 当前任务所需 Python 包入口 |
| 新增 | `backend/apps/learning/management/commands/load_learning_content.py` | 版本化教学内容、适用性或作答持久化 |
| 新增 | `backend/apps/learning/migrations/0001_initial.py` | 新增当前模块数据表及唯一约束迁移 |
| 新增 | `backend/apps/learning/migrations/__init__.py` | 当前任务所需 Python 包入口 |
| 新增 | `backend/apps/learning/models.py` | 版本化教学内容、适用性或作答持久化 |
| 新增 | `backend/apps/learning/services.py` | 版本化教学内容、适用性或作答持久化 |
| 新增 | `backend/apps/learning/tests/__init__.py` | 当前任务所需 Python 包入口 |
| 新增 | `backend/apps/learning/tests/test_learning.py` | 当前模块边界、故障和交互回归 |
| 新增 | `backend/common/serializers.py` | M4 复用的严格输入、分页、错误或 Schema 边界 |
| 新增 | `content/exercises/task-board-create.json` | 首批固定版本教学内容与维护来源 |
| 新增 | `content/knowledge/request-basics.json` | 首批固定版本教学内容与维护来源 |
| 新增 | `frontend/src/features/explanations/ExplanationPanel.test.tsx` | 当前模块边界、故障和交互回归 |
| 新增 | `frontend/src/features/explanations/ExplanationPanel.tsx` | 讲解预览、确认、结果与服务请求 |
| 新增 | `frontend/src/features/explanations/api/explanations-api.ts` | 讲解预览、确认、结果与服务请求 |
| 新增 | `frontend/src/features/explanations/index.ts` | 讲解预览、确认、结果与服务请求 |
| 新增 | `frontend/src/features/learning/LearningPanel.test.tsx` | 当前模块边界、故障和交互回归 |
| 新增 | `frontend/src/features/learning/LearningPanel.tsx` | 三类题、提示、反馈与历史服务请求 |
| 新增 | `frontend/src/features/learning/api/learning-api.ts` | 三类题、提示、反馈与历史服务请求 |
| 新增 | `frontend/src/features/learning/index.ts` | 三类题、提示、反馈与历史服务请求 |
| 新增 | `infra/docker/compose.m4-double.yaml` | 无凭据无出口的显式替身入口 |
| 新增 | `infra/docker/compose.m4-verify.yaml` | 独立 5176 模型关闭验收配置 |
| 新增 | `infra/docker/compose.model.yaml` | 仅显式启用的 Worker 模型出口和 secret |
| 新增 | `scripts/check_m4_workspace.py` | 三类题、确认、幂等和重启历史 HTTP 验收 |
| 修改 | `.dockerignore` | 仅将教学内容纳入后端构建上下文 |
| 修改 | `.env.example` | 增加可选模型 token 参数与密钥文件占位说明 |
| 修改 | `AGENTS.md` | 同步当前能力和未验收边界 |
| 修改 | `README.md` | M4 使用、配置、内容维护和隔离验收入口 |
| 修改 | `backend/apps/analysis/api/schema.py` | 公共 Schema 有类型覆盖后移除过时 ignore |
| 修改 | `backend/apps/jobs/api/serializers.py` | 接入 explanation 四态、结果与显式重试 |
| 修改 | `backend/apps/jobs/api/views.py` | 接入 explanation 四态、结果与显式重试 |
| 修改 | `backend/apps/jobs/retries.py` | 接入 explanation 四态、结果与显式重试 |
| 修改 | `backend/apps/jobs/services.py` | 接入 explanation 四态、结果与显式重试 |
| 修改 | `backend/apps/jobs/tests/test_contract.py` | 当前模块边界、故障和交互回归 |
| 修改 | `backend/apps/jobs/tests/test_retries.py` | 保留未知类型拒绝断言，更换已实现的占位类型 |
| 修改 | `backend/apps/projects/api/schema.py` | 公共 Schema 有类型覆盖后移除过时 ignore |
| 修改 | `backend/common/api.py` | M4 复用的严格输入、分页、错误或 Schema 边界 |
| 修改 | `backend/common/errors.py` | M4 复用的严格输入、分页、错误或 Schema 边界 |
| 修改 | `backend/common/schema.py` | M4 复用的严格输入、分页、错误或 Schema 边界 |
| 修改 | `backend/config/environment.py` | 注册 M4 应用、路由和默认关闭的模型配置 |
| 修改 | `backend/config/settings/base.py` | 注册 M4 应用、路由和默认关闭的模型配置 |
| 修改 | `backend/config/settings/local.py` | 注册 M4 应用、路由和默认关闭的模型配置 |
| 修改 | `backend/config/urls.py` | 注册 M4 应用、路由和默认关闭的模型配置 |
| 修改 | `compose.yaml` | 迁移后显式幂等加载教学内容 |
| 修改 | `contracts/openapi.yaml` | 生成 32 个工作台操作契约 |
| 修改 | `docs/api-catalog.md` | 同步 M4 职责、协议或运行边界 |
| 修改 | `docs/api-conventions.md` | 同步 M4 职责、协议或运行边界 |
| 修改 | `docs/backend-guidelines.md` | 同步 M4 职责、协议或运行边界 |
| 修改 | `docs/frontend-guidelines.md` | 同步 M4 职责、协议或运行边界 |
| 修改 | `docs/phase-1-plan.md` | 唯一任务状态、实际验证及逐文件变更记录 |
| 修改 | `docs/project-structure.md` | 同步 M4 职责、协议或运行边界 |
| 修改 | `docs/roadmap.md` | 同步 M4 职责、协议或运行边界 |
| 修改 | `frontend/src/app/WorkspacePage.tsx` | 工作区面板、URL 恢复或响应式布局 |
| 修改 | `frontend/src/app/workspace-location.ts` | 工作区面板、URL 恢复或响应式布局 |
| 修改 | `frontend/src/app/workspace.css` | 工作区面板、URL 恢复或响应式布局 |
| 修改 | `frontend/src/features/jobs/JobStatus.tsx` | 讲解任务类型、状态与结果链接 |
| 修改 | `frontend/src/features/jobs/JobsPage.tsx` | 讲解任务类型、状态与结果链接 |
| 修改 | `frontend/src/features/jobs/api/jobs-api.ts` | 讲解任务类型、状态与结果链接 |
| 修改 | `frontend/src/shared/api/generated/schema.d.ts` | 从 OpenAPI 生成 M4 前端类型 |
| 修改 | `frontend/src/shared/api/validation.ts` | M4 请求校验或明确未受理操作恢复 |
| 修改 | `frontend/src/shared/hooks/useIdempotentOperation.ts` | M4 请求校验或明确未受理操作恢复 |
| 修改 | `infra/docker/backend.Dockerfile` | 后端镜像包含教学内容 |
| 修改 | `scripts/check_contracts.py` | 纳入 M4 无数据库契约检查 |

### M5 实验与本地交付记录（2026-09-29）

**范围与结论。** 已完成 M5-T01 至 M5-T04 的本地实现、必要回归、演示和交付归档。开始前重新检查根目录、根 AGENTS、阶段计划、需求、结构、API、两端规范与路线图；没有更深层 AGENTS，也不是 Git 仓库。基于实际文件确认 M4 本地能力存在，但真实模型兼容与独立人工内容审阅没有验收。用户明确允许先完成 M5 本地实现与验证并保留这些前置缺口；因此本节不宣布 M4 或 v0.1 完成，不把替身结果当作供应商兼容证据。

先陈述中文计划，再实现固定实验、执行测试并同步文档。修改前对 313 个非敏感工程文件保存本地 SHA-256 与副本；没有读取秘密、执行导入源码、安装新依赖、改锁文件、初始化 Git、提交、发布或部署。使用独立 `learning-lab-m5-verify` 和首次为空的命名数据卷，入口仅为 `127.0.0.1:5177`；原实例未升级或重启。临时基线、HTTP 证据和截图均在已忽略的 `.runtime`，不是新的项目进度来源。

**实现与取舍。** 工作台新增五个 labs 操作，复用四态 Job、幂等键、领取标识、期限核对与显式重试。LabRun 保存定义和预测副本，逐步持久化实际响应、计数及耗时；学习快照在 LabRun 上关联，Job.snapshot_id=null，避免把内置执行误称为运行导入项目。前端要求先填四组预测，再展示实际观测和历史；重试按 job_id 独立查找新运行，避免历史分页或旧 run 阻止新结果出现。

独立示例仅在专用配置加载内部实验 app，复用原 TaskSerializer 与写入服务；原九个教学源码文件及人工基准摘要不变。固定传输子进程不接收用户 URL、脚本、命令或镜像，禁用代理与重定向，单请求 2 秒、子进程 6 秒、响应体 16 KiB。每次运行及 case 派生操作键；事务锁保护写入/关闭，关闭标记拒绝迟到写入，120 秒到期加每 5 秒核对兜底。与共享示例普通任务相比，按运行身份计数和清理更容易证明隔离；保留关闭标记有存储增长代价，首版没有自动归档机制。

预测错误不改变真实结果；HTTP 成功也不等于观测和清理完整。不可用时保存失败，响应不完整时保留已知内容与 null 后计数，进程在写入后退出时保持未知而非补造记录。清理未确认的历史不会因稍后回收而静默改成成功。数据库不可用期间不承诺准时清理，恢复后由核对进程继续处理。

#### 参考环境、规模和实际资源

- Windows NT 10.0.26200，Intel Core i7-13700K，16 核/24 逻辑处理器，物理内存 34,063,396,864 字节（约 31.72 GiB）；Docker Linux x86_64 引擎 29.4.0、Compose 5.1.1，24 vCPU、16,623,611,904 字节（约 15.48 GiB）分配内存。
- 固定 Python 3.13.15、Node 24.21.0；依赖仍使用原锁文件。输入为 `task-board/1.0.0` 的 9 个教学源码文件，解压 22,863 字节、ZIP 10,199 字节。镜像与工具使用已有缓存；本次“干净”指独立项目和空业务卷，不代表新宿主安装、无缓存下载或全平台支持。
- 一次模型关闭的真实 HTTP 闭环（导入、分析、三类作答、两次实验及幂等检查）实测 8.586 秒；停示例后的失败检查 0.565 秒；恢复后两次新运行加显式重试 9.806 秒；固定模型替身闭环 9.511 秒。不是重复性能基准，主机上仍有其他实例运行。
- 一次流程结束后的资源快照：api 161.9 MiB、worker 115.2、reconciler 62.97、PostgreSQL 56.05、Redis 9.047、frontend 19.42、示例 API 125.8、示例 PostgreSQL 48.43、lab-reconciler 54.35，合计约 653.17 MiB。相应 CPU 分别为 0.01%、0.03%、0.48%、0.42%、1.69%、0%、0.01%、0%、0%。这不是峰值、压力容量或最低硬件承诺。
- 最终前端构建 JS 503.14 kB（gzip 161.62 kB）、CSS 10.99 kB；构建通过，但保留 Vite 的大于 500 kB 分块警告。本次没有为此进行无关拆包重构。
- 本地固定替身用量为 null（未知），未调用真实模型、未产生真实调用费用。不能据此给出模型 token 或费用性能结论。

#### 实际命令与结果

下表的根目录为 `F:\Program\Fall_Campus_Recruitment`。为完整保存可复现参数，定义以下命令前缀；表中引用表示逐项展开这些固定参数，不是另一个脚本：

```powershell
$M5Python = 'F:/Program/Fall_Campus_Recruitment/.runtime/m1-t02-venv/Scripts/python.exe'
$M5Node = 'F:/Program/Fall_Campus_Recruitment/.runtime/tools/node-v24.21.0-win-x64/node.exe'
$M5Docker = 'C:/Program Files/Docker/Docker/resources/bin/docker.exe'
$M5Compose = @('compose', '-p', 'learning-lab-m5-verify', '-f', 'compose.yaml', '-f', 'infra/docker/compose.m5-verify.yaml', '--profile', 'task-board')
$M5Double = @('compose', '-p', 'learning-lab-m5-verify', '-f', 'compose.yaml', '-f', 'infra/docker/compose.m5-verify.yaml', '-f', 'infra/docker/compose.m4-double.yaml', '--profile', 'task-board')
$M5BackendTest = @('run', '--rm', '--no-deps', '-e', 'APP_PORT=5173', '-e', 'APP_ORIGIN=http://127.0.0.1:5173', '-v', 'F:/Program/Fall_Campus_Recruitment/backend:/workspace/backend:ro', '-v', 'F:/Program/Fall_Campus_Recruitment/content:/workspace/content:ro', '-v', 'F:/Program/Fall_Campus_Recruitment/examples:/workspace/examples:ro', '-v', 'F:/Program/Fall_Campus_Recruitment/analyzers:/workspace/analyzers:ro', '-v', 'F:/Program/Fall_Campus_Recruitment/contracts:/workspace/contracts:ro', '-v', 'F:/Program/Fall_Campus_Recruitment/testdata:/workspace/testdata:ro', '-w', '/workspace/backend', 'worker', 'python', '-B', '-m', 'pytest')
```

| 工作目录 | 实际命令或操作（上述前缀展开） | 观察结果 |
| --- | --- | --- |
| 根目录 | `Get-Location`；`git status --short --branch` | 路径正确；Git 返回 `not a git repository`，原有环境事实，未初始化 |
| 根目录 | `& $M5Docker @M5Compose build api frontend task-board-api` | 三个独立镜像构建通过；后续前端最终修订再次构建通过，保留分块警告 |
| 根目录 | `& $M5Docker @M5Compose up -d --no-build --wait frontend worker reconciler task-board-api lab-reconciler` | 空业务卷迁移与服务启动通过；清理进程最终运行正常 |
| 根目录 | `& $M5Docker @M5Compose @M5BackendTest apps/labs/tests apps/jobs/tests apps/learning/tests apps/explanations/tests apps/projects/tests apps/analysis/tests --ds=config.settings.local -q -p no:cacheprovider --tb=short` | 修复后 327 passed，69.71 秒；覆盖当前相邻模块，不代表所有环境兼容 |
| 根目录 | `& $M5Docker @M5Compose @M5BackendTest apps/labs/tests --ds=config.settings.local -q -p no:cacheprovider --tb=short` | 后续补充真实并发运行、清理失败与写入后子进程退出后，最终 12 passed，26.44 秒 |
| 根目录 | `& $M5Docker @M5Compose run --rm --no-deps -v 'F:/Program/Fall_Campus_Recruitment/examples/task-board/backend:/workspace/backend:ro' -w /workspace/backend task-board-api python -B -m pytest apps/labs/tests apps/tasks/tests/test_tasks.py --ds=config.settings.labs -q -p no:cacheprovider --tb=short` | 最终 42 passed，1.35 秒；包括固定输入、同 case 并发、隔离清理、到期关闭和原示例行为 |
| `backend` | `& $M5Python -m ruff check .`；`& $M5Python -m ruff format --check .`；`& $M5Python -m mypy config common apps tests --platform linux --no-incremental` | 通过；149 个文件格式检查，144 个源文件类型检查 |
| `examples/task-board/backend` | 同上三个静态命令 | 通过；41 个文件格式检查，36 个源文件类型检查 |
| `frontend` | `& $M5Node node_modules/vitest/vitest.mjs run` | 全量 47 passed，34.61 秒；随后新增当前任务运行定位用例后按下一行聚焦回归 |
| `frontend` | `& $M5Node node_modules/vitest/vitest.mjs run src/features/labs src/app/WorkspacePage.test.tsx` | 最终 11 passed，9.02 秒（labs 6、WorkspacePage 5） |
| `frontend` | `& $M5Node node_modules/typescript/bin/tsc --noEmit`；`& $M5Node node_modules/eslint/bin/eslint.js . --max-warnings 0`；`& $M5Node node_modules/prettier/bin/prettier.cjs --check .` | 通过；最终重试显示修订后类型检查通过，lint/format 再聚焦 `src/features/labs src/app/WorkspacePage.tsx` 通过 |
| 根目录 | `& $M5Python -X utf8 scripts/check_contracts.py --node $M5Node` | 三份 Schema 与接口表一致，两套前端类型及类型检查通过；工作台 37、默认示例 3、实验配置 7 操作；契约测试分别 47、11 项通过 |
| 根目录 | `& $M5Python -m ruff check scripts/check_contracts.py scripts/check_m5_workspace.py`；`& $M5Python -m ruff format --check scripts/check_contracts.py scripts/check_m5_workspace.py` | 两个脚本检查通过 |
| 根目录 | `& $M5Python -X utf8 -m unittest discover -s scripts -p test_check_contracts.py -v`；`& $M5Python -X utf8 -m unittest discover -s scripts -p test_check_task_board_annotations.py -v`；`& $M5Python -X utf8 scripts/check_task_board_annotations.py` | 契约脚本3项、标注脚本6项测试通过；人工基准12节点/12边完整性通过 |
| 根目录 | `& $M5Docker @M5Compose exec -T api python manage.py makemigrations --check --dry-run`；同命令服务替换为 `task-board-api` | 两端均 `No changes detected` |
| 根目录 | `& $M5Python -X utf8 scripts/check_m5_workspace.py` | 模型关闭的真实 HTTP 闭环通过；导入9文件、分析及三类固定作答，四种标题真实结果和同键并发通过 |
| 根目录 | `& $M5Docker @M5Compose stop task-board-api`；`& $M5Python -X utf8 scripts/check_m5_workspace.py --expect-failure`；在 finally 恢复 `start task-board-api` | 停服后 failed、零观测、cleanup=unconfirmed；没有模拟成功；随后恢复服务 |
| 根目录 | `& $M5Python -X utf8 scripts/check_m5_workspace.py --labs-only` | 两次新运行及针对原失败任务的显式重试通过；原失败不被覆盖 |
| 根目录 | `& $M5Docker @M5Double up -d --no-build --wait frontend worker reconciler task-board-api lab-reconciler`；`& $M5Python -X utf8 scripts/check_m5_workspace.py --model-double` | 固定替身完整闭环通过，未外发；证据文件区分模型关闭与替身两轮 |
| 根目录 | `& $M5Docker @M5Double restart postgres redis task-board-postgres api worker reconciler task-board-api lab-reconciler frontend`；健康恢复后 `& $M5Python -X utf8 scripts/check_m5_workspace.py --verify-history` | 九个服务实际重启后本轮 8 条历史可读；通过同一只读检查函数另核对模型关闭轮的 11 条资源，全部保留 |
| 根目录 | Python 标准输入 HTTP 探针，对 5177 实验提交分别移除 CSRF、设置非法 Origin、设置非法 Host | 缺 CSRF=403/CSRF_REJECTED；非法 Origin=403/ORIGIN_REJECTED；非法 Host 被 Nginx 403 拒绝（text/html），未把它误称为应用 JSON 错误 |
| 根目录 | Docker 只读端口、内部网络属性和 `stats --no-stream` 检查 | 只有 frontend 发布 127.0.0.1:5177；内部 API 不映射宿主端口，两条网络均 Internal=true；资源数值见上文 |
| 真实浏览器 | 打开 5177 导入所得快照 → 讲解预览/确认/提交 → 结果引用 → 源码 → 作答 → 实验 → 历史与刷新；键盘 Enter 操作和 390×844 窄窗口 | 本地替身文字明确；引用定位 serializers.py 8–30，作答定位9–15正确；错误预测保持原样而实际201/400独立展示；刷新可读；窄窗口 clientWidth=scrollWidth=375，无横向溢出 |
| 真实浏览器 | 原失败实验点击显式重试 | 新运行自动显示至完成、四项真实观测与清理可读，原失败记录保留；无需刷新找新记录 |
| 根目录 | 通过 `& $M5Python -X utf8 -` 执行标准输入静态审阅脚本：基线 SHA-256 比对、逐文件 diff、ast.parse、UTF-8/本地文档链接/Markdown 围栏和新增行空白检查 | 68个变更文件、42个Python语法、98处本地链接和9个教学源码摘要检查通过；依赖清单、锁文件与需求标准不变 |

**过程中发现并解决的问题。** 初次后端广泛回归出现 1 fail、11 errors（315 项通过）：原契约精确计数仍为32，以及原 jobs 迁移回退测试只恢复 jobs，连带留下下游 apps 缺表。更新精确契约为37并保留新增操作断言；迁移测试 finally 恢复原全部叶节点，复跑327项通过。初次实验核对进程使用 Compose extends 未完整继承所需配置，改为显式独立配置后验证正常。一次前端测试被加载图标的可访问名称影响，修正定位匹配，仍保留两次不同幂等键断言；没有放宽行为期望。浏览器发现显式重试仍停留旧运行，增加按 job_id 的查询并清除旧 run，补回归和真实浏览器验证。该修订第一次类型检查发现空列表返回类型未正确推断，改用 `at(0) ?? null` 后检查与构建通过。

Windows 测试临时目录出现 WinError 5、前端子进程出现 spawn 权限限制，使用相同受限范围命令经提升授权重跑通过；没有降低检查标准。超大响应参数化测试名称导致 Windows 路径限制，改为明确简短测试 ID，保留超限断言。HTTP 探针最初把 Nginx 的 HTML 403 当 JSON 解码失败，修正观测口径后确认正常拒绝。浏览器自动审批曾拒绝保存模型确认，理由是把页面确认视为持久外发许可；停止该动作，说明已核验的本地替身范围并取得用户明确授权后完成保存与提交。该许可仅用于本地5177固定替身，未授权真实模型调用。

#### 首版验收归档（不降低原标准）

“沿用”表示对应既有任务记录仍有效，本次核对相关实现未被替换，并进行必要相邻回归；不将未重做的操作写成本次新执行。下表保留 M5 本地交付当时的结论，M4 两项在当时仍待验收；当前状态以第 7 节及后续人工审阅、输出预算修复和真实复验记录为准。

| 用例 | 结论 | 当前证据及剩余边界 |
| --- | --- | --- |
| AT-01 | 通过（沿用并回归） | M2 独立快照及旧引用测试；本次真实导入与分析闭环，没有覆盖旧快照 |
| AT-02 | 通过（沿用并回归） | M2 安全 ZIP 边界，当前 projects 回归通过；本次未修改过滤或限额 |
| AT-03 | 通过（沿用并回归） | M2 排除与不泄露记录，M4 上下文边界回归；没有读取真实秘密来测试 |
| AT-04 | 通过（沿用并回归） | M2 分析回归；原人工基准12节点/12边完整性，本次九源码摘要不变 |
| AT-05 | 通过（沿用并回归） | M2 不确定关系断点、当前 analysis 测试保留 |
| AT-06 | 通过（沿用并回归） | M2 局部语法错误与整体故障分类、analysis 回归 |
| AT-07 | 通过（沿用并回归） | M3 声明的有限前端规则；本次真实分析与源码跳转，不扩大语法支持 |
| AT-08 | 通过（沿用并回归） | M3 动态/候选保守匹配；浏览器仍明确展示诊断与未匹配请求 |
| AT-09 | 通过 | M3/前端回归及本次真实讲解引用定位 serializers.py 8–30；失效引用仍拒绝 |
| AT-10 | 通过（本地边界） | M3/M4 迟到与切换回归；实验按选中分析/接口/快照校验、拒绝跨快照，按 job_id恢复新尝试 |
| AT-11 | 通过（本地边界） | M4 确认失效及幂等测试；本次固定替身浏览器经用户明确许可完成确认提交，未真实外发 |
| AT-12 | 部分通过，真实服务待验收 | 本地未配置、失败、超时与替身回归通过；真实服务兼容/中断仍为 M4-T01 缺口 |
| AT-13 | 通过（本地边界） | M4 格式/归属/行号校验测试，未把位置校验宣称为语义正确 |
| AT-14 | 通过（本地边界） | M4 注入/HTML/非法结构安全回归；实验正文使用文本呈现，不执行导入源码 |
| AT-15 | 自动化通过，独立内容审阅待完成 | 三类固定题的正确/错误/版本测试和真实作答通过；M4-T03 人工审阅仍未完成 |
| AT-16 | 通过 | 真正调用内部示例，201/400/400/400、增量1/0/0/0；浏览器可展开实际正文 |
| AT-17 | 通过 | 真停示例无观测且清理未知；不完整响应注入保留前项及 null后计数；清理失败保留四项响应 |
| AT-18 | 通过（本地） | 九服务真实重启后8+11条资源可读，浏览器刷新及作答/实验历史保留；没有重启原实例 |
| AT-19 | 通过 | 同键4线程服务测试与3并发HTTP仅一任务；冲突409；显式重试独立新run/previous_job，旧失败保留 |
| AT-20 | 通过（声明的故障条件） | 发布失败；Linux子进程在真实写入后以23退出；注入已过期期限并核对终结、迟到拒绝。不是等待真实期限的墙钟耐久测试 |
| AT-21 | 通过（沿用并回归） | M2 磁盘故障/真实子进程中断测试与当前 projects 回归，旧快照边界保留 |
| AT-22 | 通过 | 两个真实并发实验各增1且各清1；同case并发唯一写；无关普通任务及另一个运行不受影响；到期围栏用受控时钟验证 |
| AT-23 | 通过（本地浏览器范围） | 键盘切面板/提交、空预测表单、错误及重试、390×844 无横向溢出；未做所有浏览器/辅助技术兼容性承诺 |
| AT-24 | 通过（本机隔离配置） | 真HTTP缺CSRF/非法Origin/Host拒绝，127.0.0.1绑定，内部API不映射；既有来源/权限测试通过 |
| AT-25 | 本地参考环境通过，完整首版仍受限 | 独立空卷启动与固定工具/缓存镜像、闭环及资源耗时记录；真实模型、独立审阅、全新宿主安装与其他架构未验收 |

#### 演示、证据与最终审阅

README 的 M5 启动/固定替身/停服恢复/重启步骤为可复现演示说明。当前保留5177固定替身实例和本次数据卷；打开 `http://127.0.0.1:5177/` 后选择验收项目的创建任务接口。手工观察点：故意把正常标题预测为400/不写入，运行后预测仍原样保存，实际响应应是201、运行内记录0→1，其余三项400且1→1，最终只清理该运行。

脱敏本地证据：`.runtime/m5-http-disabled.json` 保存模型关闭、真停服失败及恢复重试；`.runtime/m5-http-verification.json` 保存固定替身闭环及资源路径；`.runtime/m5-workspace.png`、`.runtime/m5-workspace-narrow.png` 为浏览器截图。代表成功run为 `f43c024a-b10f-4050-9d48-6b9d36d43898`；代表失败run为 `2ff05357-2dc9-4583-88ed-b8e64f16caac`；浏览器显式重试新run为 `e96e64b5-01a8-4371-86e3-957f08c8beea`。这些标识只用于本地复核，不携带凭据。

相对本次修改前基线，新增38、修改30、删除0，共68个工程文件。依赖清单、锁文件、需求验收标准、原九教学源码与既有用户内容未被替换。最终审阅使用逐文件 diff（含生成契约的可复现核对）；修正文档中仍称32操作、实验未实现及重试未含lab的过时描述。项目记忆同步到已有AGENTS、README、阶段计划、结构、API与两端规范、路线图及示例README，没有新增平行记忆系统。长期限制保留M4未验收、清理故障、静态规则范围及资源观测口径，不推进其他任务。

范围外观察：重新核对确认 README 既有导入说明仍写25 MiB，而 `backend/config/settings/base.py` 的 archive_bytes 为20,971,520（20 MiB），`apps/projects/types.py` 同为20 MiB。该差异在M4已有记录，不阻塞本次10,199字节样例；本次不修改导入行为或开展其他编号任务，实际使用应遵守20 MiB上限。

#### M5 逐文件变更清单

| 类型 | 文件 | 用途 |
| --- | --- | --- |
| 修改 | `.dockerignore` | 将固定实验定义纳入后端构建上下文 |
| 修改 | `AGENTS.md` | 同步实验能力与首版待验收边界 |
| 修改 | `README.md` | 5177启动、演示、故障恢复与契约说明 |
| 修改 | `backend/apps/explanations/tests/double_worker.py` | 允许独立5177固定替身验收，保留无外发边界 |
| 修改 | `backend/apps/explanations/tests/test_contract.py` | 精确校验37操作及新增实验operationId |
| 修改 | `backend/apps/jobs/api/serializers.py` | 接入实验四态、领取、结果和显式重试 |
| 修改 | `backend/apps/jobs/api/views.py` | 接入实验四态、领取、结果和显式重试 |
| 修改 | `backend/apps/jobs/retries.py` | 接入实验四态、领取、结果和显式重试 |
| 修改 | `backend/apps/jobs/services.py` | 接入实验四态、领取、结果和显式重试 |
| 修改 | `backend/apps/jobs/tests/test_contract.py` | 精确契约路径加入五个实验操作 |
| 修改 | `backend/apps/jobs/tests/test_recovery.py` | 迁移回退测试恢复全部叶节点，避免污染后续测试 |
| 新增 | `backend/apps/labs/__init__.py` | 当前实验模块所需Python包入口 |
| 新增 | `backend/apps/labs/adapter.py` | 固定传输期限与返回结构、清理身份校验 |
| 新增 | `backend/apps/labs/api/__init__.py` | 当前实验模块所需Python包入口 |
| 新增 | `backend/apps/labs/api/serializers.py` | 严格预测输入及定义、响应、清理和分页类型 |
| 新增 | `backend/apps/labs/api/urls.py` | 固定实验及运行记录路由 |
| 新增 | `backend/apps/labs/api/views.py` | 查询、提交及运行历史HTTP边界 |
| 新增 | `backend/apps/labs/definition.py` | 版本化定义及九源码摘要适用性检查 |
| 新增 | `backend/apps/labs/migrations/0001_initial.py` | 新增实验表及关联约束迁移，不改写已有业务行 |
| 新增 | `backend/apps/labs/migrations/__init__.py` | 当前实验模块所需Python包入口 |
| 新增 | `backend/apps/labs/models.py` | 实验运行/会话持久化字段和资源归属 |
| 新增 | `backend/apps/labs/services.py` | 幂等运行、真实观测、事务关闭与隔离清理 |
| 新增 | `backend/apps/labs/tasks.py` | 接入现有Worker的固定实验任务入口 |
| 新增 | `backend/apps/labs/tests/__init__.py` | 当前实验模块所需Python包入口 |
| 新增 | `backend/apps/labs/tests/test_adapter.py` | 实验响应、故障、并发、隔离和恢复验证 |
| 新增 | `backend/apps/labs/tests/test_labs.py` | 实验响应、故障、并发、隔离和恢复验证 |
| 新增 | `backend/apps/labs/transport_worker.py` | 无代理无重定向的固定内网HTTP传输 |
| 修改 | `backend/config/settings/base.py` | 注册工作台实验模块 |
| 修改 | `backend/config/urls.py` | 注册五个工作台实验路由 |
| 新增 | `content/labs/request-validation.json` | 固定实验来源、版本、说明与四类输入 |
| 修改 | `contracts/openapi.yaml` | 从实现生成37操作契约与观测类型 |
| 修改 | `docs/api-catalog.md` | 同步M5职责、契约或运行边界，保留未验收项 |
| 修改 | `docs/api-conventions.md` | 同步M5职责、契约或运行边界，保留未验收项 |
| 修改 | `docs/backend-guidelines.md` | 同步M5职责、契约或运行边界，保留未验收项 |
| 修改 | `docs/frontend-guidelines.md` | 同步M5职责、契约或运行边界，保留未验收项 |
| 修改 | `docs/phase-1-plan.md` | 唯一任务状态、实际命令、验收矩阵与逐文件记录 |
| 修改 | `docs/project-structure.md` | 同步M5职责、契约或运行边界，保留未验收项 |
| 修改 | `docs/roadmap.md` | 同步M5职责、契约或运行边界，保留未验收项 |
| 修改 | `examples/task-board/README.md` | 默认公开示例与内部实验配置的职责和清理说明 |
| 新增 | `examples/task-board/backend/apps/labs/__init__.py` | 当前实验模块所需Python包入口 |
| 新增 | `examples/task-board/backend/apps/labs/management/__init__.py` | 当前实验模块所需Python包入口 |
| 新增 | `examples/task-board/backend/apps/labs/management/commands/__init__.py` | 当前实验模块所需Python包入口 |
| 新增 | `examples/task-board/backend/apps/labs/management/commands/reconcile_lab_runs.py` | 有界批次关闭过期运行，数据库故障后恢复 |
| 新增 | `examples/task-board/backend/apps/labs/migrations/0001_initial.py` | 新增实验表及关联约束迁移，不改写已有业务行 |
| 新增 | `examples/task-board/backend/apps/labs/migrations/__init__.py` | 当前实验模块所需Python包入口 |
| 新增 | `examples/task-board/backend/apps/labs/models.py` | 实验运行/会话持久化字段和资源归属 |
| 新增 | `examples/task-board/backend/apps/labs/services.py` | 幂等运行、真实观测、事务关闭与隔离清理 |
| 新增 | `examples/task-board/backend/apps/labs/tests/__init__.py` | 当前实验模块所需Python包入口 |
| 新增 | `examples/task-board/backend/apps/labs/tests/test_labs.py` | 实验响应、故障、并发、隔离和恢复验证 |
| 新增 | `examples/task-board/backend/apps/labs/views.py` | 固定内部用例输入、事务围栏和真实响应 |
| 新增 | `examples/task-board/backend/config/lab_urls.py` | 实验专用URL组合，保留默认公开入口 |
| 新增 | `examples/task-board/backend/config/settings/labs.py` | 独立实验配置加载内部app |
| 新增 | `examples/task-board/backend/config/settings/labs_test.py` | 无秘密、无业务数据库的内部Schema导出配置 |
| 新增 | `examples/task-board/contracts/labs-openapi.yaml` | 生成实验专用七操作Schema，不改变原公开契约 |
| 修改 | `frontend/src/app/WorkspacePage.tsx` | 组合实验面板，接入结果与重试切换 |
| 修改 | `frontend/src/app/workspace-location.ts` | 验证并恢复所属工作区run参数 |
| 修改 | `frontend/src/app/workspace.css` | 实验预测/结果文本布局与窄窗口样式 |
| 修改 | `frontend/src/features/jobs/api/jobs-api.ts` | 校验lab类型、null快照和结果路径 |
| 新增 | `frontend/src/features/labs/LabPanel.test.tsx` | 预测、失败、跨快照、409与新重试显示回归 |
| 新增 | `frontend/src/features/labs/LabPanel.tsx` | 先预测后运行、真实结果、失败和历史恢复界面 |
| 新增 | `frontend/src/features/labs/api/labs-api.ts` | 实验DTO运行时校验与共享请求调用 |
| 新增 | `frontend/src/features/labs/index.ts` | 实验feature公共出口 |
| 修改 | `frontend/src/shared/api/generated/schema.d.ts` | 从OpenAPI生成实验请求与响应类型 |
| 修改 | `frontend/src/shared/hooks/useIdempotentOperation.ts` | 明确拒绝的实验409释放键以允许修正 |
| 修改 | `infra/docker/compose.m4-double.yaml` | 说明固定替身可用于独立M4/M5实例 |
| 新增 | `infra/docker/compose.m5-verify.yaml` | 独立5177、本地内部网络及实验到期核对进程 |
| 修改 | `scripts/check_contracts.py` | 核对第三份内部Schema及接口表 |
| 新增 | `scripts/check_m5_workspace.py` | 真实HTTP闭环、并发提交、故障恢复与历史验证 |

### M4 人工审阅的模型配置准备（2026-09-30）

用户要求在项目根目录创建 `.env`，自行填写模型请求地址、模型 ID 和 API key，填写完成后再由代理启动项目供人工审阅。本轮仅完成配置准备，没有将此前固定替身结果当作真实服务验收，也未启动 v0.2。

核对现有配置后，以独占创建方式生成 `.env` 占位文件，未覆盖已有文件。前三项为 MODEL_BASE_URL、MODEL_NAME、MODEL_API_KEY；基础地址只接受 HTTPS，程序追加 `/chat/completions`。默认保留既有60秒、65,536字节上下文、4,096输出token和 max_completion_tokens 参数。文件已被既有 Git/镜像忽略规则排除；不记录用户后来填写的内容或其摘要。

原 `compose.model.yaml` 依赖独立密钥文件。新增可选 `infra/docker/compose.model-env.yaml`，从环境源创建同名 secret，只交给 Worker 的 `/run/secrets/model_api_key`，不把密钥注入 API、前端或命令行。保留原密钥文件模式，两个覆盖配置择一使用；真实审阅不能叠加固定替身配置。README 已记录5177启动命令，结构文档同步配置职责。未改业务代码、依赖、数据库结构或原实例。

验证工作目录为 `F:\Program\Fall_Campus_Recruitment`。`Get-Location` 确认目录，`git status --short --branch` 仍返回 `not a git repository`；没有初始化。首次 Python TemporaryDirectory 写入遇 PermissionError/WinError 5，改用项目 `.runtime` 内的独占临时测试文件后成功，测试文件已清理。只使用 `https://model.example.invalid/v1` 等无效合成配置，没有读取根 `.env`。

实际通过固定 Python 的标准输入脚本运行以下命令并捕获结果到内存，不输出合并配置正文：

```powershell
& 'C:/Program Files/Docker/Docker/resources/bin/docker.exe' compose --env-file <项目内临时合成配置文件> -p learning-lab-m5-verify -f compose.yaml -f infra/docker/compose.m5-verify.yaml -f infra/docker/compose.model-env.yaml --profile task-board config --format json
```

结果：Compose解析成功，断言密钥仅作为 Worker secret、API仅接收非秘密模型配置、仅 Worker 加入模型出口、内部实验网络保留、启动命令为正常Celery而非替身、前端仅绑定127.0.0.1:5177。此检查不启动容器、不验证真实密钥挂载或模型兼容性、不触发网络调用；启动及人工审阅等待用户填写完成后继续。没有业务代码变更，不重复运行产品单元测试。M4-T01/M4-T03与v0.1状态保持待验收。

### M4 人工审阅实例启动（2026-09-30）

用户确认已填写 `.env`，本轮按前述授权启动 `learning-lab-m5-verify` 人工审阅实例，沿用 5177 和现有数据卷。没有改写 `.env`、重新构建或拉取镜像，也没有提交讲解、保存外发确认或调用模型。此前“等待填写后启动”的准备状态由本节取代；真实供应商兼容性与独立人工内容审阅仍待验收。

实际兼容性修正：Windows Docker Compose v5.1.1 能解析 `secrets.environment`，但两次启动均在创建 Worker secret 时失败，提示只支持文件源；其他服务已启动，Worker 当时仅为 created。配置解析通过不能证明密钥挂载可运行。`compose.model-env.yaml` 因而改为后端已有的 `MODEL_API_KEY` 环境变量方式，仅注入 Worker，API/前端不接收密钥，Worker 仍使用正常 Celery 命令及模型出口。`compose.model.yaml` 的独立凭据文件挂载方式保留，两者不能叠加。此方式的密钥存在于 Worker 容器配置中，不得输出完整 Compose 配置或容器环境。README 和结构文档已同步；没有新增依赖或修改业务代码。

以下检查工作目录均为 `F:\Program\Fall_Campus_Recruitment`。通过 `.runtime/m1-t02-venv/Scripts/python.exe -B -X utf8 -` 的标准输入脚本执行配置/进程检查，捕获涉及配置的输出到内存，仅报告断言或退出码，不回显配置值、凭据或其摘要。

```powershell
& 'C:/Program Files/Docker/Docker/resources/bin/docker.exe' compose --env-file .env -p learning-lab-m5-verify -f compose.yaml -f infra/docker/compose.m5-verify.yaml -f infra/docker/compose.model-env.yaml --profile task-board config --format json
& 'C:/Program Files/Docker/Docker/resources/bin/docker.exe' compose --env-file .env -p learning-lab-m5-verify -f compose.yaml -f infra/docker/compose.m5-verify.yaml -f infra/docker/compose.model-env.yaml --profile task-board up -d --no-build --pull never --wait --wait-timeout 120 frontend worker reconciler task-board-api lab-reconciler
& 'C:/Program Files/Docker/Docker/resources/bin/docker.exe' ps -a --filter 'label=com.docker.compose.project=learning-lab-m5-verify' --format '{{.Names}}|{{.State}}|{{.Status}}|{{.Ports}}'
```

第一条命令只在上述捕获脚本中执行，不能直接输出到终端。修正后断言通过：模型配置启用、地址与模型格式有效、凭据格式有效且仅 Worker 接收、无环境/文件凭据冲突、仅 Worker 加入模型出口、内部实验网络保留、入口仅绑定 `127.0.0.1:5177`。第二条返回0；9个常驻服务运行，5个配置了健康检查的服务为 healthy，5个初始化/迁移容器退出0。最初 Docker 状态读取遇命名管道 permission denied，使用已授权的提升权限检查后恢复；未修改 Docker 安全配置。

```powershell
& 'C:/Program Files/Docker/Docker/resources/bin/docker.exe' exec learning-lab-m5-verify-worker-1 python -c "import django; django.setup(); from apps.explanations.configuration import configuration, credential; configuration(); assert credential(); from config.celery import app; assert app.control.ping(timeout=5); print('Worker 配置校验、凭据加载及 Celery ping 通过；未调用模型。')"
```

Worker 检查退出0，确认实际容器能加载配置和凭据且 Celery 响应。标准库 urllib 禁用代理后只读请求 `/`、`/api/v1/projects/`、`/api/v1/jobs/`、`/api/v1/explanations/`，全部 HTTP 200；HTML 包含应用 root，本地 JavaScript 资源可读取。本轮只涉及运行配置，不重跑产品单元测试；HTTP 与启动成功不代表浏览器交互、真实模型响应质量或供应商兼容性验收通过。人工观察点：在已分析接口的讲解面板重新生成预览，核对目标/模型、片段及预算，再由用户决定是否确认和提交。

### 人工终审前测试与真实模型预算缺陷（2026-09-30）

**范围与结论。** 用户要求由代理测试、自己做最后审阅。重新核对指令、文件、唯一阶段记录和实际实例后，执行现有回归、浏览器流程和一次明确授权的真实模型请求。当前不是 Git 仓库，未初始化。此轮仅修改验证及已知限制文档，未改业务代码、`.env`、依赖或数据结构；原有用户记录保留。测试产生四条练习作答、三条成功实验、一个预览和一条真实讲解。浏览器使用 computer-use 技能；最后恢复默认视口并保留讲解页面。

419项既有自动化测试通过，但不能据此宣布模型兼容通过：真实请求的输出预算被超过，应用仍标记成功。该缺陷阻塞 M4-T01 验收；M4-T03 的最终独立人工内容审阅仍由用户完成。M5 原有本地结论不改写，v0.1 不宣布完成，不启动后续版本。

**实际命令与自动化结果。** 工作目录除另注外均为 `F:\Program\Fall_Campus_Recruitment`。实际执行时使用如下参数数组；临时测试容器使用 `.env.example`，没有真实密钥或模型出口，数据库用 pytest 的独立测试库，正常实例保留。

```powershell
$ReviewDocker='C:/Program Files/Docker/Docker/resources/bin/docker.exe'
$ReviewCompose=@('compose','--env-file','.env.example','-p','learning-lab-m5-verify','-f','compose.yaml','-f','infra/docker/compose.m5-verify.yaml','--profile','task-board')
$ReviewBackendTest=@('run','--rm','--no-deps','-e','APP_PORT=5173','-e','APP_ORIGIN=http://127.0.0.1:5173','-v','F:/Program/Fall_Campus_Recruitment/backend:/workspace/backend:ro','-v','F:/Program/Fall_Campus_Recruitment/content:/workspace/content:ro','-v','F:/Program/Fall_Campus_Recruitment/examples:/workspace/examples:ro','-v','F:/Program/Fall_Campus_Recruitment/analyzers:/workspace/analyzers:ro','-v','F:/Program/Fall_Campus_Recruitment/contracts:/workspace/contracts:ro','-v','F:/Program/Fall_Campus_Recruitment/testdata:/workspace/testdata:ro','-w','/workspace/backend','worker','python','-B','-m','pytest')
```

| 工作目录 | 实际命令或操作 | 观察结果 |
| --- | --- | --- |
| 根目录 | `Get-Location`；`git status --short --branch` | 路径正确；`not a git repository`，未做 Git 写操作 |
| 根目录 | `& $ReviewDocker @ReviewCompose @ReviewBackendTest apps/labs/tests apps/jobs/tests apps/learning/tests apps/explanations/tests apps/projects/tests apps/analysis/tests --ds=config.settings.local -q -p no:cacheprovider --tb=short` | 329 passed，81.27秒；含既有适配器错误、确认/引用、安全、快照、任务和实验用例 |
| 根目录 | `& $ReviewDocker @ReviewCompose run --rm --no-deps -v 'F:/Program/Fall_Campus_Recruitment/examples/task-board/backend:/workspace/backend:ro' -w /workspace/backend task-board-api python -B -m pytest apps/labs/tests apps/tasks/tests/test_tasks.py --ds=config.settings.labs -q -p no:cacheprovider --tb=short` | 42 passed，1.64秒 |
| `frontend` | `& 'F:/Program/Fall_Campus_Recruitment/.runtime/tools/node-v24.21.0-win-x64/node.exe' node_modules/vitest/vitest.mjs run` | 首次因 Windows `spawn EPERM` 未能加载配置；提升执行权限后同命令48 passed、10文件、34.10秒；未弱化用例 |
| `frontend` | `& 'F:/Program/Fall_Campus_Recruitment/.runtime/tools/node-v24.21.0-win-x64/node.exe' node_modules/typescript/bin/tsc --noEmit` | 退出0 |
| 根目录 | 标准输入脚本经 `& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 -` 执行，复用 `scripts/check_m5_workspace.py` 的 Client | 同键3并发仅创建一任务，冲突载荷409，两次独立实验均为201/400/400/400、写入1/0/0/0，清理后0条，历史可读取；7.50秒；未覆盖既有HTTP证据文件 |
| 根目录 | 同一标准输入入口，urllib 禁用代理；缺少CSRF写请求、非法Host读取、跨站写请求 | 均403，前后任务数不变 |
| 根目录 | 同一标准输入入口，只读预览/讲解API | 7段文本逐行匹配内置示例；五部分共39条声明、36处引用均落在所预览范围内，不能据此断言语义正确 |

辅助检查脚本首次误用片段键 `text` 导致 KeyError；对照实际 Serializer 改为 `content` 后通过，属于测试脚本问题。下述预算探针首次未设置 Django settings；改用既有无服务 `config.settings.test` 后复现。两次脚本错误均未触发模型请求。

**浏览器与本地HTTP证据。** 基于当前9文件示例快照、分析 `704530e6-3814-4aaa-b390-3a9dbec68695`、POST接口索引6：

- 成功分析显示前后端确认关系及保守诊断；点击 TaskSerializer 定位8–30行。原失败分析仍保留，未覆盖用户选择或历史。
- 排序初次判错；改为正确顺序后使用提示并提交，正确性和提示使用分别保存。四种输入预测、关键代码9–15行定位题均判对；四条作答历史保留，刷新后仍能读到结果。
- 空实验表单被浏览器必填校验阻止。正常输入故意预测200/0，真实结果仍显示201、0→1；其余三种均400、不写入。展开真实响应可查看本次运行标识及响应，清理确认只覆盖本次运行。
- HTTP实验记录为 `2a3dc2d9-416e-4eec-87e2-7d5c3fdc0c4f`、`51ddc5e9-2968-41ea-b19a-fa36a15b6c76`；浏览器实验为 `6b29c4bb-8ad5-4bcc-8bc1-e1d068835aa3`。均可通过运行历史读取。
- 390×844视口下有效内容宽度与可视宽度均375，无横向溢出；恢复默认视口。浏览器所采集控制台没有 error/warn。此轮没有重复做真实停服/重启故障注入，相关自动化回归与既有M5实测记录仍分开保留。

**唯一一次真实模型请求。** 向用户展示预览后取得明确单次授权，再在页面勾选、保存确认和提交；没有自动重试。目标为 `https://api.deepseek.com`、模型 `deepseek-flash`、模板 `explanation/1.0.0`。预览 `4ed6cf05-5aa7-4d69-bcb5-8aa57064084a` 包含内置示例7段源码及固定模板，25,583字节，输出请求上限4,096，期限60秒，参数 `max_completion_tokens`。认证凭据仅由既有 Worker 读取，未输出或记录。

任务 `e27fd3bd-a508-494c-b6ca-a33d966203a8` 在约55.34秒后标记 succeeded，结果 `e18ba976-15fa-4135-bae3-fe102373c952` 的五部分结构可读取；引用点击能定位相应源码，刷新后内容与用量仍在。供应商报告 prompt_tokens=6,464、completion_tokens=14,623、total_tokens=21,087；没有据此推算或宣称实际账单。

**阻塞缺陷：输出预算未生效且未被应用拒绝。** 4,096与14,623不一致，不能把任务 succeeded 或有效 JSON 当作预算兼容通过。实际 `adapter.complete` 只发送配置的限额字段，`decode_completion` 检查用量类型/数值范围后返回，未比较 completion_tokens 与本次 output_tokens。使用本地合成响应模拟4,097和14,623，两者都被现有适配器接受，未产生HTTP请求。

复现入口为 `backend` 工作目录下 `& 'F:/Program/Fall_Campus_Recruitment/.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 -`：设置 `DJANGO_SETTINGS_MODULE=config.settings.test` 并 `django.setup()`；构造上限4,096的 ModelConfiguration；以 unittest.mock 替换 credential 和 subprocess.Popen，将一次 stop 响应及超限 usage 交给 `complete`。两个边界均正常返回而非 ModelFailure，证实本地校验缺口。

[DeepSeek官方 Chat Completions 文档](https://api-docs.deepseek.com/api/create-chat-completion/) 在本次核对时列出 `max_tokens`，未列出 `max_completion_tokens`；默认启用 thinking。结合实际请求参数及用量，当前配置没有约束住供应商输出。待修复应包括：明确使用供应商支持的限额字段、补充报告用量超限的拒绝与任务不发布验证、使界面预算措辞反映供应商兼容边界。返回后拒绝无法撤销已发生的供应商处理或费用，不能作为计费硬上限保证。本轮仅测试并归档，未修改 `.env` 或自动切换参数；任何追加真实调用都须重新预览和单次确认。

截图保存在已忽略的 `.runtime/review-preview-20260930.jpg`、`.runtime/review-lab-narrow-20260930.jpg`、`.runtime/review-real-model-20260930.jpg`，只作验证证据，不是平行进度系统。最终审阅重点为：已有讲解的内容与证据是否一致，以及上述预算缺陷；修复前不建议接受 M4-T01 或 v0.1 完成。

### 独立人工内容审阅确认（2026-09-30）

审阅者为当前项目用户。用户在本轮测试交付及人工终审后明确回复“没什么问题，可以通过”，据此记录当前版本的独立人工内容审阅通过，无内容修正要求。此结论来自用户确认，编码代理的自动化检查与浏览器操作仅作为辅助证据。

审阅对象绑定本轮交付：内置示例 `task-board/1.0.0`、`content/knowledge/request-basics.json` 中五张 `1.0.0` 知识卡片、`content/exercises/task-board-create.json` 中三类固定题及各自 `1.0.0` 题目和答案版本，以及当前快照 `89ff91c0-9cef-4fea-a963-10796476c4a0` 下的真实讲解 `e18ba976-15fa-4135-bae3-fe102373c952`。源码、作答与实验依据沿用上节记录，不自动扩展到后续版本或其他项目。

M4-T03 更新为已完成；M4-T01 的请求上限4,096而报告输出14,623且仍成功发布的问题保持验收阻塞。用户本次内容认可不作为预算缺陷已修复的证据，不宣布 v0.1 完成，不开始 M6–M10，不追加真实模型调用。

本轮仅同步本文、README、AGENTS 和路线图中的当前状态，历史验收记录保留。检查工作目录为 `F:\Program\Fall_Campus_Recruitment`：`git status --short --branch` 仍返回 `not a git repository`；通过标准输入执行 `& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 -`，核对四份文档的完整差异、UTF-8、Markdown 围栏、本地链接、教学内容版本及当前状态一致性。仅文档修改，不重跑产品测试，不改代码、配置、依赖或教学内容。

### M4-T01 输出预算修复与真实复验准备（2026-09-30）

用户明确要求实施已确认的预算修复计划；缺少 usage 保留兼容行为，并选择本地修复后准备一次真实复验。本轮仅处理 M4-T01 及其测试和文档，不改模型推理设置、模板、教学内容、DTO、数据库结构或依赖，不推进 M6–M10。当前不是 Git 仓库，未初始化。修改前13份非敏感文件副本及341份工程文件摘要位于忽略目录 `.runtime/m4-output-budget-baseline-20260930-6ff4b323`；不包含 `.env` 或凭据，不是平行进度来源。

**实现。** `complete` 在原响应结构、finish_reason 与用量合法性校验之后，比较 completion_tokens 与本次 output_tokens；等于上限允许，超限抛出 MODEL_OUTPUT_BUDGET_EXCEEDED。jobs 沿用原领取和终结流程，记录明确超限失败与潜在重复计费，不创建新 Explanation 或 result_url，不自动重试。缺失用量继续保存 null，界面明确无法核验实际预算。输出比较不使用输入/总用量，也不扣除输出统计中的推理用量。前端展示请求上限、限额字段、输入/输出/总用量和费用边界，旧记录不回填。

按本次明确授权，只将 `.env` 的非秘密 `MODEL_TOKEN_LIMIT_FIELD` 从 max_completion_tokens 改为 max_tokens，验证其余字节保持一致；未备份、输出或记录敏感配置及摘要。通用默认值和两种字段枚举不变，不按域名推断或失败换参。[DeepSeek 官方接口文档](https://api-docs.deepseek.com/api/create-chat-completion/) 列出 max_tokens；配置变化使旧预览/确认失效，真实复验新建讲解操作，不将旧失败重试绑定到新配置。

**实际验证。** 除另注外工作目录为 `F:\Program\Fall_Campus_Recruitment`。Docker 路径仍为 `C:/Program Files/Docker/Docker/resources/bin/docker.exe`。以下参数数组用于无真实凭据、无模型出口的独立测试容器，源码只读挂载；正常实例和历史保留：

```powershell
$BudgetDocker='C:/Program Files/Docker/Docker/resources/bin/docker.exe'
$BudgetCompose=@('compose','--env-file','.env.example','-p','learning-lab-m5-verify','-f','compose.yaml','-f','infra/docker/compose.m5-verify.yaml','--profile','task-board')
$BudgetTest=@('run','--rm','--no-deps','-e','APP_PORT=5173','-e','APP_ORIGIN=http://127.0.0.1:5173','-v','F:/Program/Fall_Campus_Recruitment/backend:/workspace/backend:ro','-v','F:/Program/Fall_Campus_Recruitment/content:/workspace/content:ro','-v','F:/Program/Fall_Campus_Recruitment/examples:/workspace/examples:ro','-v','F:/Program/Fall_Campus_Recruitment/analyzers:/workspace/analyzers:ro','-v','F:/Program/Fall_Campus_Recruitment/contracts:/workspace/contracts:ro','-v','F:/Program/Fall_Campus_Recruitment/testdata:/workspace/testdata:ro','-w','/workspace/backend','worker','python','-B','-m','pytest')
```

| 工作目录 | 实际命令或操作 | 观察结果 |
| --- | --- | --- |
| 根目录 | `& $BudgetDocker @BudgetCompose @BudgetTest apps/explanations/tests apps/jobs/tests --ds=config.settings.local -q -p no:cacheprovider --tb=short` | 155 passed，40.70秒；含两种字段及0/4095/4096/4097/14623、非法用量、旧历史、幂等和恢复 |
| 根目录 | 同一测试入口，目标 `apps/explanations/tests/test_explanations.py -k 'output_budget_checked_before_publishing or token_field_change'`，其余参数不变 | 新测试非空断言修正后复测5 passed、10 deselected，5.89秒；真实适配器加合成传输验证发布边界，新字段使旧确认失效且零发送 |
| 根目录 | `& '.runtime/m1-t02-venv/Scripts/ruff.exe' check backend/apps/explanations backend/apps/jobs`；同一 Ruff 的 `format --check` 检查本次四份后端改动 | 均通过；只格式化本次改动文件 |
| `backend` | `& 'F:/Program/Fall_Campus_Recruitment/.runtime/m1-t02-venv/Scripts/mypy.exe' apps/explanations apps/jobs` | 首次15项错误：11项来自既有 Linux 文件锁/进程 API 在 Windows 的类型限制，4项来自新测试缺少 job.error 非空断言；后者已补齐 |
| 根目录 | `& $BudgetDocker @BudgetCompose run --rm --no-deps -v 'F:/Program/Fall_Campus_Recruitment/backend:/workspace/backend:ro' -v 'F:/Program/Fall_Campus_Recruitment/content:/workspace/content:ro' -v 'F:/Program/Fall_Campus_Recruitment/analyzers:/workspace/analyzers:ro' -w /workspace/backend worker mypy apps/explanations apps/jobs` | Linux规定环境43份源文件无错误，未忽略或弱化类型检查 |
| `frontend` | 固定 Node 执行 `node_modules/vitest/vitest.mjs run src/features/explanations/ExplanationPanel.test.tsx` | 9 passed，5.24秒；新增预算说明、报告/未知用量及超限失败不重发断言 |
| `frontend` | 固定 Node 分别执行 `node_modules/typescript/bin/tsc --noEmit`、`node_modules/eslint/bin/eslint.js src/features/explanations/ExplanationPanel.tsx src/features/explanations/ExplanationPanel.test.tsx --max-warnings 0`、`node_modules/prettier/bin/prettier.cjs --check` 同两文件、`tooling/generate-api-types.mjs --check` | 均退出0，生成类型与契约一致 |
| 根目录 | `& '.runtime/m1-t02-venv/Scripts/python.exe' -B backend/manage.py spectacular --settings=config.settings.test --validate --file .runtime/m4-budget-openapi-20260930.yaml`；标准输入Python脚本逐字比较 contracts/openapi.yaml | 导出与现有OpenAPI逐字一致，公共DTO不变 |
| 根目录 | `& $BudgetDocker @BudgetCompose build --pull=false api frontend` | 退出0；依赖安装层全部缓存，前端 tsc/Vite构建通过，Vite报告503.63kB分块大小提示；未拉取新版本或调整分块阈值 |
| 根目录 | `docker compose --env-file .env -p learning-lab-m5-verify -f compose.yaml -f infra/docker/compose.m5-verify.yaml -f infra/docker/compose.model-env.yaml --profile task-board up -d --no-build --pull never --no-deps --wait --wait-timeout 120 api worker frontend` | 更新前无queued/running任务；仅三个服务重建，退出0，API/Worker/前端healthy，数据库和其他服务未重建 |
| 根目录 | 标准输入 `& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 -`，urllib禁用代理，读取原项目/快照/分析/讲解/作答/实验六个具体资源 | 六项HTTP200且ID匹配，旧超限讲解保持原样，不回填状态 |
| 浏览器 | 重载当前页、检查旧用量明细，再点击准备外发预览 | 新界面显示输入6464/输出14623/合计21087历史；新预览使用max_tokens，确认与提交仍禁用，采集控制台无error/warn |

辅助预览对照脚本首次以不保留行尾的 splitlines 比较，出现 AssertionError；核对 source_content 的精确行尾规则后，改为 splitlines(keepends=True)，七段文本逐字匹配。此失败来自检查脚本，不修改源码片段或放宽断言，未产生模型请求。

**复验预览与剩余验收。** 新预览 `e9446811-6fa0-4b43-8b1e-eaa98ff6f2dc`，摘要 `94f2a1e302bf6c5f183f2dc089e14b812dd3c0dcff391d6cb32d3ed38de570b4`；目标 https://api.deepseek.com、模型 deepseek-flash、模板 explanation/1.0.0，当前示例快照及POST接口索引6。正文与七段片段均和上次预览逐字一致，25,583字节，max_tokens=4096、期限60秒。截图为忽略目录 `.runtime/m4-budget-preview-20260930.png`。在本节准备结束时尚未勾选保存确认或提交，追加真实复验须用户对本次范围作单次授权；后续执行见下一节。

本地缺陷修复已验证，M4-T01仍部分完成，真实兼容复验尚未通过。只有有效讲解且报告输出不超过本次上限才解除对应兼容阻塞；截断、超限、失败或缺失用量如实记录，不提升预算或改推理设置获得通过。返回后的拒绝无法撤销已处理请求或费用，未知用量兼容不能作为计费硬上限保证。M4-T03用户审阅通过保留，不启动后续编号任务。

最终差异审阅通过标准输入Python执行：341份非敏感工程文件中仅13份计划内源码/测试/文档有变动，其余原有文件摘要一致；完整源码差异、UTF-8、文档围栏、本地链接及任务状态一致性通过。另有明确授权的 `.env` 单项非秘密配置变更，不对秘密文件做摘要或副本。`git status --short --branch` 再次确认非Git仓库，未进行Git写操作。本节准备结束时，新预览尚无保存的发送确认或新模型任务。

### M4-T01 一次授权真实预算复验（2026-09-30）

用户对上节具体目标、模型、七段内置示例源码和固定模板、25,583字节、max_tokens=4096、60秒期限、可能计费和失败不重试明确回复“已确认”。提交前重新读取预览，目标、模型、范围、摘要与授权一致；当时讲解任务共3项，无 queued/running。随后仅在现有5177页面勾选确认、点击“保存本次确认”，再点击一次“提交本次讲解”。没有改变配置或扩大源码范围，没有执行导入源码。

**实际结果。** 新任务 `0836010c-5a93-4767-9008-c97e0ffa8031` 于 `2026-09-30T05:05:00.013601Z` 创建，`2026-09-30T05:05:15.979535Z` 终结，从创建到终结15.965934秒（包括排队和应用处理，不等同于纯供应商延迟）。状态 failed、stage failed、错误 MODEL_TRUNCATED、result_url=null。按现有适配器，该错误由 finish_reason=length 触发，早于内容和用量解码；失败任务不保存 usage，因此本次无法从持久记录核验实际输出 token 或账单，不能宣称供应商报告恰好4,096或预算兼容验收已通过。

页面显示失败、不会自动重发及潜在重复计费，单次确认已消费，重试须重新确认且当前按钮禁用。讲解任务总数从3变为4，仅新增上述一项，无 queued/running。当前快照/分析/接口的讲解历史仍只有 `e18ba976-15fa-4135-bae3-fe102373c952`，旧记录可读，输入6464/输出14623/总计21087保持原值。没有发布新讲解，也没有额外确认、重发或提升预算、改变推理设置。

| 工作目录 | 实际命令或操作 | 观察结果 |
| --- | --- | --- |
| `F:\Program\Fall_Campus_Recruitment` | `Get-Location`；`git status --short --branch` | 当前目录正确；Git返回 not a git repository，不初始化或写Git |
| 根目录 | 标准输入 `& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 -`，urllib禁用代理；GET `/api/v1/context-previews/e9446811-6fa0-4b43-8b1e-eaa98ff6f2dc/` | HTTP200，具体目标、模型、摘要、字节数、七段片段、max_tokens与授权一致；读取不发送模型请求 |
| 现有5177浏览器页 | 保存一次确认，提交一次讲解，读取DOM及控制台error/warn | 一次提交进入失败，未重试；MODEL_TRUNCATED及无自动重发提示可见；控制台无error/warn |
| 根目录 | 同一标准输入Python入口；GET `/api/v1/jobs/0836010c-5a93-4767-9008-c97e0ffa8031/`、`/api/v1/jobs/?kind=explanation&page_size=100` | HTTP200；失败码及空结果链接正确；共4项讲解任务，只有一项本次任务，无活动讲解任务 |
| 根目录 | 同一标准输入Python入口；GET `/api/v1/explanations/?snapshot_id=89ff91c0-9cef-4fea-a963-10796476c4a0&analysis_id=704530e6-3814-4aaa-b390-3a9dbec68695&endpoint_index=6&page_size=100` 及旧讲解详情 | HTTP200；当前上下文仅一项旧讲解，ID及原用量不变，没有新发布结果 |
| 根目录 | 同一标准输入Python入口，审阅五份文档的完整差异、341份非敏感文件摘要、UTF-8、Markdown围栏、本地链接及当前状态 | 检查退出0，58处本地链接有效；仅五份任务相关文档变动，源码、测试、依赖、契约生成物及其余原文件摘要不变；不读取或复制.env |

初次只读请求脚本未设置 UTF-8，终端中文输出失真；用 `-X utf8` 再读后确认持久化错误中文正确，不改数据。两次文件定位命令包含不存在的猜测路径，随后用 `rg --files backend/config` 和实际已有序列化器、适配器定位，未创建这些路径或改变实现。

本轮仅同步本文、README、AGENTS、路线图及API清单；清单补记已实现的 MODEL_OUTPUT_BUDGET_EXCEEDED，HTTP方法、路径、DTO及数据库不变。非敏感文档对照和工程摘要位于忽略目录 `.runtime/m4-budget-real-baseline-20260930-0836010c`；失败页面截图 `.runtime/m4-budget-real-test-20260930.png`、脱敏只读核对证据 `.runtime/m4-budget-real-verification-20260930.json` 仅为本地测试产物，不是平行进度来源。没有应用代码改动，不重复执行上节已通过的155项后端、9项前端与静态/类型/构建检查。

**验收结论。** 输出预算发布缺陷的本地修复已完成；本次真实请求正确进入截断失败流程，没有有效完整讲解，M4-T01仍部分完成，真实兼容验收受阻。截断先于预算校验，不能把此失败视作真实超限保护已触发或供应商预算已实证通过；超限保护证据仍来自上节合成传输和发布边界测试。M4-T03的用户人工审阅通过结论保持，v0.1不宣布完成，不推进M6–M10。后续若需调整范围或推理设置，应另行明确方案并取得新的单次外发确认，本轮到此停止。

### M4 按用户要求取消应用模型预算与请求期限（2026-09-30）

**授权与范围。** 用户明确要求“不限制预算和请求限制，只保留请求地址、模型ID和Api key”。此要求替代上两节的模型预算策略，不把既往失败改写为成功。按 PLAN → EXECUTE → TEST → DELIVER 只调整 M4 模型请求、必要的领取续期、历史兼容、测试和文档；未调用真实模型、修改推理设置、执行导入源码、安装/升级依赖或进行 Git 写操作。根目录 `Get-Location` 确认 `F:\Program\Fall_Campus_Recruitment`，`git status --short --branch` 仍为 `not a git repository`，没有初始化。核对根 AGENTS、需求、阶段计划、结构、API、前后端规范和路线图，无独立项目记忆。342份非敏感工程文件摘要和38份必要文件副本位于忽略目录 `.runtime/m4-unlimited-baseline-20260930`，不包含 `.env`、凭据或其摘要。

**实现及取舍。** 模型用户配置仅为 MODEL_BASE_URL、MODEL_NAME、MODEL_API_KEY，旧开关、超时、上下文、输出预算和限额字段不再加载。根 `.env` 仅移除五个废弃的非秘密字段，保留用户原三项配置的字节；不输出、备份或记录其内容。请求体只有 model/messages/stream=false，不发送 max_tokens 或 max_completion_tokens；HTTP timeout=None，不设输入或原始响应字节预算，不按报告用量拒绝有效讲解。usage 仍校验非负整数，缺失保存 null，界面分别显示输入、输出和总用量，费用由用户查看供应商账单。

等待固定传输子进程时，父进程每不超过5秒续期仍有效的 running 领取；轮询不限制请求总时长，不重复发送。丢失领取或续期异常回收子进程；Worker 退出后仍由原核对机制收敛，失效不能复活，迟到结果不能发布。核对已锁定 Celery/Billiard 代码发现 task.time_limit=0 可能回退到进程池默认期限，故将进程池默认软/硬期限设为0，基础检查/导入/分析/实验通过任务注解保留原期限，讲解显式为0。生产5177只读核对确认其他四类仍各300秒。

新预览 configuration 仅含 base_url/model；HTTP操作仍37个，ModelTarget 历史四个预算字段改为可选，只用于读取。旧确认返回 CONSENT_STALE、模型零调用；前端禁用旧预览的确认/提交，要求准备新预览。消息及选中片段完整保留，静态图50/100节点/边范围、五段讲解格式和声明结构、HTTPS/凭据保护、单次确认、无自动重试、拒答/截断/引用及安全文本校验保持。无数据库迁移或历史回填。

**实际检查。** 根目录为 `F:\Program\Fall_Campus_Recruitment`；前端命令工作目录为其 `frontend`，容器命令工作目录 `/workspace/backend`。测试不读取真实 `.env`，使用 `.env.example`、临时 PostgreSQL 测试库、随机 Redis 队列及合成响应。

```powershell
$UnlimitedDocker = 'C:/Program Files/Docker/Docker/resources/bin/docker.exe'
$UnlimitedCompose = @('compose','--env-file','.env.example','-p','learning-lab-m5-verify','-f','compose.yaml','-f','infra/docker/compose.m5-verify.yaml','--profile','task-board')
$UnlimitedTest = @('run','--rm','--no-deps','-e','APP_PORT=5173','-e','APP_ORIGIN=http://127.0.0.1:5173','-v','F:/Program/Fall_Campus_Recruitment/backend:/workspace/backend:ro','-v','F:/Program/Fall_Campus_Recruitment/content:/workspace/content:ro','-v','F:/Program/Fall_Campus_Recruitment/examples:/workspace/examples:ro','-v','F:/Program/Fall_Campus_Recruitment/analyzers:/workspace/analyzers:ro','-v','F:/Program/Fall_Campus_Recruitment/contracts:/workspace/contracts:ro','-v','F:/Program/Fall_Campus_Recruitment/testdata:/workspace/testdata:ro','-w','/workspace/backend','worker','python','-B','-m','pytest')
& $UnlimitedDocker @UnlimitedCompose @UnlimitedTest apps/explanations/tests/test_adapter.py apps/explanations/tests/test_explanations.py tests/test_environment.py --ds=config.settings.local -q -p no:cacheprovider --tb=short
& $UnlimitedDocker @UnlimitedCompose @UnlimitedTest apps/explanations/tests/test_recovery.py apps/analysis/tests/test_graph_api.py --ds=config.settings.local -q -p no:cacheprovider --tb=short
& $UnlimitedDocker @UnlimitedCompose @UnlimitedTest apps tests/test_environment.py --ds=config.settings.local -q -p no:cacheprovider --tb=short
& $UnlimitedDocker @UnlimitedCompose run --rm --no-deps -v F:/Program/Fall_Campus_Recruitment/backend:/workspace/backend:ro -v F:/Program/Fall_Campus_Recruitment/content:/workspace/content:ro -v F:/Program/Fall_Campus_Recruitment/analyzers:/workspace/analyzers:ro -w /workspace/backend worker mypy apps/explanations apps/jobs config/environment.py config/settings/base.py config/settings/local.py tests/test_environment.py
```

| 检查/命令 | 实际观察 |
| --- | --- |
| 上述首轮聚焦 pytest | 83 passed，22.14秒；旧阈值0/4095/4096/4097/14623/100000001均按合法报告用量接受，未知用量兼容；超过旧消息/响应字节预算可读，实际本地HTTP只发一次 |
| 上述领取续期和迁移 pytest | 11 passed，16.27秒；实际Celery prefork等待跨越原领取期限仍成功；进程退出、过期/错误领取、迟到发布与续期异常回收边界通过 |
| 上述完整受影响后端回归 pytest | 最终366 passed，97.48秒；13条多线程环境fork弃用警告，未跳过用例 |
| 上述 mypy | 最终47个源文件无错误 |
| 根目录 `& '.runtime/m1-t02-venv/Scripts/ruff.exe' check backend/apps/explanations backend/apps/jobs/services.py backend/config/environment.py backend/config/settings/base.py backend/config/settings/local.py backend/tests/test_environment.py backend/apps/analysis/tests/test_graph_api.py` | All checks passed |
| 同路径 `ruff format --check` | 27 files already formatted |
| 前端固定Node执行 `node_modules/vitest/vitest.mjs run src/features/explanations/ExplanationPanel.test.tsx` | 12 passed，4.76秒；完整大消息、历史预算预览禁用、未知用量与14623报告显示通过 |
| 前端固定Node执行 `node_modules/typescript/bin/tsc --noEmit`、ESLint对讲解面板/测试/API三个改动文件 `--max-warnings 0`、Prettier对这些文件与生成类型 `--check`、`tooling/generate-api-types.mjs --check` | 类型、lint、格式、生成类型检查通过 |
| 根目录固定Python执行 `-B backend/manage.py spectacular --settings=config.settings.test --validate --file contracts/openapi.yaml`；前端固定Node执行 `tooling/generate-api-types.mjs` | 成功同步OpenAPI与类型；差异只将历史ModelTarget四字段改为可选 |
| 前端 `& '../.runtime/tools/node-v24.21.0-win-x64/node.exe' node_modules/vite/bin/vite.js build` | 成功；主JS503.96kB，保留已有大于500kB提示，未扩展到拆包优化 |
| 根目录 `& $UnlimitedDocker @UnlimitedCompose build --pull=false api frontend` | 固定镜像及依赖安装层使用缓存，后端/前端构建成功；前端容器内tsc及Vite构建通过 |

首轮完整回归实际为347 passed、19个fixture错误，原因是已有 analysis 迁移测试回退时卸载依赖模块，finally 只恢复analysis，后续讲解表不存在。最小修正 `test_graph_api.py` 为保存并恢复原完整迁移图，不改业务迁移或原断言；重跑后366通过。初轮 Ruff/mypy 的导入/格式、空字典注解、模块非显式导出及 TimeoutExpired 可空参数错误已修正，最终检查通过。前端受限进程首次 spawn EPERM，按现有权限规则重跑通过。HTTP核对脚本首次将 context_bytes 误算为仅正文长度；对照既有消息JSON序列化口径修正脚本后通过，没有修改产品口径或触发模型请求。

**5177更新及现状。** 更新前只读确认讲解任务4项、无queued/running。使用原数据卷，仅更新API、Worker和前端：

```powershell
& 'C:/Program Files/Docker/Docker/resources/bin/docker.exe' compose --env-file .env -p learning-lab-m5-verify -f compose.yaml -f infra/docker/compose.m5-verify.yaml -f infra/docker/compose.model-env.yaml --profile task-board up -d --no-build --pull never --no-deps --wait --wait-timeout 120 api worker frontend
```

退出0，三服务healthy，未删除卷、运行迁移或重启其他实例。随后 `exec -T worker python -B -c ...` 只断言配置键为base_url/model、凭据非空、讲解和进程池时限为0、其他四任务时限300；不输出配置或凭据值、不调用模型。标准库 urllib 禁用代理，只读核对项目、快照、分析、新旧预览、旧讲解、旧失败任务及任务列表，八项HTTP200且归属/历史一致。脱敏证据为 `.runtime/m4-unlimited-http-before-20260930.json`、`.runtime/m4-unlimited-http-after-20260930.json`。

实际浏览器验证：刷新原页后，旧预览原4096/max_tokens/60秒信息保留，确认/提交禁用。只点击“准备外发预览”，新预览 `a1b212ec-4ebb-4e7a-9c5c-ef13767b5c94` 显示 https://api.deepseek.com、deepseek-flash、7段25583字节、无遗漏及应用不设限额说明。没有勾选或保存外发确认，没有提交/重试；讲解任务仍4项，无活动任务。原讲解用量6464/14623/21087及原MODEL_TRUNCATED失败均不变，控制台无error/warn。截图 `.runtime/m4-unlimited-preview-20260930.png`，页面保留供用户审阅。

**审阅、记忆和结论。** 38个非敏感工程文件及根.env的非秘密配置行修改，无新业务文件或目录、依赖/锁文件/教学内容/迁移不变；342文件基线中304份保护文件摘要不变。修改文件UTF-8、Python AST、116处现有本地文档链接、新增行空白/冲突标记及所检敏感模式均通过；.env不参与内容扫描、摘要或备份。完整非敏感差异和清单位于基线目录review.diff/changes.json，仅为忽略的审计产物。同步已有AGENTS、README、需求、结构、API契约/清单、两端规范、路线图及本文，消除当前策略仍宣称预算有效的矛盾，保留所有历史验证及M4-T03用户通过结论；没有建立平行记忆系统。

取消应用预算是用户明确的行为变更，不声称能取消供应商容量、默认token、网络/系统或容器资源限制。无限期等待可占用唯一Worker且请求/响应可能增加内存和费用；用户自行决定提交，应用失败无法撤销已发生的供应商费用。结构和引用校验保留，不承诺讲解结论正确。当前策略本地实现与验证完成，真实兼容尚未复验，M4-T01继续部分完成，v0.1未完成；不自动调用、不提高并发或调整推理设置、不推进M6–M10。

手工复核点：在保留的5177页面核对目标、模型、实际片段和字节数，预览不再显示应用预算；旧预览仍有历史参数且不能提交。若用户决定真实试用，须在新预览审阅后自行保存一次确认并提交一次。

### M4-T01 当前策略回归与真实复验准备（2026-09-30）

用户要求补齐 M4-T01。重新检查当前目录、根 AGENTS、实际文件及 Git 状态，读取任务、FR-05、AT-12/13/14、结构、API 契约/清单、两端规范和路线图。当前仍非 Git 仓库，无更深层 AGENTS 或独立项目记忆；不初始化 Git。现有三项配置和无应用预算/请求总期限策略已实现，本轮不修改业务代码、配置、依赖、数据库结构或教学内容，不执行导入源码。修改前342份非敏感工程文件摘要和6份预期文档副本保存在忽略目录 `.runtime/m4-compat-baseline-20260930`，不包含 `.env`、凭据或其摘要。

**预览及确认边界。** 只读 HTTP 与真实页面核对现有新策略预览 `a1b212ec-4ebb-4e7a-9c5c-ef13767b5c94`，绑定快照 `89ff91c0-9cef-4fea-a963-10796476c4a0`、分析 `704530e6-3814-4aaa-b390-3a9dbec68695`、接口 #6（POST /api/v1/tasks/）、模板 explanation/1.0.0。目标为 https://api.deepseek.com/chat/completions，模型 deepseek-flash；完整消息 JSON 的 UTF-8 长度25,583字节，7段内置 task-board/1.0.0 源码的内容摘要全部匹配，无遗漏。预览摘要 `5cd777ba439c53e67cafaa0a152170e92962958601a0360309b07befd752ebaa`，configuration 仅为 base_url/model。片段范围为 serializers.py:8–30、urls.py:5、views.py:36–122、models.py:6–19、backend/config/urls.py:9、TaskBoard.tsx:19–265、tasks-api.ts:68–92，完整路径由预览展示。

准备时讲解任务4项，无 queued/running，旧讲解 `e18ba976-15fa-4135-bae3-fe102373c952` 可读；已保存旧任务及结果的非敏感摘要，供真实提交后核对历史不变。页面的本次确认未勾选，保存和提交按钮禁用。已展示目标、范围、字节数、无应用预算/请求总期限及可能计费说明，并请求新的单次授权；旧真实请求授权已消费，不能复用。截至本节准备验证结束，没有保存新确认或提交真实调用，真实兼容尚不能标记通过。预览截图为 `.runtime/m4-compat-preview-20260930.png`，本地 GET 核对清单为基线目录 `http-before.json`。

**实际检查。** 宿主工作目录为 `F:\Program\Fall_Campus_Recruitment`，聚焦测试容器工作目录为 `/workspace/backend`。仅使用 `.env.example`、临时 PostgreSQL 测试库及合成传输响应，不读取真实密钥、不调用供应商。

```powershell
$CompatDocker = 'C:/Program Files/Docker/Docker/resources/bin/docker.exe'
$CompatCompose = @('compose','--env-file','.env.example','-p','learning-lab-m5-verify','-f','compose.yaml','-f','infra/docker/compose.m5-verify.yaml','--profile','task-board')
$CompatTest = @('run','--rm','--no-deps','-e','APP_PORT=5173','-e','APP_ORIGIN=http://127.0.0.1:5173','-v','F:/Program/Fall_Campus_Recruitment/backend:/workspace/backend:ro','-v','F:/Program/Fall_Campus_Recruitment/content:/workspace/content:ro','-v','F:/Program/Fall_Campus_Recruitment/examples:/workspace/examples:ro','-v','F:/Program/Fall_Campus_Recruitment/analyzers:/workspace/analyzers:ro','-v','F:/Program/Fall_Campus_Recruitment/contracts:/workspace/contracts:ro','-v','F:/Program/Fall_Campus_Recruitment/testdata:/workspace/testdata:ro','-w','/workspace/backend','worker','python','-B','-m','pytest')
& $CompatDocker @CompatCompose @CompatTest apps/explanations/tests/test_adapter.py apps/explanations/tests/test_explanations.py tests/test_environment.py --ds=config.settings.local -q -p no:cacheprovider --tb=short
```

结果：83 passed，23.37秒，退出0。覆盖未配置、非法配置、鉴权/连接/超时/截断等错误、空或非法响应、缺失/非法用量、旧阈值以上的合法用量、完整大消息、引用和安全文本、单次确认、幂等、失败不发布与不重发、历史预览失效及领取续期。该结果为本地回归，不替代选定服务和模型的真实兼容证据；未重复运行已通过的全量回归或构建。

通过项目隔离解释器 `& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 -` 从标准输入运行基线及只读 HTTP 检查；初两次辅助脚本将实际的 sha256/source_ref 字段误写为 content_sha256/path，分别 KeyError，未创建模型任务。对照实际 Serializer 修正辅助脚本后，342文件保护摘要、消息长度、7片段摘要、4项终态任务及旧结果读取断言通过；没有修改产品字段或忽略断言。另准备基线目录 `verify_http.py`，只接收已创建 Job ID 并 GET 检查结果与历史，不具备提交或重试能力；尚未运行真实结果核验。

**准备阶段结论。** 第二阶段计划的进入条件仍写“明确调用预算”，与当前用户要求及配置/适配器冲突；对照现有三项配置、无请求限额实现及本地回归，将该句同步为当前策略与单次确认，保留供应商费用边界。准备结束时 M4-T01 尚未完成，未提前解除门槛；随后取得的单次授权与实际结果见下节。M4进度和验证仅在本文维护，第二阶段任务仍未开始。手工观察点：5177讲解面板显示 deepseek-flash、25,583字节和无应用限额说明，确认未勾选时不能提交；预览和刷新没有模型调用。

### M4-T01 一次授权的当前策略真实兼容验收（2026-09-30）

**授权与范围。** 用户对前节披露的预览、DeepSeek目标、deepseek-flash、7段内置示例及固定模板/关联信息、25,583字节、无应用输出限额/请求总期限和可能计费说明，明确答复“授权这一次真实兼容复验”。提交前再次核对页面摘要与预览 ID，仅勾选并保存本次确认，点击一次“提交本次讲解”；没有使用旧授权、添加片段、调整推理设置、重试或发起其他供应商请求。单次确认已消费，页面保存/提交按钮禁用。

**真实结果。** Job `0b42cd60-b446-409c-bb4d-ed76ffc72be3` 于 `2026-09-30T09:24:59.093896Z` 创建，在 `2026-09-30T09:25:29.996522Z` 终结，状态 succeeded、stage completed、error=null，result_url 指向 `/api/v1/explanations/734fb051-b0d9-4080-94b7-b8a523418e08/`。创建至终结30.902626秒，包含排队和应用处理，不视作纯供应商延迟或容量基准。有效讲解绑定原预览、快照、分析、接口 #6、模板和模型；五段分别4/8/8/7/6条声明，41处引用均位于7段已预览源码内，结构、安全文本和必要依据断言通过。供应商报告输入6464、输出8747、总计15211 token，分别保存与显示；这是当前策略下的合法用量，不作为原4,096预算策略通过或实际账单证据。

**持久化及浏览器。** 讲解任务从4项变为5项，仅新增本次一项，无 queued/running。4项旧任务与旧讲解的完整公共响应摘要与提交前一致，旧截断失败仍保留，预览也未变化。页面通过“阅读本次讲解”打开保存结果，五段和三项用量正确展示；刷新后仍恢复本次 Job/Explanation 及上下文。点击结果中的 serializers.py:8–30 引用，跳转到原快照的 `backend/apps/tasks/api/serializers.py` 第8–30行，快照/分析不变；返回讲解后结果仍可读。浏览器控制台 warn/error 列表为空，没有额外保存确认或提交。

实际检查命令及操作：

| 工作目录 | 实际命令或操作 | 观察结果 |
| --- | --- | --- |
| 根目录 | `& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 '.runtime/m4-compat-baseline-20260930/verify_http.py' 0b42cd60-b446-409c-bb4d-ed76ffc72be3` | 退出0；GET核对绑定、5段33条声明、41处引用、合法用量、仅1项新增及历史摘要不变 |
| 本地5177浏览器 | 保存本次确认 → 提交一次 → 阅读本次讲解 → reload → 点击 serializers.py:8–30 → 返回讲解；读取 warn/error | 成功结果可读，刷新/引用跳转通过，确认已消费，无警告或错误；不执行导入源码 |
| 根目录 | `docker inspect --format '{{.Config.WorkingDir}}' learning-lab-m5-verify-worker-1`；实际使用安装目录的 Docker CLI | 当前Worker工作目录 `/app/backend` |
| 根目录及Worker `/app/backend` | 项目隔离Python经标准输入解析 `docker inspect --format '{{json .Config.Cmd}}'`，再通过 `docker exec -i -w /app/backend learning-lab-m5-verify-worker-1 python -B -c` 比对8份源码摘要 | 正常 `celery -A config.celery:app worker`，无固定替身入口；配置、适配器、传输、内容校验、讲解/Job服务、讲解任务及基础设置与宿主一致，不输出环境或凭据 |

辅助运行检查的首个命令断言误写为 `-A config`，实际文件为 `config.celery:app`，导致 AssertionError；随后误用临时测试容器的 `/workspace/backend` 检查常驻Worker，返回127。对照实际 Dockerfile、Compose 和只读 WorkingDir 修正辅助检查后，两项断言通过，没有修改服务或业务代码，没有追加模型请求。这些是检查脚本问题，不是供应商或产品失败。

证据为基线目录 `submitted-job.json`、`http-after.json`、`runtime-review.json`，以及 `.runtime/m4-compat-result-20260930.png`、`.runtime/m4-compat-source-20260930.png`。本地证据只作审计，不是平行进度或记忆；持久结果仍由数据库与原 API 提供。核心知识与取舍：兼容验收同时要求传输、格式、引用和原子发布有效，不能只看HTTP成功；应用按用户要求不控制模型预算，供应商报告用量与账单分开，单次确认和失败不重发仍保留。手工复核点：打开本次讲解核对输入6464/输出8747/总计15211，再点击序列化器引用核对原快照8–30行；有效行号不保证解释语义正确。

**最终审阅与记忆同步。** 根目录实际运行 `& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 '.runtime/m4-compat-baseline-20260930/verify_docs.py'`，退出0；342文件基线仅7份文档变更，335份其余保护文件不变，75处本地文件链接、UTF-8/围栏、辅助脚本AST、新增行空白/冲突与所检敏感模式通过，18项首阶段任务为已完成、10项第二阶段任务仍未开始。浏览器刷新与引用跳转后重跑前述 `verify_http.py`，退出0，仍仅1项新增任务，历史及预览摘要保持不变。完整非敏感差异与检查结果为基线目录 `review.diff`、`document-review.json`，不是新进度系统。

最终一致性检查发现结构文档仍写“真实模型兼容性仍未验收”；对照本次持久结果与运行源码检查更新该现状，并在修改前补充第7份文档副本。第二阶段的旧模型预算条件也已修正，旧历史修订及失败记录保留。同步已有AGENTS、README、两份阶段计划、结构、API清单和路线图；任务证据只在本文维护，其他文档只引用结论。需求、契约、前后端规范的当前行为未变，核对后无需修改。没有独立项目记忆文件或新记忆系统，不读取、改写、备份或摘要真实.env与凭据。最终 `git status --short --branch` 仍为非Git仓库，未初始化或进行Git写操作。

**当前验收及v0.1交付结论。** M4-T01 在既有合成错误回归与本次选定服务/模型的基础非流式成功范围内完成；83项本地聚焦回归见前节，其他已通过检查不伪称本轮重跑。M4-T03的独立人工内容审阅通过结论与固定教学内容保持，本轮没有代替用户宣布新生成文本的语义完全正确。结合本文已有M1–M5记录，标准样例在Windows x64宿主/Linux amd64参考环境下的v0.1本地验收完成，原真实模型兼容阻塞已解除，历史预算缺陷及失败不改写。37个HTTP操作、数据库结构、依赖、配置和业务代码均未变；只同步本文及受影响文档入口。

v0.2进入门槛已满足，M6–M10仍未开始，本轮到此停止。该兼容结论只适用于已测试的地址、模型、模板、源码范围和当前策略，不自动推广至其他服务/模型、流式/工具调用、长请求或大规模容量；改变目标后需重新验收。应用不设期限可能占用唯一Worker，供应商自身限制仍存在，费用须由用户查看供应商账单；本次未核验账单。后续开发仍需用户明确指定任务，不以规划文档或本次通过自动开工。

## 11. 文档与项目记忆同步

本项目初始没有独立项目记忆文件。项目文档承担长期依据，不另建平行记忆系统。按版本分开的阶段计划分别拥有互不重叠的任务编号；本文不复制维护 M6–M10 的进度，后续文档也不得重新判定 M1–M5 的历史验收。

每次完成任务都检查是否影响需求、版本边界、模块职责、接口、命令或限制；有变化时修改负责该事项的文档、相关链接和修订记录。没有长期知识变化时，在交付中明确说明无需更新及原因。

记录内容以实际实现为准；实现偏离确认需求时先修复或显式变更需求，不能仅改文档来把失败行为描述为预期。

## 12. 修订记录

| 版本 | 日期 | 变更 | 实现状态 |
| --- | --- | --- | --- |
| v0.1 | 2026-09-28 | 建立 M1 至 M5 任务、依赖、学习产出、需求追踪和验证记录规则 | 文档已建立，所有开发任务未开始 |
| v0.2 | 2026-09-28 | 加入结构与执行入口、单任务状态和前置规则，同步端点职责与文档导航 | 仅文档更新，产品任务未开始 |
| v0.3 | 2026-09-28 | 进入 M1-T01，建立依赖与工具检查基线并记录验证边界 | M1-T01 验收受阻，业务及产品用例未开始 |
| v0.4 | 2026-09-28 | 修复声明冲突，增加官方 wheel 缓存安装并完成两端工具验收 | M1-T01 已完成；M1-T02 未开始，产品用例未执行 |
| v0.5 | 2026-09-29 | 完成固定基础检查、同源服务、持久化/幂等/期限核对，记录真实安全与故障验收 | M1-T01、M1-T02 已完成；其余任务未开始 |
| v0.6 | 2026-09-29 | 完成独立任务示例、人工关系基准及聚焦行为验证 | M1-T01 至 M1-T03 已完成；M1-T04 及后续未开始 |
| v0.7 | 2026-09-29 | 完成 M1 契约表、错误边界、生成漂移检查及实际响应验证 | M1 已完成；M2–M5 未开始 |
| v0.8 | 2026-09-29 | 完成项目导入、快照/受控读取及安全/中断验证 | 仅 M2-T01 新增完成，其他任务保持原状态 |
| v0.9 | 2026-09-29 | 完成 Python/DRF 静态分析、来源、覆盖和诊断及相关验收 | 仅 M2-T02 新增完成，其他任务保持原状态 |
| v0.10 | 2026-09-29 | 完成有界图存储、证据、BFS/DFS、API-13 及历史兼容验收 | 仅 M2-T03 新增完成，M2-T04 及后续未开始 |
| v0.11 | 2026-09-29 | 完成现有任务显式重试、幂等、故障收敛和历史兼容验收 | M2-T04 与 M2 完成，未启动 M3 |
| v0.12 | 2026-09-29 | 完成受控前端解析、保守关联、源码工作区及隔离浏览器验收 | M3-T01/T02/T03 完成，M4/M5 未开始 |
| v0.13 | 2026-09-29 | 实现 M4 本地模型边界、讲解确认和版本化固定练习，补充真实本地验收 | T02 完成，T01 真实兼容与 T03 独立人工审阅仍待验收；M5 未开始 |
| v0.14 | 2026-09-29 | 完成M5固定实验、本地闭环、故障/隔离验证与交付归档 | M5本地完成；保留M4真实模型与独立人工审阅缺口，不宣布v0.1完成 |
| v0.15 | 2026-09-30 | 链接第二阶段计划，明确进度归属和先完成 v0.1 的门槛 | 原任务状态及验收记录不变 |
| v0.16 | 2026-09-30 | 按用户要求准备本地模型 .env 和仅 Worker secret 的可选启动配置 | 合成配置合并检查通过；等待填写后启动和人工审阅 |
| v0.17 | 2026-09-30 | 修正 Windows 环境源 secret 的运行兼容问题，启动现有5177人工审阅实例 | 配置、9个常驻容器、Worker及只读HTTP验证通过；没有模型调用，人工验收待完成 |
| v0.18 | 2026-09-30 | 记录419项回归、浏览器/HTTP闭环及一次授权真实讲解；归档输出预算超限缺陷 | M4-T01验收阻塞，M4-T03待用户终审；未改业务代码或自动重发 |
| v0.19 | 2026-09-30 | 记录用户对当前版本的独立人工内容审阅确认，同步当前状态入口 | M4-T03完成；M4-T01预算缺陷仍阻塞，v0.1未完成，后续任务未启动 |
| v0.20 | 2026-09-30 | 修复输出用量超限发布缺陷，明确未知用量和费用边界，更新5177并准备新预览 | 本地回归通过；真实复验待单次确认，M4-T01仍部分完成 |
| v0.21 | 2026-09-30 | 记录一次明确授权的真实预算复验、截断失败及未发布/未重发边界，同步当前入口 | 本地缺陷修复完成；真实兼容验收仍受阻，保留M4-T03通过，未推进后续任务 |
| v0.22 | 2026-09-30 | 按用户要求取消模型应用预算及请求总期限，保留三项配置、单次确认、领取续期和历史兼容 | 本地实现/验证完成，新策略真实兼容待验收；保留M4-T03通过，不推进后续任务 |
| v0.23 | 2026-09-30 | 完成83项聚焦回归与一次授权的当前策略真实兼容，核对结果、刷新、引用和历史，修正入口文档 | M4-T01完成，v0.1本地验收完成；v0.2门槛满足，M6–M10未开始 |
