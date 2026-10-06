# 项目解读实验室：API 分类与版本清单

| 项目 | 内容 |
| --- | --- |
| 文档版本 | v0.25 |
| 文档状态 | 83 个工作台操作（含退役兼容入口）及生成契约；实际验收见所属阶段计划 |
| 更新日期 | 2026-10-03 |
| 适用阶段 | 产品 v0.1 至 v1.0 已实现清单；工作台 HTTP API v1 |
| 本文职责 | API 分类、首版方法与路径、模块归属及开发任务的权威来源 |

## M26 当前兼容与增量

M26 是当前生效范围，M1–M25 的实现描述与验收保留为阶段历史。课程、先修路径、学习进度、固定练习、作答/自评、受控实验、快照对比、候选影响、人工关系校准、通知写入和基础检查已退役；旧业务写入口返回 `410 FEATURE_RETIRED`，历史模型、迁移和必要 GET 保留。旧队列消息及通用重试不能恢复执行。当前进度与实际证据唯一见[第四阶段计划 M26](phase-4-plan.md#m26)。

当前83项HTTP操作。旧退役写契约保留operation_id和路径，标记deprecated且410，正常同源边界仍适用；旧GET保留必要历史读取，新增实例不发布课程或练习。以下旧阶段成功模式/执行说明为历史定义，不能绕过本节退役规则。

API-74日志列表在原端点增加q名称搜索，API-74/75响应增加固定数字display_id；不增加端点或替换UUID详情路径。日志q匹配类型中文名称/代码、操作对象与保存的项目名称，可与四列条件组合；具体长度、数字范围和分页以API契约规范及生成类型为准。

## 1. 使用方法与边界

本文确定首版端点范围和类型管理方式。[API 契约规范](api-conventions.md)统一维护响应、错误、分页、四态任务、幂等、快照与外发确认；本文引用这些规则，不另设协议。目录和命名见[项目结构](project-structure.md)，任务及验收见[阶段计划](phase-1-plan.md)和[需求文档](requirements.md)。

当前 API-01 至 API-83 对应实现，OpenAPI 与前端类型从实现生成；v0.1 验证见首阶段计划，v0.2 验证见[第二阶段计划](phase-2-plan.md)，v0.3 验证见[第三阶段计划](phase-3-plan.md)，快照命名及 M25 首页所需搜索、通知与阅读进度的实际状态唯一见[第四阶段计划](phase-4-plan.md)。业务字段、过滤参数、排序、资源就绪条件及逐项错误在下文对应接口设计中说明；Schema 从实现导出。

初始 v1.0 保持 56 个操作；用户随后授权快照名称 API-57、M25 的 API-58 至 API-62。HTTP v1 与内容版本保持，工程回归和验收证据见[第四阶段计划](phase-4-plan.md)。

同一路径的不同方法分开编号，当前共 83 个 HTTP 操作。API 编号用于文档追踪，`operation_id` 用于机器契约；两者保持稳定，不能因文件移动或 View 类改名而无意改变。

## 2. API 分类

| 类型 | 形式 | 用途与边界 |
| --- | --- | --- |
| 同步资源接口 | REST + JSON | 查询项目、快照、分析结果、知识和历史记录；同步创建轻量记录 |
| 文件上传接口 | HTTP multipart | 上传ZIP或目录清单/文件并提交导入任务 |
| 长任务接口 | HTTP 202 + 任务轮询 | 导入、扫描、分析、讲解、删除；成功接收不等于完成 |
| 源码读取接口 | 受控 HTTP 读取 | 用快照和文件标识定位；内容类型及分段上限在 M2-T01 明确 |
| 外部模型接口 | 服务端 Chat Completions | 非流式讲解；必须经过外发预览和确认 |
| 内部解析接口 | 子进程 stdin/stdout JSON | Python Worker 调用本地 Node 程序；没有独立 HTTP 服务 |
| 内部实验接口 | 固定 HTTP 地址与允许输入 | 调用受控示例；不能提交任意地址或运行导入代码 |

工作台浏览器只调用工作台 HTTP API；独立教学示例页面只调用自身同源服务，见 4.6 节。首版长任务使用轮询，不增加 GraphQL、WebSocket 或 SSE；模型接口、解析器协议和示例接口不列为浏览器可调用的工作台端点。

## 3. 类型与契约的归属

| 对象 | 目标位置 | 规则 |
| --- | --- | --- |
| 持久化模型 | `backend/apps/<模块>/models.py` 或职责包 | 表达存储及约束，不直接充当 HTTP DTO |
| HTTP 输入输出 | `backend/apps/<模块>/api/serializers.py` 或职责包 | 分开定义输入、输出、列表、错误；只有接口允许的字段可以外发 |
| 公共协议处理 | `backend/common/` | 统一错误、分页、CSRF 等技术能力，不承载业务流程 |
| OpenAPI | `contracts/openapi.yaml` | 由 drf-spectacular 从后端导出并校验，生成结果仍需与设计核对 |
| 前端生成类型 | `frontend/src/shared/api/generated/schema.d.ts` | 由 OpenAPI 生成；禁止手工修改 |
| 功能 API 与类型别名 | `frontend/src/features/<功能>/api/`、`types.ts` | 引用生成类型，可定义明确别名；不复制同一 DTO 的字段结构 |
| 页面和表单状态 | 所属 feature 的组件、hooks 或 `types.ts` | 与 DTO 分开；不写入生成目录 |
| Python 内部结果 | 所属模块的 `types.py` 或职责包 | 使用明确类型；独立于 ORM 与 HTTP 表达 |
| Node 解析协议 | `contracts/typescript-analysis.schema.json` | 人工维护的 JSON Schema；共同约束输入、输出及协议版本 |

契约生成链为：接口语义 → Serializer/View → OpenAPI → 前端类型。HTTP 字段保留 `snake_case`，类型名用 `PascalCase`。稳定的 `operation_id` 使用 `资源_动作`，例如 `projects_list`、`projects_create`、`analyses_create`、`jobs_retry`；同一 HTTP 操作只能有一个唯一标识。

生成类型只能检查编译期形状，不能替代外部输入、模型输出和跨进程消息的运行时校验。解析器只接收受控源码文本及必要元数据，不能接收可执行命令、加载项目配置或安装导入项目依赖。stdout 只输出协议数据，stderr 输出有界且脱敏的诊断；M3 已固定成功退出 0、协议失败退出 2、60 秒期限和输入/输出预算；stderr 不回传，失败映射与两端校验见 4.12。

## 4. 清单中的公共约定

- 下表路径完整包含 `/api/v1/`，所有路径使用尾斜杠。`csrf` 是基础协议入口，`graph` 是单个分析结果的图表示；它们是明确的单数例外。
- **读取**：成功返回 `200`；列表使用统一分页。图与源码是有界的单个表示，不机械拆成分页列表。
- **同步创建**：首次创建返回 `201` 和资源；不创建后台任务。
- **异步提交**：可靠接收返回 `202`、任务资源及同源 `Location`；最终业务结果由任务的 `result_url` 指向。
- 所有业务 POST 都要求 `Idempotency-Key`。同键同请求返回 `200` 和原有资源或任务；同键不同请求返回 `409 IDEMPOTENCY_CONFLICT`。具体规则以 [API 幂等约定](api-conventions.md#job-contract)为准。
- 每个操作同时继承本地来源保护、错误格式和必要快照绑定；表内需求为主要追踪项，不排除适用的公共 NFR。
- 多任务归属表示分阶段负责同一个端点；后续任务扩充已经存在的能力，不创建重复接口。M1-T02 仅建立本任务接口所需的最小生成入口；M1-T04 整理两套现有服务契约与检查基线，见 4.7。

### 4.1 本地请求保护、项目与源码

| 编号 | 方法 | 路径 | 职责 | 模块 | 开发任务 | 需求 | 成功模式 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| API-01 | GET | `/api/v1/csrf/` | 获取标准 CSRF 令牌并设置 Cookie，禁止缓存 | common / config | M1-T02 | NFR-04 | 读取 |
| API-02 | GET | `/api/v1/projects/` | 项目列表 | projects | M2-T01 | FR-01、FR-08 | 读取 |
| API-03 | POST | `/api/v1/projects/` | 创建项目记录，不上传源码 | projects | M2-T01 | FR-01 | 同步创建 |
| API-04 | GET | `/api/v1/projects/{project_id}/` | 项目详情 | projects | M2-T01 | FR-01、FR-08 | 读取 |
| API-05 | POST | `/api/v1/projects/{project_id}/imports/` | multipart ZIP 上传并提交导入任务 | projects | M2-T01 | FR-01 | 异步提交 |
| API-06 | GET | `/api/v1/projects/{project_id}/snapshots/` | 项目已发布快照列表 | projects | M2-T01 | FR-01、FR-08 | 读取 |
| API-07 | GET | `/api/v1/snapshots/{snapshot_id}/` | 快照详情、导入摘要与支持范围 | projects | M2-T01 | FR-01、FR-08 | 读取 |
| API-08 | GET | `/api/v1/snapshots/{snapshot_id}/files/` | 当前快照的受控文件清单 | projects | M2-T01 | FR-01、FR-04 | 读取 |
| API-09 | GET | `/api/v1/snapshots/{snapshot_id}/files/{file_id}/content/` | 受控源码读取与行号定位 | projects | M2-T01、M3-T03 | FR-04 | 读取 |
| API-57 | PATCH | `/api/v1/snapshots/{snapshot_id}/` | 更新服务端快照名称，保留源码及关联 | projects | 用户追加 UI 调整 | FR-01、FR-08 | 同步更新 |

项目创建与导入分开。导入失败保留项目记录和失败任务，不发布半成品快照。源码读取验证 `file_id` 确实属于该快照；源码引用的 `file_path` 仍按 API 公共协议表达，由文件清单解析为读取标识，不能把相对路径直接当宿主路径。

### 4.2 分析与任务

| 编号 | 方法 | 路径 | 职责 | 模块 | 开发任务 | 需求 | 成功模式 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| API-10 | POST | `/api/v1/snapshots/{snapshot_id}/analyses/` | 提交当前快照分析 | analysis | M2-T02 | FR-02 | 异步提交 |
| API-11 | GET | `/api/v1/analyses/{analysis_id}/` | 分析详情、规则版本与覆盖摘要 | analysis | M2-T02 | FR-02 | 读取 |
| API-12 | GET | `/api/v1/analyses/{analysis_id}/endpoints/` | 识别的接口及关联摘要 | analysis | M2-T02、M3-T02 | FR-02、FR-03 | 读取 |
| API-13 | GET | `/api/v1/analyses/{analysis_id}/graph/` | 有界关系图、引用及截断说明 | analysis | M2-T03、M3-T02 | FR-03、FR-04 | 读取 |
| API-14 | GET | `/api/v1/analyses/{analysis_id}/diagnostics/` | 未支持写法、解析失败和关联缺口 | analysis | M2-T02 | FR-02 | 读取 |
| API-15 | GET | `/api/v1/jobs/` | 可恢复的任务历史列表 | jobs | M1-T02、M2-T04 | FR-08 | 读取 |
| API-16 | GET | `/api/v1/jobs/{job_id}/` | 任务状态、结果链接或失败原因 | jobs | M1-T02、M2-T04 | FR-08 | 读取 |
| API-17 | POST | `/api/v1/jobs/{job_id}/retries/` | 显式新建失败任务的下一次尝试 | jobs | M2-T04 | FR-08 | 异步提交 |

任务四态只在 [API 规范](api-conventions.md#job-contract)定义。分析详情属于 `analysis`，任务生命周期属于 `jobs`；业务模块通过自己的提交接口创建任务，不增设可任意指定命令的通用任务创建接口。

重试只适用于允许重试且前置资源仍有效的失败任务，保留旧尝试。模型任务重试仍需核对原确认范围与当前服务配置，不能绕过外发确认；实验重试仍需隔离数据，不能误用上一运行的观测。具体任务的重试条件在所属任务接口设计中填写。

### 4.3 讲解与外发确认


| 编号 | 方法 | 路径 | 职责 | 模块 | 开发任务 | 需求 | 成功模式 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| API-18 | POST | `/api/v1/context-previews/` | 准备并保存有界外发预览，不调用模型 | explanations | M4-T02 | FR-05 | 同步创建 |
| API-19 | GET | `/api/v1/context-previews/{preview_id}/` | 查看绑定快照、片段、模板及脱敏目标 | explanations | M4-T02 | FR-05 | 读取 |
| API-20 | POST | `/api/v1/context-previews/{preview_id}/consents/` | 保存用户对该预览范围的发送确认 | explanations | M4-T02 | FR-05 | 同步创建 |
| API-21 | GET | `/api/v1/explanations/` | 已有讲解列表 | explanations | M4-T02 | FR-05、FR-08 | 读取 |
| API-22 | POST | `/api/v1/explanations/` | 验证确认后提交讲解任务 | explanations | M4-T01、M4-T02 | FR-05 | 异步提交 |
| API-23 | GET | `/api/v1/explanations/{explanation_id}/` | 讲解内容、来源分类与有效引用 | explanations | M4-T02 | FR-05、FR-08 | 读取 |

M4-T01 先建立模型适配层，API-22 的可供用户使用的提交链在 M4-T02 完成外发确认后才成立。预览或确认创建成功不能自动触发模型调用。用户拒绝时不提交确认和讲解；修改范围后重新预览确认，不复用失效凭据。

### 4.3.1 M4 已实现契约

本节为 M4 的实施契约，实际验收仅记录在阶段计划。所有新增 POST 沿用 UUID 操作键、严格 JSON、Origin/CSRF、同键重放 200 与冲突 409；不接受未知字段。

| 工程 | 方法 | 路径 | operation_id | 请求与结果 |
| --- | --- | --- | --- | --- |
| workbench | POST | `/api/v1/context-previews/` | `context_previews_create` | analysis_id、endpoint_index、可选 node_ids/excluded_snippets；201 不可变预览，不调用模型 |
| workbench | GET | `/api/v1/context-previews/{preview_id}/` | `context_previews_retrieve` | 已保存消息、片段、来源、模板、目标、预算与遗漏 |
| workbench | POST | `/api/v1/context-previews/{preview_id}/consents/` | `context_consents_create` | accepted=true；201 单次发送确认，不调用模型 |
| workbench | GET | `/api/v1/explanations/` | `explanations_list` | 可按 snapshot_id、analysis_id、endpoint_index 筛选；按 created_at/id 倒序分页 |
| workbench | POST | `/api/v1/explanations/` | `explanations_create` | consent_id；202 explanation 任务；提交时原子消费确认 |
| workbench | GET | `/api/v1/explanations/{explanation_id}/` | `explanations_retrieve` | 五段讲解、证据、快照、模型、模板、时间及可空用量 |
| workbench | GET | `/api/v1/knowledge-cards/` | `knowledge_cards_list` | 按 slug/version/id 排序分页，无模型依赖 |
| workbench | GET | `/api/v1/knowledge-cards/{card_id}/` | `knowledge_cards_retrieve` | 版本化卡片和适用范围 |
| workbench | GET | `/api/v1/exercises/` | `exercises_list` | 必须给出 analysis_id、endpoint_index；返回该工作区的题目和适用性，不含答案 |
| workbench | GET | `/api/v1/exercises/{exercise_id}/` | `exercises_retrieve` | 同样要求工作区参数；返回题干、提示、版本、选项和适用性 |
| workbench | GET | `/api/v1/exercise-attempts/` | `exercise_attempts_list` | 可按 snapshot_id、analysis_id、endpoint_index 筛选；按 created_at/id 倒序分页 |
| workbench | POST | `/api/v1/exercise-attempts/` | `exercise_attempts_create` | 已退役：410 FEATURE_RETIRED，零业务写入/投递 |
| workbench | GET | `/api/v1/exercise-attempts/{attempt_id}/` | `exercise_attempts_retrieve` | 历史题干、答案版本、用户答案、提示使用、反馈与来源 |

预览绑定规范化配置、模板、完整消息及片段摘要。确认只允许一次新任务，重复消费返回 CONSENT_STALE；同键恢复已存在任务不触发重新校验或外发。提交与执行前检查配置及快照完整性，变更须重新预览。模型任务重试通过 API-17 提交新的 consent_id，内容必须与原预览相同；不改变已有三类任务的正文。MODEL_NOT_CONFIGURED、MODEL_CONFIGURATION_INVALID、CONSENT_STALE、EXERCISE_VERSION_MISMATCH、EXERCISE_NOT_APPLICABLE 使用 409；任务错误分别表达鉴权、限流、传输、超时、拒答、截断、结构及引用失败。原始供应商错误不回传。

题目输入按类型固定：flow_order 为步骤标识数组；error_prediction 为场景标识到 status/writes 的映射；code_location 为 file_path/start_line/end_line。答案、反馈和题干绑定版本，GET 题目不得输出答案。样例以规范化源码摘要及 POST /api/v1/tasks/ 归属匹配，错误版本不套用标准答案。源码定位允许范围在题目中明确，服务端校验后才评分。


预览输入 `node_ids` 最多 50 个 UUID，必须属于所选接口的有界图；`excluded_snippets` 最多 50 个预览片段 id（引用范围的 SHA-256），不能提供任意路径或正文。改变节点选择时排除集合重新选择。片段响应另有正文 SHA-256，范围 id 不等于内容摘要；配置、消息及所有片段一起参与 `payload_digest`。默认节点/边上限 50/100，不设模型字节预算，完整保留选中片段；`context_bytes` 是完整消息实际 UTF-8 字节数。`omissions` 记录图截断或 user_excluded，历史 context_bytes 遗漏仍可读取。新 configuration 仅为 base_url/model，历史四个预算字段为可选读取字段；旧确认失效，需新预览。

作答额外核对 `snapshot_id` 与 `analysis_id` 的归属，不能仅凭相同路径或项目名匹配。流程答案是所有选项 id 的有序数组；错误预测是每个场景 id 对应 `{status: integer, writes: 0|1}`；代码定位为 `{file_path, start_line, end_line}`，完整字段声明要求精确范围。题干、答案、示例版本均随记录可读；答案类型由服务端题型确定，额外键、非法整数、越界和缺失项拒绝。五个筛选/分页参数使用有界公共输入规则，超限明确拒绝。

讲解任务 `kind=explanation`、`stage=generating`，`result_url` 指向 API-23。输出五段内的每条声明有 kind/text/source_refs；`source_fact` 和 `static_inference` 必须引用预览范围，evidence 段至少一个有依据声明，`general_principle` 可无引用。任务机器码包含 MODEL_AUTH_FAILED、MODEL_RATE_LIMITED、MODEL_CONNECTION_FAILED、MODEL_TIMEOUT、MODEL_SERVICE_ERROR、MODEL_REFUSED、MODEL_TRUNCATED、MODEL_EMPTY_RESPONSE、MODEL_INVALID_RESPONSE、MODEL_INVALID_EVIDENCE、MODEL_UNSAFE_CONTENT；丢失领取使用 EXECUTION_INTERRUPTED。新请求不产生 MODEL_RESPONSE_TOO_LARGE 或 MODEL_OUTPUT_BUDGET_EXCEEDED，历史错误不改写。报告用量仅校验合法非负整数，缺失继续按未知兼容；不设请求总期限或输出限额，费用及供应商限制由用户判断。等待时续期领取，终态或失效领取拒绝发布。每次任务至多一次供应商请求，正文或原始错误不写日志。

### 4.4 学习与实验

| 编号 | 方法 | 路径 | 职责 | 模块 | 开发任务 | 需求 | 成功模式 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| API-24 | GET | `/api/v1/knowledge-cards/` | 知识卡片列表 | learning | M4-T03 | FR-06 | 读取 |
| API-25 | GET | `/api/v1/knowledge-cards/{card_id}/` | 卡片内容与适用范围 | learning | M4-T03 | FR-06 | 读取 |
| API-26 | GET | `/api/v1/exercises/` | 练习列表，不返回标准答案 | learning | M4-T03 | FR-06 | 读取 |
| API-27 | GET | `/api/v1/exercises/{exercise_id}/` | 题干、版本及作答要求，不返回标准答案 | learning | M4-T03 | FR-06 | 读取 |
| API-28 | GET | `/api/v1/exercise-attempts/` | 作答历史 | learning | M4-T03 | FR-06、FR-08 | 读取 |
| API-29 | POST | `/api/v1/exercise-attempts/` | 同步校验固定题答案，保存作答及反馈 | learning | M4-T03 | FR-06 | 同步创建 |
| API-30 | GET | `/api/v1/exercise-attempts/{attempt_id}/` | 指定作答的结果、反馈与题目版本 | learning | M4-T03 | FR-06、FR-08 | 读取 |
| API-31 | GET | `/api/v1/labs/` | 固定实验列表 | labs | M5-T01 | FR-07 | 读取 |
| API-32 | GET | `/api/v1/labs/{lab_id}/` | 实验说明、允许输入及示例来源 | labs | M5-T01 | FR-07 | 读取 |
| API-33 | POST | `/api/v1/labs/{lab_id}/runs/` | 提交一次受控实验运行 | labs | M5-T01 | FR-07 | 异步提交 |
| API-34 | GET | `/api/v1/lab-runs/` | 实验运行记录列表 | labs | M5-T01 | FR-07、FR-08 | 读取 |
| API-35 | GET | `/api/v1/lab-runs/{run_id}/` | 运行来源、输入、实际观测及失败诊断 | labs | M5-T01 | FR-07、FR-08 | 读取 |

标准答案保存在服务端教学内容中，不打包到浏览器静态资源，也不藏在题目 DTO 的其他字段里；完成作答后返回与该尝试绑定的反馈。题目、答案和尝试记录绑定内容版本及适用快照/示例，不能把其他版本成绩套用到当前项目。

实验定义可描述预期行为；实际运行响应和写入变化仅来自真实观测。运行结果始终标明内置示例及版本，用户预测与观测分开记录；失败时已取得的观测与缺失项均可查看。

### 4.5 M1-T02 基础链路检查（2026-09-29 确认）

为验证真实匿名写请求与后台任务链路，用户确认增加固定检查入口；不接受任务种类、命令、文件、URL 或业务参数。以下是本任务编码前的接口设计，实际验收状态仅见阶段计划。

| 编号 | 方法与路径 | operation_id | 输入与输出 |
| --- | --- | --- | --- |
| API-36 | POST `/api/v1/system-checks/` | system_checks_create | JSON 必须为 `{}`；UUID 形式 `Idempotency-Key`；首次可靠接收返回 202 和公共任务，重放返回 200，Location 指向任务 |
| API-37 | GET `/api/v1/system-checks/{check_id}/` | system_checks_retrieve | 成功的固定检查结果：id、job_id、check_version、database、queue、worker、completed_at；未就绪或不存在返回 404 |

API-01 返回 `csrf_token`，设置 host-only、SameSite=Strict 的 Cookie，禁止缓存。所有不安全方法要求精确匹配 APP_ORIGIN 的 Origin 和标准 X-CSRFToken；不接受 Referer 代替缺失 Origin，不信任客户端转发头。Host 必须匹配选定入口的主机与端口。

API-15 仅接受 page/page_size，按 created_at 降序、id 降序分页；API-16 使用不透明 UUID 标识。返回公共任务全部字段，固定检查的 kind 为 system_check，snapshot_id/previous_job_id/progress 为 null；排队 stage=queued、执行 stage=checking、终态 stage=completed/failed。成功 result_url 指向 API-37；检查结果只证明该次队列交付和 Worker 数据库写入，不代表持续可用性或业务分析结果。

API-36 的幂等范围为 system_checks_create，摘要为规范化空对象；数据库唯一键覆盖并发请求。同键重放不再次投递，带未知输入拒绝为 400，不将额外字段静默忽略。提交先持久化再投递；投递异常返回 503、任务 Location 及脱敏错误，同时保存失败任务。客户端可用原键恢复查询。数据库不可用返回 503，不声称已接收。

共有错误沿用统一对象：400 VALIDATION_ERROR、403 ORIGIN_REJECTED/CSRF_REJECTED、404 RESOURCE_NOT_FOUND/PAGE_NOT_FOUND、409 IDEMPOTENCY_CONFLICT、415 UNSUPPORTED_MEDIA_TYPE、503 SERVICE_UNAVAILABLE。固定任务失败使用 QUEUE_UNAVAILABLE、QUEUE_TIMEOUT、EXECUTION_TIMEOUT、CHECK_FAILED。初始排队/执行期限各 300 秒；独立核对进程每 5 秒处理超期，启动时也核对。终态不可覆盖；本任务不实现 API-17 显式重试。

对应 FR-08、NFR-03、NFR-04、AT-24，以及 AT-18/19/20 中仅涉及基础任务的子场景。当前三类任务的恢复见 4.11；后续作答、模型和实验仍由所属任务验收。

### 4.6 M1-T03 独立教学示例契约

以下操作属于 `examples/task-board` 的独立服务，通过 `http://127.0.0.1:5174` 同源访问，不加入工作台的 37 个操作。示例版本为 `task-board/1.0.0`，对应 FR-02/03/06/07，为 AT-04/07/16 提供基准；默认公开配置不加载实验运行接口，M5 专用内部配置见 4.13。

| 方法与路径 | operation_id | 约定 |
| --- | --- | --- |
| GET `/api/v1/csrf/` | task_board_csrf_retrieve | 标准令牌和独立 Cookie 名 `task_board_csrftoken`，禁止缓存 |
| GET `/api/v1/tasks/` | task_board_tasks_list | 公共页码分页，按 `created_at`、`id` 倒序；仅允许 page/page_size |
| POST `/api/v1/tasks/` | task_board_tasks_create | JSON 对象仅含必填字符串 title；去掉首尾空白后长度 1–200；拒绝缺失、null、非字符串、空白、未知字段和 NUL 字符 |

资源包含只读 `id`（UUID）、`title`、`created_at`（UTC）；新建返回 201。写请求必须提供精确 Origin、X-CSRFToken 和 UUID Idempotency-Key；键仅用于创建任务这一动作。服务端以规范化标题作为请求摘要的等价比较值，数据库唯一键保护并发；同键同标题返回原资源及 200，同键不同标题返回 409。记录与键一并保留，不隐式过期；不同键允许同名任务。错误沿用公共对象及 400/403/404/409/413/415/500/503 分类。

浏览器禁止自动重发写请求。会话仅保存必要操作键；提交结果不确定时保留原标题、锁定编辑并显式恢复；刷新后用户重新输入原标题配合原键恢复，冲突不会新建。成功后重新查询第一页；查询失败明确说明已创建但列表未刷新。示例数据与工作台数据库完全分离，不绑定虚构 snapshot_id。人工标注绑定示例版本和文件 SHA-256；真正导入后再由后续任务映射到不可变快照。

示例自身的 Schema 位于 `examples/task-board/contracts/openapi.yaml`，生成类型位于其 `frontend/src/shared/api/generated/schema.d.ts`。M1-T04 的全阶段契约核对见 4.7。

### 4.7 M1 契约核对表与错误基线

下表记录 M1 已有实现，与 4.8–4.13 一起供 `scripts/check_contracts.py` 与三份独立导出逐项核对。结合八个导入操作、四个分析操作、一个图查询和一个重试操作，加上 4.3.1 的 M4 操作及 4.13 的五个实验操作，工作台共 37 个已实现操作。HTTP 操作的细化规则沿用 4.5、4.6 及公共契约。

| 服务 | 方法 | 路径 | operation_id | 输入与成功响应 | 特有错误与追踪 |
| --- | --- | --- | --- | --- | --- |
| workbench | GET | `/api/v1/csrf/` | `csrf_retrieve` | 无正文；200 Csrf，设置标准 Cookie | NFR-04、AT-24 |
| workbench | GET | `/api/v1/jobs/` | `jobs_list` | page/page_size；200 JobPage | 400 参数、404 页码、503 数据库；FR-08 |
| workbench | GET | `/api/v1/jobs/{job_id}/` | `jobs_retrieve` | UUID 路径；200 Job，即使任务已 failed | 404 资源、503 数据库；FR-08 |
| workbench | POST | `/api/v1/system-checks/` | `system_checks_create` | 已退役：410 FEATURE_RETIRED，零业务写入/投递 |
| workbench | GET | `/api/v1/system-checks/{check_id}/` | `system_checks_retrieve` | UUID 路径；200 SystemCheck | 404 资源、503 数据库；FR-08 |
| task-board | GET | `/api/v1/csrf/` | `task_board_csrf_retrieve` | 无正文；200 Csrf，独立 Cookie | NFR-04、AT-24 基准 |
| task-board | GET | `/api/v1/tasks/` | `task_board_tasks_list` | page/page_size；200 TaskPage | 400 参数、404 页码、503 数据库；FR-02/03 基准 |
| task-board | POST | `/api/v1/tasks/` | `task_board_tasks_create` | 必填 title；201 Task，重放 200 | 400/409/413/415/503；FR-02/03/06/07、AT-16 基准 |

所有操作均声明 403 来源保护、406 `NOT_ACCEPTABLE`（不接受 JSON 响应）和 500 `INTERNAL_ERROR`。未知 API 路径返回 404 `RESOURCE_NOT_FOUND`；已有路径的不支持方法返回 405 `METHOD_NOT_ALLOWED`，写方法仍先通过 Origin/CSRF。HEAD/OPTIONS 属于 DRF 协议行为，不另列业务 operation_id。两服务内部可控制的错误均使用公共错误对象，`X-Request-ID` 与正文一致；所有响应 `Cache-Control: no-store`。代理返回非 JSON 或网络中断由客户端作为传输异常处理，不编造服务端机器码或请求标识。

POST 请求头为精确 Origin、标准 X-CSRFToken、UUID Idempotency-Key。基础接口正文上限 4096 字节，超过返回 413 `REQUEST_TOO_LARGE`，不同于导入限制的 `ARCHIVE_LIMIT_EXCEEDED`。列表参数默认 1/20，上限分别 2147483647/100；只接受单个 ASCII 十进制正整数，未知或重复参数拒绝；结果按 created_at、id 倒序。Schema 声明页码范围、操作键格式和示例额外字段拒绝；标题空白规范化仍由实际 Serializer 验证。

API-36 的 200/202 必带相对 Location；503 只有“持久化后投递失败”才带 Location 和 `details.job_url`，数据库未接收则没有。HTTP 请求标识与历史任务 `error.request_id` 各自指向对应事件，不能要求后续查询标识覆盖历史失败标识。同步 Task 字段与工作台 Job/SystemCheck 字段仍由各自 Serializer 及生成契约维护，不复制另一套 DTO。

本任务以 NFR-02/NFR-06 约束来源准确和可复现检查；没有据此完成 AT-05/08/09/13/14/20/25 的后续业务验收。无新增快照、引用、模型外发或实验协议；其规则继续由对应编号任务落实。

### 4.8 M2-T01 项目与导入契约

以下为本任务编码前确定的协议；对应 FR-01/04/08、NFR-01/06、AT-01/02/03/21。保留公共错误、分页、匿名来源保护和四态任务。

| 服务 | 方法 | 路径 | operation_id | 输入与成功响应 | 特有错误与追踪 |
| --- | --- | --- | --- | --- | --- |
| workbench | GET | `/api/v1/projects/` | `projects_list` | page/page_size、可选 q；200 ProjectPage，name 子串筛选后 created_at/id 倒序 | 400 参数、404 页码、503 数据库 |
| workbench | POST | `/api/v1/projects/` | `projects_create` | JSON 仅含 name，字符串去首尾空白后 1–200 字符，无控制字符；201 Project，重放 200 | 400/409/413/415/503 |
| workbench | GET | `/api/v1/projects/{project_id}/` | `projects_retrieve` | UUID；200 Project：id/name/created_at | 404 资源 |
| workbench | POST | `/api/v1/projects/{project_id}/imports/` | `imports_create` | multipart/form-data 仅一个 archive 文件；202 Job，重放 200；Location 指向任务 | 400 INVALID_ARCHIVE/VALIDATION_ERROR、413 ARCHIVE_LIMIT_EXCEEDED、409 幂等、503 存储/投递 |
| workbench | GET | `/api/v1/projects/{project_id}/snapshots/` | `snapshots_list` | page/page_size；200 SnapshotPage，仅已发布快照，created_at/id 倒序 | 404 项目/页码 |
| workbench | GET | `/api/v1/snapshots/{snapshot_id}/` | `snapshots_retrieve` | 200 Snapshot：id/name/project_id/job_id/created_at/summary/source_extensions | 404 资源 |
| workbench | PATCH | `/api/v1/snapshots/{snapshot_id}/` | `snapshots_rename` | JSON 仅必填 name；200 Snapshot；不创建任务 | 400 名称/字段、403 来源/CSRF、404 资源、415 内容类型 |
| workbench | GET | `/api/v1/snapshots/{snapshot_id}/files/` | `snapshot_files_list` | page/page_size；200 SourceFilePage，file_path/id 升序 | 404 快照/页码 |
| workbench | GET | `/api/v1/snapshots/{snapshot_id}/files/{file_id}/content/` | `snapshot_file_content_retrieve` | start_line/end_line，默认从第 1 行最多 200 行；200 SourceContent，最多 500 行 | 400 行范围、404 文件或归属、409 SNAPSHOT_NOT_READY |

Project 创建幂等范围为该动作，摘要比较规范化 name；导入范围为动作与 project_id，摘要比较 ZIP 原始字节 SHA-256（不比较上传文件名或 MIME）。同键不同摘要冲突；新键重复上传生成独立快照。所有 POST 沿用 UUID 操作键及 Origin/X-CSRFToken。拒绝重复、未知表单字段或查询参数。

Snapshot 的 `name` 是独立的可编辑展示元数据，输出始终包含该字符串；历史及新导入快照初始为 `""`，前端显示“未命名快照”与真实时间，不虚构用户名称。PATCH 仅接受字符串 name，去除首尾空白后长度为 1–200，拒绝 C0/C1 控制字符、空名称、非字符串及额外字段；必须同源并携带 X-CSRFToken，只更新 name，不改 UUID、创建时间、归属、源码、清单摘要或分析引用。重复设置相同名称自然幂等，不需要 Idempotency-Key，不自动重试；同一快照的并发命名以最后一次成功写入为准，符合本地单用户边界。导入 multipart 仍仅接受 archive。

接收流、归档中央目录和路径在接收阶段有界校验；CRC、实际展开量、文本解码在 Worker 完成。同步拒绝不创建任务；可靠接收后的失败保留 Job，error.details 只含稳定 reason，不回显归档条目或正文。kind=import，stage=queued/extracting/publishing/completed/failed，progress 暂为 null；成功 snapshot_id 与 result_url 指向新快照。投递失败与基础检查相同：503 含任务 Location，重放返回已有失败任务；不自动重试。

summary 含 entries/accepted/excluded/skipped/rejected/declared_bytes/extracted_bytes 与按原因计数的 reasons；已发布结果 rejected=0，失败不会发布摘要为成功快照。目录不计入 accepted；仅接收 .py/.js/.jsx/.ts/.tsx，其他普通文件跳过。排除规则优先；UTF-8（可有 BOM）源码统一换行为 LF 后存储，空文件按 1 行定位，不执行 Python 编码声明。SourceFile 含 id/snapshot_id/file_path/sha256/size_bytes/line_count/encoding；SourceContent 增加 start_line/end_line/content，encoding 固定 utf-8。大小、哈希和行索引均描述快照中保存的规范化文本，旧引用永不重定向到新快照。

上传资源上限见后端规范；multipart 总请求另允许 64 KiB 封装开销，必须有有效 Content-Length。危险路径、链接/特殊文件、加密、重复规范路径、大小写或 Unicode 规范冲突、文件/目录冲突均拒绝整包；首版只接受单卷普通 ZIP，压缩方法只接受 STORE/DEFLATE；ZIP64 与自解压前缀包拒绝。处理失败代码为 INVALID_ARCHIVE、ARCHIVE_LIMIT_EXCEEDED、IMPORT_STORAGE_FAILED、IMPORT_FAILED，期限失败沿用 QUEUE_TIMEOUT/EXECUTION_TIMEOUT。存储缺失、完整性标识或文件摘要不符时读取失败，不返回部分源码。

### 4.9 M2-T02 静态分析契约

M2-T02 分析接口设计：API-10 只接受 JSON `{"root_urlconf":"backend/config/urls.py"}`；路径须精确属于目标快照且为 Python 文件，不接受宿主路径、命令、规则代码或模型配置。作用域为 `analyses_create:{snapshot_id}`，摘要绑定规范化请求；同键冲突返回 409，同键重放返回 200，新任务返回 202 与任务 Location。不存在快照/文件返回 404，非法输入 400，媒体类型 415，队列故障 503 并保留任务链接。

API-11 返回 `id/job_id/snapshot_id/root_urlconf/rule_version/coverage/created_at`。API-12/14 使用标准分页，默认 20、上限 100，不支持其他过滤。接口条目保存 `method/path/path_kind/action/view/serializer/model/evidence`；符号含名称和源码引用，缺失关联为 null 并提供诊断。`path_kind` 区分 Django path 与 Router 正则，正则保留其语义，不当作运行时 URL。证据区分 `source_fact/static_inference/framework_rule`，框架依据有规则标识且不伪造源码位置。诊断含稳定代码、中文说明、严重级别及可空源码引用，不回显源码或原始异常。仅成功持久化结果可查询，未知结果为 404。

覆盖摘要记录 Python 文件总量/成功/语法失败/跳过数、接口数、诊断数、完整性标记及规则支持边界；成功可有部分诊断。无 Python、根路由语法错误、快照损坏、解析器崩溃/超时/超预算或无有效协议结果使任务失败。单个非根文件语法错误保留其余结果。该任务不实现 API-13 图或 API-17 重试。

任务 `kind=analysis`，始终绑定目标 snapshot_id；阶段为 queued/parsing/completed/failed。成功 result_url 指向 API-11，progress 为 null，不假造处理百分比。失败 `error.details.reason` 保存稳定原因，包括根路由不可解析、快照完整性、子进程失败/超时、协议和资源限制；原始异常、源码正文不进入结果或日志。

| 服务 | 方法 | 路径 | operation_id | 输入及成功响应 | 错误与验收 |
| --- | --- | --- | --- | --- | --- |
| workbench | POST | `/api/v1/snapshots/{snapshot_id}/analyses/` | `analyses_create` | root_urlconf；202 Job，重放 200；Location 指向原任务 | 400/403/404/409/413/415/503；FR-02、AT-04/05/06 |
| workbench | GET | `/api/v1/analyses/{analysis_id}/` | `analyses_retrieve` | 200 Analysis；规则版本和覆盖摘要 | 404 资源、503 数据库 |
| workbench | GET | `/api/v1/analyses/{analysis_id}/endpoints/` | `analysis_endpoints_list` | page/page_size、可选 q；200 EndpointPage，原索引及顺序不变，method/path 子串筛选后分页 | 400 参数、404 资源/页码 |
| workbench | GET | `/api/v1/analyses/{analysis_id}/diagnostics/` | `analysis_diagnostics_list` | page/page_size；200 DiagnosticPage，按文件解析和路由访问顺序 | 400 参数、404 资源/页码 |

路由和诊断按当前结果固定排序，不会因切换“最新快照”而变化。M2-T02 保存的分析文档与关联摘要不变，M2-T03 的独立图结果见 4.10。`coverage.complete` 仅表示本轮没有诊断；即使为 true，limitations 声明的静态范围仍生效。重复方法/路径保留多个条目并诊断，不任意选取。

### 4.10 M2-T03 静态关系图契约

| 服务 | 方法 | 路径 | operation_id | 输入及成功响应 | 错误与验收 |
| --- | --- | --- | --- | --- | --- |
| workbench | GET | `/api/v1/analyses/{analysis_id}/graph/` | `analysis_graph_retrieve` | 可选 root_node_id、algorithm、max_nodes、max_edges；200 Graph，有界单个表示，不分页 | 400 参数、404 分析/所属节点、409 GRAPH_NOT_AVAILABLE、500 损坏结果、503 数据库；FR-02/04、NFR-02，AT-04/05/09 后端子集 |

参数：root_node_id 是当前图的 UUID；algorithm 为 bfs/dfs，默认 bfs。max_nodes 默认 200、范围 1–1000；max_edges 默认 400、范围 1–2000，只接受单个 ASCII 十进制正整数。未知、重复、空或非法参数返回 400，不静默修正。未指定根时按接口原序号优先、其余类型/名称/ID 稳定排序遍历全部分量；指定根时只沿出边展开，不补选其他分量。邻接目标按同一稳定次序展开，DFS 使用反序入栈得到确定次序。

Graph 公共字段：analysis_id、snapshot_id、rule_version、graph_version、root_node_id（可空）、algorithm、nodes、edges、coverage、diagnostics_url、total_nodes、total_edges、returned_nodes、returned_edges、truncated、truncation_reasons。总数描述保存的完整图；返回量描述本次选择。只有预算导致遗漏才标记截断，主动指定根不算截断；原因仅 max_nodes/max_edges。边两端始终在返回节点中，保留自环和回边，边按本次节点次序及边 ID 稳定排序。coverage 仍是原解析摘要；缺失关系从 diagnostics_url 读取，不能将未截断误读为完整识别。

节点字段：id、kind（endpoint/view/serializer/model）、name、source_ref、evidence、endpoint。endpoint 节点的 endpoint 对象包含 index（原接口列表从 0 开始的固定序号）、method、path、path_kind、action、is_candidate；其他节点此字段为 null。同方法/路径/path_kind 的重复候选标记 is_candidate=true，保留独立 ID。符号按类型、名称和源码位置去重；节点 ID 由 analysis_id 命名空间和节点身份生成，不承诺不同分析间相同 ID。

边字段：id、source_id、target_id、relation、evidence；relation 为 route_view/serializer_class/meta_model。节点和边继承图的快照及版本绑定；所有源码引用另含 snapshot_id。路由包含链、注册位置和隐式动作保存在 endpoint 及 route_view 的证据；固定属性关联的边维持 static_inference，不宣称调用已执行。框架证据可 source_ref=null，源码事实不能无引用。service/ORM 调用、前端关系和人工确认不属于本次图投影。

新分析将图与分析及成功任务原子发布。图版本初始为 analysis-graph/1.0.0，独立于解析规则版本；保存预算及超限行为见后端规范 5.2。历史分析不回填、不改写：分析存在但无图返回 409 GRAPH_NOT_AVAILABLE，提示新操作键重新分析原快照；成功空图返回 200 和空数组。GET 不执行解析或提交任务。现有分析列表、结果及幂等重放行为不变；读图仍使用统一错误、no-store 和 X-Request-ID。Schema 配置固定既有证据枚举 KindEnum 的名称，新增节点 kind 不改变旧组件及客户端生成类型。

### 4.11 M2-T04 失败任务重试契约

| 工程 | 方法 | 路径 | operation_id | 请求与成功响应 | 错误与验收归属 |
| --- | --- | --- | --- | --- | --- |
| workbench | POST | `/api/v1/jobs/{job_id}/retries/` | `jobs_retry` | 新 UUID Idempotency-Key、Origin/X-CSRFToken；按原任务类型提供正文；202 Job，同键恢复 200；Location 指向新尝试 | 400 输入、403 来源、404 任务、409 状态/幂等/缺失输入、413 上传上限、415 类型、503 存储/数据库/投递；FR-08、NFR-03、AT-18/19/20 |

仅允许 failed 的 system_check、import、analysis、explanation、lab；其他状态或未实现类型返回 409 JOB_NOT_RETRYABLE。explanation 须提供绑定原预览的新 consent_id，详见 4.3.1。基础检查、分析和实验只接受必填空 JSON 对象，不允许替换快照、路由入口或指定任务类型。分析复用 AnalysisRequest 中的 snapshot_id/root_urlconf，原请求或快照入口缺失返回 409 RETRY_INPUT_UNAVAILABLE；源码物理完整性继续由 Worker 受控读取核对，损坏使新尝试失败留痕。实验保留原预测及定义副本，创建独立的新 run_id，详情见 4.13。

导入只接受 multipart/form-data 的单一 archive 文件字段，必须重传原 ZIP 的相同字节；服务端继续执行接收上限、ZIP 校验、过滤和 SHA-256 比较。不同摘要返回 409 IDEMPOTENCY_CONFLICT，即使使用新键也不能在旧任务的重试下替换输入；改变输入须使用原导入端点发起新的用户操作。原 ImportRequest 缺失返回 409 RETRY_INPUT_UNAVAILABLE。失败暂存仍按原规则清理，不长期保存未过滤的归档。重放导入重试也须携带相同 ZIP，不绕过请求验证。

幂等范围为 jobs_retry 与原 job_id，摘要绑定原请求；新键不得等于直接前一次任务的键。同键同请求只返回原重试任务，不再次投递；失败重试的再次尝试应针对该失败任务使用新键。新任务 previous_job_id 指向原任务，新导入使用独立 storage_id/快照，分析保持原快照，旧任务、错误、结果和快照不改写。首次可靠投递为 202，投递异常为 503 并返回任务 Location；若消息实际上已被领取/完成，投递异常不能回退其状态，客户端须查询任务。四态、期限和外发边界保持不变；讲解需经新的单次确认，实验只运行固定受控示例。

### 4.12 M3 前后端关联契约

M3 扩充现有操作，不增加 HTTP 端点。API-10 的正文和幂等摘要仍只有 root_urlconf；一次任务顺序执行后端、前端解析和关联，全部通过校验后原子发布。Node 协议由 `contracts/typescript-analysis.schema.json` 维护，版本为 typescript-analysis/1.0.0；前端规则为 typescript-react/1.0.0，关联规则为 method-path/1.0.0。

- API-11 增加可空 frontend 摘要：protocol_version、rule_version、association_rule_version、coverage，以及 confirmed/candidate/unmatched 请求数量。coverage 包含 source_files、parsed_files、syntax_failed_files、function_count、request_count、complete 和 limitations。历史 null 表示当时未执行前端解析，不等于请求数为零。
- API-12 增加 index（原结果内从零开始的固定序号）、frontend_available 和 frontend_links。关联摘要包括图 request_id、method、path、status、reason、source_ref；候选不会标为确认。
- API-13 增加 endpoint_index 查询（0–9999，与 root_node_id 互斥），回溯当前接口的前端上游并展开后端下游，不通过共享模型加入其他接口。原 root_node_id 出边语义、预算和截断协议保持不变。响应增加可空 endpoint_index，graph_version 返回实际保存版本。
- 图 v2 增加 frontend_function/frontend_request 节点及 direct_call、contains_function、contains_request、callback_binding、method_path_match、candidate_match 关系。函数包含、请求包含只表达源码位置；回调分派带 framework_rule。节点增加可空 request：method、original_path、path、status、reason。确认连接仍是静态推断，不是运行轨迹。无匹配请求保留为节点并带诊断。
- API-15 增加可选 kind（system_check/import/analysis）和规范 UUID snapshot_id 筛选，组合条件为 AND。重复、空、未知或非法参数返回 400；不存在快照的筛选返回空列表，不推断资源存在性。分页链接保留筛选，原无筛选查询兼容。

Analysis.frontend 使用可空 JSON 增量迁移，保存经校验的解析文档和候选列表；旧记录保持 null，不回填。读取同时支持 analysis-graph/1.0.0 和 analysis-graph/2.0.0；GET 不执行解析、创建任务或覆盖历史。协议、持久化引用或版本损坏明确失败，不用空结果替代。原 Python 覆盖字段保留其统计含义，diagnostic_count/complete 包含新增前端及关联诊断。

未知基础路径、绝对 URL 的目标归属、动态参数及重复后端候选均不自动确认。路径大小写和尾斜杠保留；查询参数值、请求头和请求体不写入解析结果。单文件语法错误可形成部分结果；Node 不可用、超时、超限、非法协议或关联预算超限使整个任务失败，沿用 ANALYSIS_FAILED 和安全 reason。实际验收及状态仅见阶段计划。

### 4.13 M5 固定实验与运行记录

固定实验 `request-validation` 版本 `1`，示例版本 `task-board/1.0.0+request-validation/1`。仅在选择 POST `/api/v1/tasks/` 且九个相关源码摘要与内置内容匹配时可运行；不匹配的项目仍可静态浏览。没有任意 URL、脚本、请求方法或用户输入正文入口。

| 服务 | 方法 | 路径 | operation_id | 输入与结果 |
| --- | --- | --- | --- | --- |
| workbench | GET | `/api/v1/labs/` | `labs_list` | 必填 analysis_id/endpoint_index；分页返回实验与 applicable/原因 |
| workbench | GET | `/api/v1/labs/{lab_id}/` | `labs_retrieve` | 同上；固定版本、四种输入，不含预填预测 |
| workbench | POST | `/api/v1/labs/{lab_id}/runs/` | `lab_runs_create` | 已退役：410 FEATURE_RETIRED，零业务写入/投递 |
| workbench | GET | `/api/v1/lab-runs/` | `lab_runs_list` | 可按 analysis_id、endpoint_index、job_id 过滤，created_at/id 倒序分页 |
| workbench | GET | `/api/v1/lab-runs/{run_id}/` | `lab_runs_retrieve` | 成功/失败/执行中均可读取已持久化预测、观测、清理状态和嵌套任务 |

`predictions` 严格包含 normal/missing/empty/whitespace，各有整数 status（100–599）和 writes（0/1）；拒绝布尔值、缺项和额外字段。版本或适用性变化返回 409 LAB_VERSION_MISMATCH/LAB_NOT_APPLICABLE；沿用公共 400/403/404/409/413/415/503 错误。投递失败保留任务和运行记录，503 附任务链接。

运行记录的 snapshot_id/analysis_id/endpoint_index 仅表示学习上下文；Job.snapshot_id 为 null。definition 保存提交时的实验内容与示例版本，predictions 原样保存。observations 逐项追加 case_id、固定 input、内部 request_path、实际 HTTP response.status/body、before_count/after_count、elapsed_ms、observed_at；未取得的后计数为 null。任务失败仍保留已知观测，不用预期填补。cleanup 为 pending/completed/unconfirmed，成功关闭须观测 closed=true 且 record_count=0；关闭观测另含 deleted_count。失败任务显式重试用空 JSON、新操作键和新 run_id，保留 previous_job_id；不自动重发。

实验专用示例配置 `config.settings.labs` 仅供内部网络的受控 Worker 使用；默认任务簿仍只有原三个操作。`labs-openapi.yaml` 独立导出以下七个操作，不生成工作台浏览器客户端：

| 服务 | 方法 | 路径 | operation_id | 说明 |
| --- | --- | --- | --- | --- |
| lab-board | GET | `/api/v1/csrf/` | `task_board_csrf_retrieve` | 原示例来源和 CSRF 保护 |
| lab-board | GET | `/api/v1/tasks/` | `task_board_tasks_list` | 原示例查询 |
| lab-board | POST | `/api/v1/tasks/` | `task_board_tasks_create` | 原示例创建与幂等 |
| lab-board | GET | `/internal/labs/runs/{run_id}/` | `lab_board_runs_retrieve` | 真实 scoped count 和关闭状态 |
| lab-board | POST | `/internal/labs/runs/{run_id}/` | `lab_board_runs_open` | 空 JSON；幂等创建固定 120 秒运行窗口，不延长旧期限 |
| lab-board | POST | `/internal/labs/runs/{run_id}/cases/{case}/` | `lab_board_cases_create` | 仅接受对应固定输入；复用原 TaskSerializer/create_task，真实 201/200/400 |
| lab-board | POST | `/internal/labs/runs/{run_id}/close/` | `lab_board_runs_close` | 空 JSON；仅删除该运行的固定键记录，保留关闭标记 |

内部 POST 同样要求 Host、Origin 和 CSRF；幂等身份由 URL 的 run_id/case 派生，调用方不能覆盖。关闭和用例写入共享运行行锁，已关闭/过期用例返回 409 LAB_RUN_CLOSED。固定地址不允许代理、重定向或用户配置。公共“所有业务 POST 要求 Idempotency-Key”针对浏览器公开契约，内部运行资源用上述固定身份保证幂等。

### 4.14 M7 人工候选决定

| 服务 | 方法 | 路径 | operation_id | 输入与结果 |
| --- | --- | --- | --- | --- |
| workbench | GET | `/api/v1/analyses/{analysis_id}/relation-reviews/` | `relation_reviews_list` | 必填 request_id；page/page_size；追加历史分页及当前 state |
| workbench | POST | `/api/v1/analyses/{analysis_id}/relation-reviews/` | `relation_reviews_create` | 已退役：410 FEATURE_RETIRED，零业务写入/投递 |

GET 仅接受上述查询键，request_id 必须是当前图中的前端请求；未处理的请求返回修订 0 和空历史，不创建数据库记录。历史按修订/ID 倒序，本页截止修订与 state 一致。POST 的 action 为 `confirm/exclude/reset`，expected_revision 为 0 至 2147483646 的整数，不接受布尔值或字符串。操作需要公共 Origin、CSRF 与 Idempotency-Key 保护；目标必须是该请求在原图中的 candidate_match，静态已确认关系不可人工改写。

同一请求最多确认一个目标，不自动排除其他候选；排除或撤销只作用于指定目标。数据库事务保存当前状态并追加历史，重新分析不迁移决定。幂等摘要包含分析及四个输入字段，重放返回原记录和读取时的当前状态；同键异参为 `409 IDEMPOTENCY_CONFLICT`，旧修订为 `409 RELATION_REVISION_CONFLICT`（details.current_revision），非候选为 `409 RELATION_NOT_CANDIDATE`。读取或提交不存在资源为 404；公共结构、内容类型、来源和存储错误沿用既有约定。

接口列表的 frontend_links 附加可空 relation_review，图读取附加 relation_reviews，决定为 `confirmed/excluded/undecided` 并携带请求、目标与修订。原静态 status、节点、边及证据保持原义；模型预览直接读取原图，不包含这些人工元数据。

### 4.15 M8 快照对比

| 服务 | 方法 | 路径 | operation_id | 输入与结果 |
| --- | --- | --- | --- | --- |
| workbench | POST | `/api/v1/projects/{project_id}/snapshot-comparisons/` | `project_snapshot_comparisons_create` | 已退役：410 FEATURE_RETIRED，零业务写入/投递 |
| workbench | GET | `/api/v1/projects/{project_id}/snapshot-comparisons/` | `project_snapshot_comparisons_list` | page/page_size；绑定、任务状态及可空摘要 |
| workbench | GET | `/api/v1/snapshot-comparisons/{comparison_id}/` | `snapshot_comparisons_retrieve` | 摘要、两侧版本、接口/关系变化和历史引用适用性 |
| workbench | GET | `/api/v1/snapshot-comparisons/{comparison_id}/files/` | `comparison_files_list` | page/page_size；按路径排序文件变化 |
| workbench | GET | `/api/v1/snapshot-comparisons/{comparison_id}/files/{change_id}/` | `comparison_files_retrieve` | 有界统一行差异、双侧位置和变更行范围 |

POST 使用公共 CSRF/Origin 和幂等键，严格 JSON 的 base_snapshot_id、target_snapshot_id 必填，base_analysis_id、target_analysis_id 必须成对给出或省略。跨项目或分析归属错误返回 409 COMPARISON_SCOPE_MISMATCH。绑定和结果归 analysis，Job.snapshot_id 为目标快照，snapshot_comparison 任务沿用公共失败、超时、显式重试和迟到结果规则。GET 只读取；未成功返回 409 COMPARISON_NOT_READY（job_url），损坏结果为 500，不存在为 404，非法查询为 400。历史包含失败/处理中请求，摘要未发布时为空。

结果版本为 snapshot-comparison/1.0.0，模式为 comparable/files_only/incomparable；两侧版本不同不输出接口或关系变化。重复接口/符号为 ambiguous，不比较跨分析 UUID。文件重命名按删除与新增。旧引用保持基准快照，只按文件 SHA 标记适用性，不验证讲解语义。输出预算和失败原因见后端规范，读取不会调用模型或改写历史。

### 4.16 M9 静态影响范围

| 服务 | 方法 | 路径 | operation_id | 输入与结果 |
| --- | --- | --- | --- | --- |
| workbench | GET | `/api/v1/analyses/{analysis_id}/impact/` | `analysis_impact_retrieve` | 必填 node_id；include_candidates、max_nodes、max_edges；范围、依据路径、修订及覆盖限制 |
| workbench | GET | `/api/v1/snapshot-comparisons/{comparison_id}/impact/` | `comparison_impact_retrieve` | 可选 change_id 选择文件变化；同上开关与预算；两侧独立结果 |

查询仅接受以上键，拒绝重复、未知和非法格式；include_candidates 仅 true/false，默认 false。预算沿用图默认 200/400、最大 1000/2000；达到上限返回 truncated 与原因。缺少 node_id 或非法预算为 400，不属于该图的节点/不属于对比的 change_id 为 404。对比未发布沿用 409 COMPARISON_NOT_READY；缺分析或原先无历史图的侧返回 available=false 与原因，已绑定图损坏为 500。GET 不创建任务、不补算图、不触发模型。

默认静态和人工确认参与；人工排除始终不参与，未决候选只在开关开启后参与。路径按依赖方向从受影响入口指向起点，path_node_ids/path_edge_ids 引用响应原图节点和边，relation_reviews 是所用边的当前决定与修订；候选路径明确 via_candidate。节点及边证据定位变更起点时也应用同一人工/候选规则。未映射变化文件、图中无引用文件、解析诊断及限制分别返回；没有结果不声明没有影响。

### 4.17 v0.3 学习与系统实验

以下为本版已实现接口；实际验收与限制只见[第三阶段计划](phase-3-plan.md)。

| 编号 | 方法 | 路径 | 职责 | 模块 | 开发任务 | 需求 | 成功模式 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| API-47 | GET | `/api/v1/knowledge-curricula/` | 已发布课程分页 | learning | M12-T01 | FR-13 | 读取 |
| API-48 | GET | `/api/v1/knowledge-curricula/{curriculum_id}/` | 指定版本先修图 | learning | M12-T01 | FR-13 | 读取 |
| API-49 | GET | `/api/v1/learning-paths/` | 指定课程/功能的目标先修路径 | learning | M12-T01 | FR-14 | 读取 |
| API-50 | GET | `/api/v1/attempt-reviews/` | 指定作答的追加自评历史 | learning | M13-T01 | FR-15 | 读取 |
| API-51 | POST | `/api/v1/attempt-reviews/` | 新增复习自评 | learning | M13-T01 | FR-15 | 同步创建 |
| API-52 | GET | `/api/v1/system-labs/` | 固定系统实验定义 | labs | M14-T01 | FR-16、FR-17 | 读取 |
| API-53 | GET | `/api/v1/system-labs/{lab_id}/` | 固定网络/子进程定义 | labs | M14-T01 | FR-16、FR-17 | 读取 |
| API-54 | POST | `/api/v1/system-labs/{lab_id}/runs/` | 保存预测并提交固定实验 | labs | M14-T01 | FR-16、FR-17 | 异步提交 |
| API-55 | GET | `/api/v1/system-lab-runs/` | 独立系统实验历史 | labs | M14-T01 | FR-16、FR-17、FR-08 | 读取 |
| API-56 | GET | `/api/v1/system-lab-runs/{run_id}/` | 原预测/真实观测/清理状态 | labs | M14-T01 | FR-16、FR-17、FR-08 | 读取 |

| 服务 | 方法 | 路径 | operation_id | 输入及结果 |
| --- | --- | --- | --- | --- |
| workbench | GET | `/api/v1/knowledge-curricula/` | `knowledge_curricula_list` | 分页，按 slug/version/id 升序 |
| workbench | GET | `/api/v1/knowledge-curricula/{curriculum_id}/` | `knowledge_curricula_retrieve` | UUID，已发布定义及摘要 |
| workbench | GET | `/api/v1/learning-paths/` | `learning_paths_retrieve` | analysis_id、endpoint_index、curriculum_id、可选 goal；版本绑定的先修闭包 |
| workbench | GET | `/api/v1/attempt-reviews/` | `attempt_reviews_list` | 必填 attempt_id，created_at/id 倒序分页 |
| workbench | POST | `/api/v1/attempt-reviews/` | `attempt_reviews_create` | 已退役：410 FEATURE_RETIRED，零业务写入/投递 |
| workbench | GET | `/api/v1/system-labs/` | `system_labs_list` | 必填 analysis_id/endpoint_index，定义分页及适用性 |
| workbench | GET | `/api/v1/system-labs/{lab_id}/` | `system_labs_retrieve` | 固定 lab_id 与工作区参数，两个预测场景 |
| workbench | POST | `/api/v1/system-labs/{lab_id}/runs/` | `system_lab_runs_create` | 已退役：410 FEATURE_RETIRED，零业务写入/投递 |
| workbench | GET | `/api/v1/system-lab-runs/` | `system_lab_runs_list` | analysis_id/endpoint_index/job_id 筛选，created_at/id 倒序分页 |
| workbench | GET | `/api/v1/system-lab-runs/{run_id}/` | `system_lab_runs_retrieve` | UUID，原定义/预测、观测、清理与 Job |

学习接口参数及字段见第三阶段计划第 4 节。learning-paths 的可选 goal 默认 create-task，必须存在于已发布课程 goals；未知/重复查询键拒绝。先修边方向 prerequisite → dependent；路径不适用时 order/steps 为空。复习是用户判断，不是正确性评分。

系统实验 definition 的两个 case_id 固定为 first/second；predictions 的两个布尔值分别预测是否连接（网络）或是否在期限内正常退出（进程）。观测逐项包含 case_id、hostname/addresses/connected、pid/return_code/stdout/timed_out/reaped、status/error_code、elapsed_ms/observed_at；不相关字段为 null 或空列表。timeout 模式的真实终止与回收属于成功观测；依赖不可用、畸形响应或清理不确认则任务失败。查询历史可按 analysis_id、endpoint_index、job_id 筛选，稳定倒序分页。新实验 Job.kind 仍为 lab，成功 result_url 为 system-lab-runs；旧 lab-runs 保留原义。所有 POST 使用现有 CSRF/Origin/幂等保护，失败通过既有 jobs 重试创建新运行。

### 4.18 M26 三条主线增量

- M26阶段契约共75操作，保留历史编号；新增目录导入/重试、源码扫描/读取、知识卡片/命中、接口关联图、删除预览/DELETE及日志列表/详情。
- Job仍为queued/running/succeeded/failed，增加source_scan/delete，source_kind、parent_job_id、result_deleted_at/result_deleted。结果删除后URL为null，仅摘要可读。
- Snapshot增加preparation_status及当前source_scan_id/scan_job_id/analysis_job_id/analysis_id。needs_root是准备状态，不是第五种Job状态；历史无准备记录返回pending而GET不补写。
- 目录multipart的manifest为JSON文件：`{"files":[{"path":"app/views.py","index":0}]}`，files按连续index提交；只接受相对路径，来源由服务端可信入口保存，不接受用户抬高限额。
- 删除预览含目标、范围、can_delete、接收状态、忙任务和confirmation_digest。DELETE接受该摘要，需Origin/CSRF/Idempotency-Key；202新任务/200重放，409忙或范围变化，410删除隔离。失败继续清理使用jobs重试新尝试，成功不能提前返回。
- OperationLog独立保存UUID与名称、结果/时间、稳定错误、任务和事件；项目、operation、result、started_after/started_before筛选，时间须含时区。前置拒绝和重放追加事件；数据库不可用等未可靠记录必须明确。
- 接口关联direction=undirected，scope明确共享符号范围；原graph方向保持。知识分页含扫描版本、coverage和diagnostics，可按scan_id/file_path或analysis_id+endpoint_index筛选。
- 预览模板1.1.0含保留片段匹配的知识版本。旧未消费确认不能提交新讲解；旧已生成结果可读。模型预算/期限现行策略不变。

| 编号 | 方法 | 路径 | 职责 | 模块 | 开发任务 | 需求 | 成功模式 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| API-63 | POST | `/api/v1/projects/{project_id}/folder-imports/` | 目录导入 | projects | M26 | FR-26 | 202新任务/200重放 |
| API-64 | POST | `/api/v1/jobs/{job_id}/folder-retries/` | 目录导入重试 | projects/jobs | M26 | FR-26 | 202新任务/200重放 |
| API-65 | POST | `/api/v1/snapshots/{snapshot_id}/source-scans/` | 显式源码扫描 | analysis | M26 | FR-26、FR-28 | 202新任务/200重放 |
| API-66 | GET | `/api/v1/source-scans/{scan_id}/` | 读取持久源码扫描 | analysis | M26 | FR-26、FR-28 | 读取 |
| API-67 | GET | `/api/v1/snapshots/{snapshot_id}/knowledge-cards/` | 扫描匹配知识卡片 | learning | M26 | FR-28 | 读取 |
| API-68 | GET | `/api/v1/snapshots/{snapshot_id}/knowledge-hits/` | 扫描知识命中 | learning | M26 | FR-28 | 读取 |
| API-69 | GET | `/api/v1/analyses/{analysis_id}/endpoint-relations/` | 共享源码接口关联图 | analysis | M26 | FR-27 | 读取 |
| API-70 | GET | `/api/v1/projects/{project_id}/deletion-preview/` | 项目删除范围预览 | jobs/projects | M26 | FR-29 | 读取 |
| API-71 | GET | `/api/v1/snapshots/{snapshot_id}/deletion-preview/` | 快照删除范围预览 | jobs/projects | M26 | FR-29 | 读取 |
| API-72 | DELETE | `/api/v1/projects/{project_id}/` | 项目内部永久清理 | jobs/projects | M26 | FR-29 | 202新任务/200重放 |
| API-73 | DELETE | `/api/v1/snapshots/{snapshot_id}/` | 快照内部永久清理 | jobs/projects | M26 | FR-29 | 202新任务/200重放 |
| API-74 | GET | `/api/v1/operation-logs/` | 操作日志筛选分页 | jobs | M26 | FR-29 | 读取 |
| API-75 | GET | `/api/v1/operation-logs/{log_id}/` | 操作日志详情与任务摘要 | jobs | M26 | FR-29 | 读取 |

| 服务 | 方法 | 路径 | operation_id | 输入与结果 |
| --- | --- | --- | --- | --- |
| workbench | POST | `/api/v1/projects/{project_id}/folder-imports/` | `folder_imports_create` | 目录导入；字段与错误以生成Schema及M26契约为准 |
| workbench | POST | `/api/v1/jobs/{job_id}/folder-retries/` | `folder_imports_retry` | 目录导入重试；字段与错误以生成Schema及M26契约为准 |
| workbench | POST | `/api/v1/snapshots/{snapshot_id}/source-scans/` | `source_scans_create` | 显式源码扫描；字段与错误以生成Schema及M26契约为准 |
| workbench | GET | `/api/v1/source-scans/{scan_id}/` | `source_scans_retrieve` | 读取持久源码扫描；字段与错误以生成Schema及M26契约为准 |
| workbench | GET | `/api/v1/snapshots/{snapshot_id}/knowledge-cards/` | `snapshot_knowledge_cards_list` | 扫描匹配知识卡片；字段与错误以生成Schema及M26契约为准 |
| workbench | GET | `/api/v1/snapshots/{snapshot_id}/knowledge-hits/` | `snapshot_knowledge_hits_list` | 扫描知识命中；字段与错误以生成Schema及M26契约为准 |
| workbench | GET | `/api/v1/analyses/{analysis_id}/endpoint-relations/` | `endpoint_relations_retrieve` | 共享源码接口关联图；字段与错误以生成Schema及M26契约为准 |
| workbench | GET | `/api/v1/projects/{project_id}/deletion-preview/` | `project_deletion_preview` | 项目删除范围预览；字段与错误以生成Schema及M26契约为准 |
| workbench | GET | `/api/v1/snapshots/{snapshot_id}/deletion-preview/` | `snapshot_deletion_preview` | 快照删除范围预览；字段与错误以生成Schema及M26契约为准 |
| workbench | DELETE | `/api/v1/projects/{project_id}/` | `projects_delete` | 项目内部永久清理；字段与错误以生成Schema及M26契约为准 |
| workbench | DELETE | `/api/v1/snapshots/{snapshot_id}/` | `snapshots_delete` | 快照内部永久清理；字段与错误以生成Schema及M26契约为准 |
| workbench | GET | `/api/v1/operation-logs/` | `operation_logs_list` | 操作日志筛选分页；字段与错误以生成Schema及M26契约为准 |
| workbench | GET | `/api/v1/operation-logs/{log_id}/` | `operation_logs_retrieve` | 操作日志详情与任务摘要；字段与错误以生成Schema及M26契约为准 |

## 5. 编码前细化和后续扩展

每个接口细化时补充：请求头及内容类型、字段/必填/范围、成功与失败示例、列表过滤和稳定排序、资源就绪条件、幂等摘要范围、快照和内容版本绑定、FR/NFR、AT 用例、`operation_id`。复用公共错误与任务格式，避免每个接口再复制整套公共规则。

接口示例必须脱敏，不能使用真实凭据、绝对宿主路径或未获允许的源码。生成产物必须来自实际实现；当前包含工作台 API-01 至 API-83 及独立示例的真实 OpenAPI 和生成类型，不为后续候选接口创建占位。命令及工作目录见[后端规范](backend-guidelines.md)、[前端规范](frontend-guidelines.md)和[结构文档](project-structure.md)。

增加端点先判断是否能在已有资源语义内表达，并更新需求、本文、对应任务和用例。移除/改变接口需要说明消费者及兼容影响；保留旧 API 编号的历史，不把旧编号重新分配给不同操作。产品升级到 v0.2 不自动改用 `/api/v2/`，也不自动引入候选功能接口。

<a id="v02-api-plan"></a>
### 5.1 v0.2 操作登记与任务追踪

本表登记 v0.2 已实现操作、职责和稳定编号，字段与错误见 4.14–4.16；均已加入实现契约核对表。所有操作归 analysis；projects 提供受控快照读取，jobs 管理执行资格，explanations 仅提供已有证据。任务与验收只见第二阶段计划，后续未实现端点仍不得生成占位契约。

| 编号 | 方法 | 路径 | operation_id | 职责与成功模式 | 任务 | 需求及验收 |
| --- | --- | --- | --- | --- | --- | --- |
| API-38 | GET | `/api/v1/analyses/{analysis_id}/relation-reviews/` | `relation_reviews_list` | 已实现；候选决定及历史、当前修订，见 4.14 | M7-T01 | FR-10；AT-29/30 |
| API-39 | POST | `/api/v1/analyses/{analysis_id}/relation-reviews/` | `relation_reviews_create` | 已实现；严格输入、追加历史、幂等及修订冲突，见 4.14 | M7-T01 | FR-10；AT-29/30 |
| API-40 | POST | `/api/v1/projects/{project_id}/snapshot-comparisons/` | `project_snapshot_comparisons_create` | 已实现；显式双侧绑定及异步提交，见 4.15 | M8-T01 | FR-11、FR-08；AT-31/34 |
| API-41 | GET | `/api/v1/projects/{project_id}/snapshot-comparisons/` | `project_snapshot_comparisons_list` | 已实现；项目对比历史和任务状态分页，见 4.15 | M8-T01 | FR-11；AT-34/37 |
| API-42 | GET | `/api/v1/snapshot-comparisons/{comparison_id}/` | `snapshot_comparisons_retrieve` | 已实现；摘要、语义变化与证据适用性，见 4.15 | M8-T01、M8-T02 | FR-11；AT-31/32/33 |
| API-43 | GET | `/api/v1/snapshot-comparisons/{comparison_id}/files/` | `comparison_files_list` | 已实现；按路径排序的文件变化分页，见 4.15 | M8-T01 | FR-11；AT-31 |
| API-44 | GET | `/api/v1/snapshot-comparisons/{comparison_id}/files/{change_id}/` | `comparison_files_retrieve` | 已实现；有界行差异和双侧引用，见 4.15 | M8-T01 | FR-11；AT-31/34 |
| API-45 | GET | `/api/v1/analyses/{analysis_id}/impact/` | `analysis_impact_retrieve` | 已实现；节点候选影响及路径，见 4.16 | M9-T01 | FR-12；AT-35/36 |
| API-46 | GET | `/api/v1/snapshot-comparisons/{comparison_id}/impact/` | `comparison_impact_retrieve` | 已实现；双侧候选影响和覆盖，见 4.16 | M9-T01 | FR-12；AT-35/36 |

人工决定最小输入为请求标识、候选目标、确认/排除/撤销动作及期望修订；原始 `confirmed/candidate/unmatched` 不改变含义。图与接口读取以附加人工元数据表达新能力，模型预览仍使用原静态图。身份必须属于目标 analysis，非候选不能借此补边；数据库并发冲突与幂等冲突分别呈现。

对比输入显式给出基准和目标 snapshot_id，均属于路径 project_id；analysis_id 两侧同时给出或同时省略，给出时必须分别属于指定快照。请求摘要包含全部绑定，不自动选择最新分析。Job 的 `snapshot_id` 为目标快照，kind 为 `snapshot_comparison`；原 API-17 以空 JSON 显式重试原对比绑定，保留旧任务及结果。四态、来源保护、POST 幂等、分页和安全错误继续使用公共协议。

影响输入限定当前图的节点或已保存对比，不接受任意源码路径/图数据；未决候选默认不纳入，人工排除始终生效。返回结果区分基准与目标，绑定各侧图及人工修订，携带依据路径、覆盖缺口和预算截断。旧图无可用前端或对比未绑定分析时明确说明缺失，GET 不触发计算任务或自动重算。

具体字段、错误、分页与预算已按实现记录在 4.14–4.16 及后端规范；机器契约以导出 OpenAPI 为准。语义与兼容边界见 [v0.2 契约约定](api-conventions.md#v02-contract)。

### 5.2 M25 搜索、通知与课程阅读进度

M25 扩展既有项目和接口列表的 q，不增加搜索端点。q 为可选、单个、不超过 200 Unicode 字符的大小写不敏感子串；空串等同未筛选，不修剪或解释为正则。项目仅匹配 name，接口仅匹配 method/path；接口先建立原始 index、前端关联和人工依据，再筛选及分页，不能重新编号。统一 count 与翻页链接描述筛选结果，链接保留 q。未知、重复参数及超长输入返回 400。

| 编号 | 方法 | 路径 | operation_id | 职责与成功模式 | 任务 | 需求及验收 |
| --- | --- | --- | --- | --- | --- | --- |
| API-58 | GET | `/api/v1/notifications/` | `notifications_list` | 派生终态任务通知，分页与未读数 | M25-T01 | M25；验证见第四阶段计划 |
| API-59 | PATCH | `/api/v1/notifications/{job_id}/` | `notifications_mark_read` | 显式标记单条已读 | M25-T01 | M25；验证见第四阶段计划 |
| API-60 | PATCH | `/api/v1/notification-read-state/` | `notification_read_state_update` | 单调推进全部已读时间水位 | M25-T01 | M25；验证见第四阶段计划 |
| API-61 | GET | `/api/v1/knowledge-curricula/{curriculum_id}/progress/` | `curriculum_progress_retrieve` | 课程精确版本卡片与阅读完成标记 | M25-T01 | M25；验证见第四阶段计划 |
| API-62 | PATCH | `/api/v1/knowledge-curricula/{curriculum_id}/progress/{card_id}/` | `curriculum_card_progress_update` | 显式更新该课程卡片的 completed | M25-T01 | M25；验证见第四阶段计划 |

| 服务 | 方法 | 路径 | operation_id | 输入与成功响应 | 特有错误与追踪 |
| --- | --- | --- | --- | --- | --- |
| workbench | GET | `/api/v1/notifications/` | `notifications_list` | page/page_size；200 NotificationPage | 400 参数、404 页码；GET 不建已读记录 |
| workbench | PATCH | `/api/v1/notifications/{job_id}/` | `notifications_mark_read` | 已退役：410 FEATURE_RETIRED，零业务写入/投递 |
| workbench | PATCH | `/api/v1/notification-read-state/` | `notification_read_state_update` | 已退役：410 FEATURE_RETIRED，零业务写入/投递 |
| workbench | GET | `/api/v1/knowledge-curricula/{curriculum_id}/progress/` | `curriculum_progress_retrieve` | 无查询参数；200 CurriculumProgress | 404 课程；409 LEARNING_CONTENT_UNAVAILABLE |
| workbench | PATCH | `/api/v1/knowledge-curricula/{curriculum_id}/progress/{card_id}/` | `curriculum_card_progress_update` | 已退役：410 FEATURE_RETIRED，零业务写入/投递 |

NotificationPage 保留 count/next/previous/results，results 为 `{job: Job, read: boolean}`，附加全量终态通知的 unread_count、服务端 as_of 及可空 read_through。仅查询 succeeded/failed，按 updated_at/id 倒序；as_of 不包含此时之后完成的任务。read 为已有单条标记或 updated_at 不晚于全局水位。单条 PATCH 返回 `{job, read:true}`；全局 PATCH 返回 `{read_through, unread_count, as_of}`。read_through 必须为带时区 ISO 8601，不能超过服务端当前时间；锁定唯一状态行后取较大值，重复或较旧请求不会重新变成未读。新完成任务不被旧水位吞掉。列表 GET 不创建任务或任何已读状态。

CurriculumProgress 为 `{curriculum_id, version, completed_count, total_count, cards}`；cards 按已发布 definition.nodes 原顺序，元素为 `{card_id, slug, version, title, completed}`，按 slug/card_version 精确关联，不能跨课程或版本共享状态。没有显式记录时 completed=false；GET 不建记录、不推断理解、不暴露答案。PATCH 可标记或取消，课程行锁和课程/卡片唯一约束保护并发，返回完整进度。缺少定义绑定版本时失败封闭，不替换为其他版本。

所有新 PATCH 沿用严格 JSON、Origin/X-CSRFToken、统一错误、no-store 和 X-Request-ID，不接受额外字段、查询参数或隐式布尔转换，不创建后台任务。它们为指定状态的自然幂等更新，不新增 Idempotency-Key；未知结果先读取核实，浏览器不自动重试写入。HTTP v1、任务状态、源码只读、模型确认及原有 57 项操作保持；新迁移仅创建 NotificationRead、NotificationReadState、CurriculumCardProgress，旧记录不回填、不改写。

### M27 参考图重构只读接口

字段与筛选、统计、导出边界见[契约规范](api-conventions.md)，保留原写入及退役规则；实际验证唯一见第四阶段计划M27。

| 编号 | 方法 | 路径 | operation_id | 职责 | 任务 |
| --- | --- | --- | --- | --- | --- |
| API-76 | GET | `/api/v1/projects/management/` | `projects_management_list` | 项目摘要、技术筛选与稳定排序 | M27 |
| API-77 | GET | `/api/v1/projects/activity/` | `projects_activity_retrieve` | 活动阶段与最近完成流程 | M27 |
| API-78 | GET | `/api/v1/snapshots/` | `snapshots_search` | 跨项目快照名称搜索 | M27 |
| API-79 | GET | `/api/v1/snapshots/{snapshot_id}/files/{file_id}/evidence/` | `snapshot_file_evidence_list` | 同快照已保存源码依据分页 | M27 |
| API-80 | GET | `/api/v1/operation-logs/statistics/` | `operation_logs_statistics` | 全查询范围日志统计 | M27 |
| API-81 | GET | `/api/v1/operation-logs/export/` | `operation_logs_export` | 完整筛选范围安全CSV | M27 |
| API-82 | GET | `/api/v1/operation-logs/{log_id}/related/` | `operation_logs_related` | 直接父子任务与重试关联 | M27 |
| API-83 | GET | `/api/v1/operation-logs/{log_id}/history/` | `operation_logs_history` | 同对象操作历史分页 | M27 |

| 服务 | 方法 | 路径 | operation_id | 输入与成功响应 |
| --- | --- | --- | --- | --- |
| workbench | GET | `/api/v1/projects/management/` | `projects_management_list` | 项目摘要、技术筛选与稳定排序；200，GET零业务写入 |
| workbench | GET | `/api/v1/projects/activity/` | `projects_activity_retrieve` | 活动阶段与最近完成流程；200，GET零业务写入 |
| workbench | GET | `/api/v1/snapshots/` | `snapshots_search` | 跨项目快照名称搜索；200，GET零业务写入 |
| workbench | GET | `/api/v1/snapshots/{snapshot_id}/files/{file_id}/evidence/` | `snapshot_file_evidence_list` | 同快照已保存源码依据分页；200，GET零业务写入 |
| workbench | GET | `/api/v1/operation-logs/statistics/` | `operation_logs_statistics` | 全查询范围日志统计；200，GET零业务写入 |
| workbench | GET | `/api/v1/operation-logs/export/` | `operation_logs_export` | 完整筛选范围安全CSV；200，GET零业务写入 |
| workbench | GET | `/api/v1/operation-logs/{log_id}/related/` | `operation_logs_related` | 直接父子任务与重试关联；200，GET零业务写入 |
| workbench | GET | `/api/v1/operation-logs/{log_id}/history/` | `operation_logs_history` | 同对象操作历史分页；200，GET零业务写入 |

## 6. 修订记录

| 版本 | 日期 | 变更 | 实现状态 |
| --- | --- | --- | --- |
| v0.2 | 2026-09-28 | 明确 API 分类、35 个首版操作、模块/任务/需求追踪和类型归属 | 仅文档；字段细化、端点与生成产物未实现 |
| v0.3 | 2026-09-29 | 按用户确认增加固定检查提交和结果读取，细化基础任务、来源保护及错误 | 5 个操作已实现；实际验收见阶段计划 |
| v0.4 | 2026-09-29 | 细化独立示例的三个操作、标题、幂等、来源和类型归属 | 与工作台端点分开；验收见阶段计划 |
| v0.5 | 2026-09-29 | 整理 M1 八个操作、公共错误与检查基线 | 两套服务独立导出；验证见阶段计划 |
| v0.6 | 2026-09-29 | 细化 API-02 至 API-09、上传/过滤/行读取和项目范围幂等 | 工作台 13 个操作；验收见阶段计划 |
| v0.7 | 2026-09-29 | 细化并实现 API-10/11/12/14、静态证据和部分诊断协议 | 工作台 17 个操作；未实现图或显式重试 |
| v0.8 | 2026-09-29 | 实现 API-13、静态图投影、遍历截断及历史无图响应 | 工作台 18 个操作；前端关联与显式重试未实现 |
| v0.9 | 2026-09-29 | 实现 API-17、重试输入、关联与恢复语义；修正当前清单遗漏 API-13 | 工作台 19 个操作；验收见阶段计划 |
| v0.10 | 2026-09-29 | 增加 M3 已实现扩展、内部协议和历史兼容字段 | 保持 19 个 HTTP 操作 |
| v0.11 | 2026-09-29 | 落实 API-18 至 API-30、单次确认、讲解重试和版本化固定作答 | 32 个工作台操作；真实模型兼容未验收 |
| v0.12 | 2026-09-29 | 登记五个实验公开操作及独立内部契约 | 验证见阶段计划；不宣布 v0.1 完成，不启动后续版本 |
| v0.13 | 2026-09-30 | 单独登记 API-38 至 API-46 的 v0.2 计划及任务追踪 | 当前仍为 37 个已实现操作，生成契约未变 |
| v0.14 | 2026-09-30 | 补记报告输出用量超限错误及不发布、未知用量边界 | HTTP路径、DTO及37个已实现操作不变；验收见首阶段计划 |
| v0.15 | 2026-09-30 | 同步无模型预算/请求期限、历史字段兼容和领取续期；旧错误仅保留历史 | 仍为37个现有操作，新策略真实兼容待验收 |
| v0.16 | 2026-09-30 | 同步当前策略选定服务/模型的真实兼容结论，保留历史失败及单次确认边界 | 仍为37个现有操作，契约与数据库结构不变；证据仅见首阶段计划 |
| v0.17 | 2026-09-30 | 登记 API-38/39、人工决定元数据、追加历史、修订及幂等语义 | 39 个工作台操作；其余规划不进入契约，验收见第二阶段计划 |
| v0.18 | 2026-10-01 | 登记 API-40 至 API-46 的实际字段、对比任务及影响语义，同步生成契约核对表 | 工作台 46 操作；验收证据见第二阶段计划 |
| v0.19 | 2026-10-01 | 同步 v0.3 学习路径、复习和固定系统实验职责及边界 | 实际状态、证据与限制仅见第三阶段计划 |
| v0.20 | 2026-10-01 | 同步 v1.0 保持 56 项操作和契约的工程验收入口 | 无新增 API 或字段，验证见第四阶段计划 |
| v0.21 | 2026-10-01 | 登记用户授权的 API-57 快照命名 PATCH、字段与校验边界 | 当前工作台 57 操作；验证唯一见第四阶段计划 |
| v0.22 | 2026-10-03 | 登记 M25 的搜索、终态通知已读水位和课程精确版本阅读进度 | 当前工作台 62 操作；实际状态与验证唯一见第四阶段计划 |

| v0.23 | 2026-10-03 | API-63–75目录/扫描/知识/关联/清理/日志，明确退役写410兼容；本轮验收唯一见M26 |
| v0.24 | 2026-10-03 | API-74/75增加display_id与日志q搜索；端点数量和UUID路径保持，验收唯一见M26 |

| v0.25 | 2026-10-04 | M27登记API-76–83，新增只读项目/快照/依据/日志查询 | 实际验证唯一见第四阶段计划M27 |
