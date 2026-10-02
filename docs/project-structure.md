# 项目解读实验室：项目结构与命名规范

| 项目 | 内容 |
| --- | --- |
| 文档版本 | v0.30 |
| 文档状态 | v0.1–v0.3 及 v1.0 稳定性/验收工程已建立；实际验收与限制见所属阶段计划 |
| 更新日期 | 2026-10-02 |
| 适用阶段 | v0.1 首版及后续按职责扩展 |
| 本文职责 | 目标目录、职责、依赖方向、命名和新增功能放置规则的权威来源 |

## 1. 阅读方式与当前状态

当前工作区包含项目文档、根目录 [AGENTS.md](../AGENTS.md)、工具基线与基础任务工程，仍未初始化 Git。已有 `backend`、`frontend` 各自的清单、锁文件、版本约束与工具配置；`backend/tooling` 保留无业务的验证样例，`backend/tests` 同时覆盖工具与配置，`frontend/tooling` 还包含本地类型生成入口。根级 `.env.example` 声明配置与安全占位，`.gitignore` 排除运行产物；实际服务配置见下文。

`scripts/prepare_toolchain.py` 在 `.runtime` 准备经校验的 Windows x64 工具及 Linux uv；`scripts/test_prepare_toolchain.py` 覆盖摘要失败、缓存与续传边界；`scripts/check-toolchain.ps1` 运行 Windows/Linux 工具检查，Linux 副本白名单包含本次必要配置、模块和前端源码。`frontend/.prettierignore` 排除前端构建和覆盖率产物。`.runtime` 保存隔离工具、缓存、下载、文档基线和脱敏验证记录，不是长期进度来源。

M1-T01 修复增加 `scripts/prepare_backend_wheels.py` 及其测试，按后端锁文件准备官方 wheel，缓存模式为每次 Windows 验收创建独立虚拟环境。`frontend/tooling` 增加 `type-patches.json`、`apply-type-patches.mjs`、`type-patches.test.mjs`、`dependency-types.test.mjs`，只承载已知第三方声明修复与回归检查。没有新增业务目录或根级依赖工程。

M1-T02 新增 `backend/manage.py`、`config/`、`common/` 与 `apps/jobs/`，包含固定检查模型、API、迁移、Worker 入口和期限核对命令；前端新增 `src/app/`、`features/jobs/`、统一 API 客户端与生成声明。根级 `compose.yaml` 组合 PostgreSQL、Redis、API、Worker、独立核对进程和 Nginx 前端；镜像与代理文件位于 `infra/docker/`、`infra/nginx/`。`scripts/check_local_stack.py` 负责本地 HTTP 与故障验收，`infra/docker/compose.verify.yaml` 仅提供验收用短期限。

`contracts/openapi.yaml` 和前端 `shared/api/generated/schema.d.ts` 包含工作台的 57 个已实现操作；生成脚本为 `frontend/tooling/generate-api-types.mjs`。启动与验证入口见 [README](../README.md)。新增 `examples/task-board` 的独立前后端、三操作 Schema、测试与 README；`testdata/analysis/task-board-create.json` 保存人工关系基准。根 Compose 按需组合示例独立 PostgreSQL/API/前端，使用独立网络、数据与凭据卷；镜像文件为 `infra/docker/task-board-*.Dockerfile`、代理为 `infra/nginx/task-board.conf.template`。`scripts/check_task_board.py` 验证真实 HTTP，`scripts/check_task_board_annotations.py` 及其测试检查引用完整性。下文未说明已有实现的部分仍为目标结构；讲解、学习和固定实验已有本地实现，当前策略的 DeepSeek/deepseek-flash 基础非流式兼容通过，具体证据与限制仅见首阶段计划，不推广至其他模型。

M1-T04 增加两服务各自的 `common/schema.py`，集中声明既有公共错误、响应头及分页参数约束；示例 `apps/tasks/api/schema.py` 补足严格 title 输入契约，工作台保留原空对象请求 Schema。两套 `test_contract.py` 覆盖无数据库协议边界，新增 `test_contract_responses.py` 使用真实 PostgreSQL 验证持久化响应。两端类型生成器增加只检查模式及 `generate-api-types.test.mjs`；示例客户端新增 `client.test.ts`，工作台扩充既有客户端测试。根 `scripts/check_contracts.py` 与 `test_check_contracts.py` 负责导出、文档清单和保存产物的一致性检查，不是业务服务或平行进度系统。

M2-T01 新增 `backend/apps/projects`：`archive.py` 负责纯归档检查/过滤，`storage.py` 负责 Linux 文件锁、暂存及原子发布，`services.py` 编排项目/导入/读取，`models.py` 保存 Project/ImportRequest/Snapshot/SourceFile；`uploads.py` 在 CSRF 解析 multipart 前约束接收，API、迁移、Worker 与测试按模块组织。`jobs` 增加动作范围唯一键与导入结果引用，保留执行资格所有权；独立核对进程通过 projects 服务清理遗留。Compose 的 `import-data` 私有命名卷供 API/Worker/核对进程共享，初始化仅设置该卷权限。该阶段仅兼容导入历史；M3 工作区实现见下文。

M2-T02 新增 `backend/apps/analysis`：`python_index.py` 索引 AST，`drf_rules.py` 处理类关系，`parser.py` 处理路由；`types.py` 为内部结果唯一类型定义，`protocol.py` 校验跨进程结果，`runner.py/worker.py` 管理可信解析进程。`models.py` 持久化提交与分析文档，`services.py/tasks.py/api/` 连接快照服务、任务和分析 HTTP 操作；迁移及测试随模块维护。`common/api.py` 从 projects 提取既有操作键/分页/数字参数公共能力，供两个模块复用，不引入业务依赖。`testdata/analysis/drf-static/` 与对应 expected JSON 为小型 Router 人工基准；既有 task-board 示例未复制或修改。

M2-T03 在同一 analysis 模块增加 `graph.py` 及内部图类型、一对一 AnalysisGraph 存储和新增迁移；服务原子发布图，API 增加 graph 查询。`tests/test_graph.py` 覆盖纯算法与证据，`tests/test_graph_api.py` 覆盖持久化、错误、隔离及历史迁移；`testdata/analysis/graph-expected.json` 是既有人工基准的后端投影预期。该阶段未创建新 app 或图数据库；前端图页面由 M3 补齐。

M2-T04 新增 `jobs/retries.py`、可空原任务关联迁移及 `test_retries.py`/`test_recovery.py`，协调已有三类任务的显式重试；业务请求仍由 projects/analysis 服务保存。重试上传复用既有上传中间件和 Nginx 有界入口，前端 jobs 仅补历史关联兼容。未创建新 app、调度服务或进度系统。

产品行为见[需求文档](requirements.md)，阶段边界见[路线图](roadmap.md)，执行范围见[阶段计划](phase-1-plan.md)，接口清单见 [API 目录](api-catalog.md)。各端实现规则分别由[后端规范](backend-guidelines.md)和[前端规范](frontend-guidelines.md)维护。

采用单仓库、后端模块化单体、前端按功能组织。项目根目录仍为 `F:\Program\Fall_Campus_Recruitment`，本次不重命名。

用户浏览器注释调整仍由现有职责承接：projects 的 `Snapshot.name` 与 `0002_snapshot_name` 管理服务端展示名称，严格输入和 PATCH 位于同一详情视图，源码存储与导入协议不变；前端 projects 的 `SnapshotNameForm`、`snapshot-name` 负责显式命名与一致显示。`GraphDiagram.css` 只负责图内工具栏、可选关系标签与单一依据区；`StaticGraphPanel` 不再组合分析摘要、诊断或图外关系列表。共享外壳移除宣传和项目横幅，独立模块和 URL 归属继续保留。实际变更及验证唯一见第四阶段计划的浏览器注释章节。

<a id="target-tree"></a>
## 2. 目标目录树

```text
项目根目录/
├── AGENTS.md                    Codex 项目约束与文档入口
├── README.md                    项目介绍、文档导航和已验证的启动方法
├── compose.yaml                 本地应用及依赖服务的组合入口
├── .gitignore                   排除秘密、运行数据、依赖和构建产物
├── .env.example                 配置名称、说明和安全占位值
├── docs/                        需求、路线、计划、规范和执行提示词
├── backend/
│   ├── manage.py                Django 管理入口
│   ├── pyproject.toml           Python 依赖与工具配置
│   ├── uv.lock                  Python 依赖锁文件
│   ├── config/                  Django 配置、总路由、ASGI/WSGI 与 Celery 入口
│   │   └── settings/            公共、本地运行和测试配置
│   ├── apps/
│   │   ├── projects/            项目导入、快照、受控源码读取
│   │   ├── analysis/            解析、关联、关系图和诊断
│   │   ├── explanations/        上下文、发送确认与模型讲解
│   │   ├── learning/            知识卡片、练习与作答记录
│   │   ├── labs/                固定实验调用与观测记录
│   │   └── jobs/                任务状态、幂等与恢复
│   ├── common/                  无业务归属的少量公共技术能力
│   └── tests/
│       └── integration/        跨模块、数据库和队列集成测试
├── frontend/
│   ├── package.json             前端依赖和脚本入口
│   ├── package-lock.json        前端依赖锁文件
│   ├── src/
│   │   ├── app/                 应用入口、路由、Provider 和主题
│   │   ├── features/            按业务功能组织的页面与交互
│   │   └── shared/
│   │       ├── api/             HTTP 客户端及公共协议处理
│   │       │   └── generated/   由 OpenAPI 生成的类型
│   │       ├── components/      跨功能通用组件
│   │       ├── hooks/           无业务归属的通用 hooks
│   │       └── lib/             按明确用途命名的纯工具模块
│   └── e2e/                     Playwright 完整流程测试
├── analyzers/
│   └── typescript/              独立 Node 静态解析程序
│       ├── src/                 CLI、语法解析和结构化输出
│       └── tests/               解析器测试
├── contracts/
│   ├── openapi.yaml             后端导出的工作台 HTTP 契约
│   └── typescript-analysis.schema.json
│                                Node 解析器输入输出协议
├── content/
│   ├── knowledge/               人工维护的知识卡片
│   ├── exercises/               题目、版本和标准答案
│   └── labs/                    固定实验教学说明与允许输入
├── examples/
│   └── task-board/              独立教学示例及其前后端
├── test/
│   ├── README.md                页面试用导入步骤与材料边界
│   ├── task-board.zip           已发布任务簿核心源码导入包
│   └── task-board/              ZIP 的 9 文件目录副本
├── testdata/
│   └── analysis/                共享解析样例、反例与预期关系
├── infra/
│   ├── docker/                  各服务镜像构建文件
│   └── nginx/                   同源入口和反向代理配置
├── scripts/                     契约生成、检查等开发辅助脚本
└── .runtime/                    明确配置的本地运行文件，禁止提交
```

树中没有展开的工具配置同样放在其所属工程内，例如 `frontend/vite.config.ts`、`frontend/tsconfig.json`。文件名由工具约定时不强制改名。

### 2.1 顶层边界

| 位置 | 允许放置的内容 | 不应放置的内容 | 首次需要的阶段 |
| --- | --- | --- | --- |
| backend | API、业务、数据库访问与 Worker 业务代码 | 另一套重复的 Worker 业务实现 | M1 |
| frontend | 工作台 UI、请求客户端和界面测试 | 服务端密钥、Python 分析或持久化逻辑 | M1 |
| analyzers/typescript | 本地 Node 程序、自己的清单及锁文件 | HTTP 服务、用户项目插件或构建执行 | M3 |
| contracts | 可机器校验的边界定义 | 业务实现、供应商凭据 | HTTP 契约 M1；解析协议 M3 |
| content | 人工审阅并版本化的教学内容 | 用户作答、运行观测或模型生成历史 | 学习内容 M4；实验说明 M5 |
| examples/task-board | 可独立运行的可信示例及自身测试 | 工作台业务或真实用户项目 | M1 |
| test | 用户要求的页面试用材料、按发布清单复制的核心源码及 ZIP | 第二套独立维护的应用、依赖、凭据或用户作答 | v1.0 试用补充 |
| testdata/analysis | 小型解析输入、反例和人工标注 | 第二份长期维护的完整示例应用 | M1 准备标注，M2/M3 扩展 |
| infra | 镜像与本地服务入口配置 | 业务规则、通用云部署平台 | M1 按需要创建 |
| scripts | 开发时的可重复辅助操作 | 常驻服务或绕过业务边界的维护后门 | 对应任务需要时 |
| .runtime | 本地暂存、临时报告等明确用途文件 | 可提交源码、长期项目知识或唯一业务持久化来源 | 实际运行时 |

后端与 Worker 共享代码，通过不同启动入口运行。Docker 持久化数据默认使用命名卷；本地路径仅在显式配置下使用。运行文件、秘密和导入源码不得进入镜像构建上下文、Git 或长期文档。

可运行示例只有 `examples/task-board` 一份源码来源。解析测试可以引用它或按确定步骤生成临时输入；专门反例放入 `testdata`，不能复制整套示例后分别修改。用户要求的 `test/task-board/` 与 ZIP 仅按 `content/exercises/task-board-create.json` 的已发布路径和摘要复制 9 份核心源码，作为页面试用导入材料；不含独立运行配置、不另行修改业务逻辑。使用与交付验证见第四阶段计划的试用测试项目补充记录。

### 2.2 依赖清单与配置

每个独立 Python/Node 工程维护自己的依赖清单和锁文件：后端使用 `pyproject.toml`/`uv.lock`，Node 工程使用 `package.json`/`package-lock.json`。示例的前后端也拥有独立清单，以验证其与工作台运行环境的分离。

首版不增加根级 monorepo 构建框架或混用 npm/pnpm/yarn 锁文件。依赖按任务引入，不因为目录树列出了某个工程就提前安装它的依赖。

`compose.yaml` 是根目录组合入口；镜像构建文件放在 `infra/docker`，如 `backend.Dockerfile`、`frontend.Dockerfile`。需要的 `.dockerignore` 放在对应构建上下文根，显式排除运行数据和秘密。`config/settings/base.py`、`local.py`、`test.py` 分别承载公共、本地和测试配置，值从受控配置入口读取。

`.env.example` 仅描述变量与安全占位，不复制真实环境文件。此文件可作为本项目配置说明；导入第三方源码时仍按后端规范排除 `.env.*`，两种场景不能混淆。

<a id="backend-layout"></a>
## 3. 后端模块结构与依赖

```text
apps/projects/
├── apps.py                      Django app 注册信息
├── models.py                    持久化模型和数据库约束
├── services.py                  跨步骤业务流程
├── tasks.py                     Celery 任务入口与业务服务连接
├── types.py                     模块内结构化输入输出
├── exceptions.py                模块领域错误
├── api/
│   ├── urls.py                  本模块 HTTP 路由
│   ├── views.py                 请求响应边界
│   └── serializers.py          输入输出校验及契约声明
├── migrations/                 Django 管理的数据库迁移
└── tests/                      模块单元测试、API 测试
```

以上为可选组成，不要求每个 app 创建所有文件。`__init__.py` 等必要 Python 包文件遵循语言与框架要求，不为了“避免空文件”破坏正常导入。

API View 调用业务服务，业务服务使用模型、解析器或适配器；Celery `tasks.py` 是另一个调用入口，不再复制业务逻辑。配置总路由负责组合各模块路由。

`common` 仅承载明确复用的 HTTP 错误、CSRF、本地访问保护等技术能力，不放项目、分析或学习规则。默认通过模块服务入口协作；跨模块模型关系与只读查询须显式设计，跨模块写入使用所属模块服务，不能任意修改内部状态。

`jobs` 管理执行资格、状态、幂等任务记录和恢复，不拥有分析、讲解或实验的业务结果。纯解析与图算法不依赖 View、Serializer 或 Django 请求对象。

当 `services.py` 需要拆分时，改为 `services/` 包并按职责组织，如 `imports.py`、`snapshots.py`；删除同名文件前核对调用方并保持必要导入兼容。禁止同时存在 `services.py` 与 `services/`，也不因行数达到固定阈值机械拆分。

<a id="frontend-layout"></a>
## 4. 前端模块结构与依赖

```text
features/projects/
├── pages/                       路由页面和业务区域组合
├── components/                  项目功能内的组件
├── hooks/                       功能查询和交互流程
├── api/                         项目资源 API 与查询键
└── types.ts                     UI 状态和生成 DTO 的明确别名
```

业务功能可对应 `projects`、`analysis`、`explanations`、`learning`、`labs`、`jobs`，按实际需求创建。数据按后端模块分组不要求前端逐文件镜像后端结构。

依赖方向为 `app → features → shared`，`app` 也可直接使用 `shared`。`shared` 不反向依赖业务功能；功能之间不得深入导入彼此内部文件，跨功能流程由应用层组合。需要复用的能力应先判断业务归属，不能把领域逻辑搬到 `shared` 以绕过依赖限制。

通用 HTTP 客户端放在 `frontend/src/shared/api/client.ts`；生成类型放在 `frontend/src/shared/api/generated/schema.d.ts`。功能 API 与查询 hooks 引用生成类型，UI 状态在 feature 内维护。`app` 负责路由、Provider 和统一主题，不能变成跨模块业务服务层。

组件与 hook 的单元测试优先同目录放置，Playwright 场景统一放在 `frontend/e2e`；后端跨模块测试与 Node 解析器测试分别由其所属工程负责。

<a id="naming"></a>
## 5. 文件、目录与标识符命名

专用语言、框架和工具规则优先于普通文件命名规则。所有文件名称应说明职责，不依赖仅大小写不同的名称区分对象。

| 对象 | 规则 | 示例 |
| --- | --- | --- |
| 普通目录、Markdown、PowerShell/Shell 脚本 | 小写 kebab-case | `task-board`、`project-structure.md`、`check-contracts.ps1` |
| Python 包、模块、脚本、函数、变量 | snake_case | `snapshot_import.py`、`create_snapshot` |
| Python 类 | PascalCase | `SnapshotImportService` |
| React 组件和页面文件 | PascalCase.tsx | `ProjectList.tsx` |
| React hook 文件与函数 | use 开头的 camelCase | `useProjectsQuery.ts` |
| 普通 TypeScript 文件 | kebab-case.ts | `projects-api.ts`、`query-keys.ts`、`parse-source.ts` |
| TypeScript 函数与变量 | camelCase | `createProject` |
| TypeScript 类型与接口 | PascalCase | `ProjectDto`、`ProjectListState` |
| 常量和错误代码 | UPPER_SNAKE_CASE | `MAX_SOURCE_FILES`、`CONSENT_STALE` |
| HTTP 资源路径 | 小写复数，复合词使用短横线 | `/lab-runs/` |
| JSON 字段 | snake_case | `snapshot_id` |
| Python 测试 | test_*.py | `test_snapshot_import.py` |
| 前端单元测试 | 与被测文件同名并增加 .test | `ProjectList.test.tsx`、`useProjectsQuery.test.ts` |
| 浏览器测试 | 场景名加 .spec.ts | `project-import.spec.ts` |
| 普通样式与组件样式 | 普通样式用 kebab-case；组件样式与组件同名 | `global.css`、`ProjectList.module.css` |
| 教学与测试数据文件 | 普通数据用描述性 kebab-case；源码仍遵循对应语言规则 | `request-validation.json`、`router_alias.py` |

教学内容版本作为明确的元数据管理；测试源码同样遵循对应语言命名规则，Python 文件统一采用 snake_case。

固定文件名如 `README.md`、`AGENTS.md`、`Dockerfile`、`pyproject.toml`、`package-lock.json`、`vite.config.ts`、Django 的 `0001_initial.py` 和生成的 `schema.d.ts` 遵循对应工具，不为满足普通规则改名。

不得新增职责不明的 `utils2`、`common-new`、`final`、`temp`。需要工具函数时采用 `path_validation.py`、`date-time.ts` 等能解释用途的名称。框架要求的缩写保持原样，新注释及实质修改的注释使用简体中文。

<a id="feature-placement"></a>
## 6. 后续功能如何新增目录

1. 在需求与路线中确认编号、所属版本、用户行为和验收标准。
2. 确定现有业务归属，优先扩展对应 app 和 feature。
3. 同一模块形成独立职责且需要多个文件时新增子目录；单个简单功能先保留单文件。
4. 只有出现独立业务概念、数据生命周期和明确协作边界时才新增 app/feature，并记录不适合现有模块的原因。
5. 同步 API 清单、类型来源、测试和目录说明；创建实际文件时才建立目录，不增加空占位树。

| 版本与能力 | 放置位置 | 约束 |
| --- | --- | --- |
| v0.2 快照差异 | `backend/apps/analysis/diffs/`；`frontend/src/features/analysis/` 内的差异展示 | 快照归属仍在 projects，不复制快照存储逻辑 |
| v0.2 人工确认关联 | 现有 analysis 服务、API 与组件 | 保留人工来源，不伪装成源码事实 |
| v0.3 知识先修路径 | `backend/apps/learning/paths/`；`frontend/src/features/learning/` | 知识图与代码图分别维护 |
| v0.3 网络与进程实验 | `content/labs/`、受控 `examples/` 实现和 labs 适配器 | 不转变为任意代码执行平台 |
| 新增框架解析 | analysis 模块内对应框架规则 | 仅在确需另一运行时且获得该功能授权后扩展 analyzers |

产品 v0.2 不对应 `backend/v0.2/` 或 `frontend/v0.2/`。文档版本、产品版本、HTTP `/api/v1/`、解析协议版本和教学内容版本各自说明兼容性，不能因产品发布自动改全部编号。

## 7. 契约、产物和检查工作目录

`contracts/openapi.yaml` 从后端生成并评审；`frontend/src/shared/api/generated/schema.d.ts` 从该契约生成。二者在开发任务中生成、校验并纳入变更，不手改；工作台当前共 57 个操作，包含 v0.1 的 37 个、v0.2 的 9 个、v0.3 的 10 个，以及用户后续明确授权的快照命名 PATCH。示例公开契约独立维护 3 个操作，实验配置契约维护 7 个操作。`contracts/typescript-analysis.schema.json` 是人工维护的内部解析协议来源，不与 HTTP OpenAPI 混用。

后端命令从 `backend` 执行；导出位置为 `../contracts/openapi.yaml`。前端命令从 `frontend` 执行，其类型生成脚本读取 `../contracts/openapi.yaml` 并写入上述生成目录。Node 解析程序从 `analyzers/typescript` 管理依赖与测试。容器工作目录和挂载必须保持对应关系，不能把相对导出路径写到临时镜像层后声称文件已交付。

示例的前后端从各自目录运行，根级 Compose 负责组合。基础应用已验证命令见 README 与对应规范；尚未创建的路径在文档中使用代码格式说明，不作为现有文件链接。

每次新增功能审查：文件是否有明确业务归属、依赖方向是否正确、生成文件是否可重现、秘密与运行数据是否隔离，以及是否出现重复样例或相同类型的第二来源。

### M3 实际组件与依赖方向

`analyzers/typescript` 是独立 Node 工程，包含 `src/cli.ts`、`src/protocol.ts`、`src/parse-source.ts` 和同工程测试；独立 npm 锁文件仅加入 TypeScript 与开发声明。它只接收标准输入源码，不提供 HTTP 服务。`contracts/typescript-analysis.schema.json` 是人工维护的协议源。

后端 analysis 内新增 `frontend_runner.py`（进程与校验）、`frontend_types.py`（内部类型）、`associations.py`（保守匹配和图扩展）；`Analysis.frontend` 由 `0003_analysis_frontend.py` 可空迁移保存。旧结果不回填，图 v1/v2 分版本读取。jobs 仅扩展历史筛选，项目存储和执行资格逻辑沿用原模块。

前端 `app/WorkspacePage.tsx` 组合 projects、analysis 和 jobs 的公共 `index.ts`；`workspace-location.ts` 管理 History API。projects 负责导入、快照和受控源码；analysis 负责分析提交、历史与关系浏览；jobs 公开任务解析、查询、重试及状态组件。features 仅通过公共出口复用任务协议，不深入其他 feature 内部。`shared/api/validation.ts` 与 `shared/hooks/useIdempotentOperation.ts` 分别负责传输校验和提交恢复。未新增路由库、图编辑器或全局状态库。

后端镜像固定包含可信 Node、已构建解析器及协议 Schema，构建白名单只扩展这些文件。`infra/docker/compose.m3-verify.yaml` 配合独立项目名 `learning-lab-m3-verify` 提供回环 5175 验收入口；`scripts/check_m3_workspace.py` 只请求该独立实例，合成归档不改教学示例。


### M4 实际模块边界

`backend/apps/explanations/` 负责配置校验、固定 HTTP 子进程、上下文/引用校验、预览、确认与讲解业务结果；`jobs` 只负责任务资格、幂等、期限核对和原子完成。`backend/apps/learning/` 负责版本化内容加载、源码摘要匹配、类型化固定答案校验与追加作答。内容文件只打包至后端，不进入前端构建。

模型用户配置仅为地址、模型和密钥；explanations 不设模型输入/响应预算或请求期限，只发送基础消息协议。模型等待由 jobs 提供领取续期，失效核对和原子完成边界保留；其他任务仍有固定执行期限。历史 ModelTarget 限额字段仅用于兼容读取，不再生成或参与新请求。

`frontend/src/features/explanations/`、`learning/` 经公共出口由工作区组合；前者复用 jobs 的公共任务协议，后者不依赖模型服务。`common/serializers.py` 是严格输入技术边界，不保存业务规则。公共 Schema 方法补充类型后，两处已有子类去掉已失效的类型忽略，不改变其输入语义。

`infra/docker/compose.m4-verify.yaml` 提供独立项目及 5176 入口；`compose.m4-double.yaml` 仅为无出口固定替身验收。真实模型使用独立密钥文件时显式叠加 `compose.model.yaml`；用户自行填写根 `.env` 时使用 `compose.model-env.yaml`，通过环境变量仅交给 Worker，API/前端不接收密钥。当前 Windows Compose 创建环境源 secret 失败，不能以配置解析成功代替运行验证；此模式的密钥存在于 Worker 容器配置中，不得输出完整配置或环境。两种配置择一使用，不叠加固定替身。`scripts/check_m4_workspace.py` 核验本地 HTTP 和历史，不能用于真实模型外发；测试替身入口位于 explanations/tests，不在正常 Worker 启动路径中。

### M5 实际模块边界

`backend/apps/labs/` 负责固定定义/适用性、运行模型、提交/重试、检查点和观测保存；`adapter.py` 校验内部响应，`transport_worker.py` 仅执行固定 HTTP 动作。jobs 复用既有资格、期限、幂等与失败重试，不导入示例的业务模块。`content/labs/request-validation.json` 是后端可信实验定义，沿用已有学习内容中的示例源码摘要。

示例新增 `apps/labs/`、`config/lab_urls.py`、`config/settings/labs.py` 与无数据库导出配置 `labs_test.py`；复用 tasks 的序列化器和写入服务，不修改原九个教学源码文件。内部 HTTP 契约位于 `examples/task-board/contracts/labs-openapi.yaml`，与三操作公开契约分离。`reconcile_lab_runs` 管理过期清理，关闭标记用于阻止迟到写入。两侧 labs 的 0001 只新增各自数据库表。

`frontend/src/features/labs/` 经公共出口由 WorkspacePage 组合，复用 jobs 公共组件及共享幂等 hook；URL run 参数恢复历史。`infra/docker/compose.m5-verify.yaml` 在独立项目提供 5177 与内部示例、清理进程；`scripts/check_m5_workspace.py` 复用既有导入/练习验证，再验证真实实验响应与历史。M5 时 `check_contracts.py` 核对工作台 37 操作、示例公开 3 操作、实验配置 7 操作，以及两套前端生成类型；当前操作数见第 7 节。未新增依赖、通用运行器、任意代码执行或新进度文件。

### v0.2 实际组件与职责归属

[第二阶段计划](phase-2-plan.md)是 M6–M10 唯一任务与验证来源；[首阶段计划](phase-1-plan.md)保留 M1–M5 历史。两份计划分工不重叠，不创建第二套项目记忆、按产品版本分叉的代码目录或占位工程。

现有规则扩展位于 `backend/apps/analysis/actions.py`、既有 DRF/parser 模块和 `analyzers/typescript/src/parse-source.ts`；规则样例、支持矩阵、旧基线及评估报告位于 `testdata/analysis/v02-*.json`。`scripts/check_analysis_rules.py` 用于有限样例评估；样例由编码代理按用户授权复核，不冒称独立人工标注。

人工决定位于 analysis/models.py、reviews.py、api/review_serializers.py、api/review_views.py 与 test_reviews.py；0004 只增加两张记录表。read_graph 服务读取不可变图，公开 API 另附决定元数据，explanations 不应用人工决定。前端 RelationReviews.tsx 与 api/review-api.ts 负责候选交互、历史及恢复输入，共享 hook 仍只处理幂等生命周期。

`analysis/diffs/` 内 files/semantics/engine 分别计算文件、语义和引用适用性；runner/worker/protocol 维持隔离计算与结果校验，services 负责双侧绑定和原子发布。0005 增加 SnapshotComparisonRequest/SnapshotComparison；HTTP 位于 api/comparison_serializers.py、api/comparison_views.py。`analysis/impact.py` 是纯反向遍历，impact_services.py 读取图与人工修订并整理覆盖，api/impact_views.py 负责输入边界；复用既有图预算。projects 继续独占快照和受控源码读取，jobs 管理新任务生命周期，explanations/evidence.py 只读原讲解证据。

前端 analysis 内的 ComparisonWorkspace.tsx、ImpactPanel.tsx 及 api/comparison-api.ts、api/impact-api.ts 提供双侧对比、路径和来源校验，由 app 组合项目/快照导航和旧讲解入口。workspace-location.ts 保存 comparison/change/candidates；不将业务状态移入 shared，也不引入另一套图编辑器或全局状态库。公共 DTO 仍由后端导出生成。

`scripts/check_v02_backend.py` 以已安装的固定镜像依赖启动随机命名的独立 PostgreSQL/Redis，--labs 提供固定实验 HTTP 服务；退出只清理自己的带标签资源。`check_v02_upgrade.py` 要求显式的隔离空库标记，构造合成旧记录并比较迁移前后摘要；拒绝用于已有实例。`check_v02_workspace.py` 要求明确的回环 origin，生成合成归档并走真实 HTTP 主线。精确命令与结果只见第二阶段计划。

新增数据库记录采用增量迁移，不重算或改写旧分析；依赖清单、锁文件、原教学源码和 v0.1 阶段历史保持不动。临时验收证据只留在忽略的 .runtime，不是新的项目记忆来源。

### v0.3 实际组件与职责归属

M11–M15 的唯一任务进度、恢复与验收来源是[第三阶段计划](phase-3-plan.md)；首两阶段计划保留历史，不创建独立记忆系统。

`learning/paths/graph.py` 为纯 DAG 校验及目标先修闭包算法，publication.py 负责内容引用和版本发布，services.py 只读取工作区与已发布版本。`content/paths/` 保存人工维护课程，`content/knowledge/learning-systems.json` 增加三张系统基础卡片；新内容由编码代理复核，不冒称独立人工审阅。`learning/reviews.py` 追加自评，services.py 校验重新作答归属。learning/0002 新增课程和复习表及可空原作答外键，保留旧记录。

`labs/system_definition.py` 校验可信定义和程序摘要，system_adapter.py 管理固定子进程和回收，system_services.py 管理持久化、任务资格与部分观测；labs/0002 新增独立 SystemLabRun。`examples/system-labs/probe.py` 仅为两项可信实验，不依赖导入源码；旧 request-validation/LabRun 不改形状。Docker 构建白名单包含 content/paths 与 examples/system-labs。

前端 learning 内 LearningPathPanel/AttemptReviewPanel 和 paths-api.ts 分别负责先修路径、自评及响应校验；labs 内 SystemLabPanel/system-labs-api.ts 负责两项实验与独立历史。app 的 URL 增加 curriculum/goal/system_run/panel，仍使用原查询、幂等和源码读取能力。新 DTO 从实际契约生成。

`check_v03_backend.py` 复用独立 PostgreSQL/Redis 检查并启用 init，`check_v03_upgrade.py` 只接受隔离空库。`check_v03_stack.py` 管理自身标签的只读源码验收环境，`check_v03_workspace.py` 验证真实 HTTP/Worker；`compose.v03-verify.yaml` 提供本版已打包镜像的独立入口。临时证据留在忽略的 .runtime，详细结果只进入第三阶段计划。

### v1.0 实际组件与职责归属

[第四阶段计划](phase-4-plan.md)维护 M16–M20 唯一状态与证据，前三阶段计划不改写。`docs/v1-demo.md` 负责架构/算法/失败/演示与资源口径，`docs/v1-trial.md` 负责真实试用协议及空白观察模板；无独立记忆系统。

`frontend/src/app/AppErrorBoundary.tsx` 只负责渲染失败的通用恢复入口，由 main.tsx 包裹 Providers/工作区。根 onCaughtError 只输出固定诊断码，不复制异常内容；异步错误和写入恢复仍归 features/shared 原有流程。测试同目录放置，未引入依赖或改变查询/任务协议。

`scripts/check_v1_release.py` 负责显式镜像构建、独立 Compose 生命周期与已有 HTTP 检查编排；`scripts/v1_acceptance.py` 负责固定合成源码、完整耗时和 cgroup 读数。对应聚焦测试位于 scripts，同一目录不另建包或通用运行平台。显式构建避免 Compose 项目标签污染镜像；容器校验同时要求实际 config-hash/container-number，拒绝接管仅继承镜像标签的容器。

`infra/docker/compose.v1-verify.yaml` 覆盖 v1.0 本地镜像、关闭模型和回环 5181，沿用原 Compose/M5 实验隔离。入口只读取自身 `.runtime/v1-verify` 空环境/状态，默认停止保留卷；删除测试卷前验证容器、网络和卷归属。该目录及 `.runtime/v1-development-20261001` 是忽略的临时证据，不是任务状态的长期来源。

依赖清单、锁文件、56 个 API、迁移、教学内容/示例版本、HTTP v1 和解析规则均保留。镜像标签 1.0.0 表示本轮作品构建，不将 Python/npm 包清单版本或旧内容/协议编号一并改写。

### M21 UI 专项组件职责

| 位置 | 职责与依赖边界 |
| --- | --- |
| `frontend/public/theme-init.js`、`index.html` | 同源首屏主题引导；不执行内联脚本、不改变 CSP |
| `frontend/src/app/ThemeProvider.tsx`、`global.css` | 偏好与 Ant Design/语义样式统一，覆盖错误恢复页 |
| `frontend/src/app/WorkspaceShell.tsx`、`workspace.css` | 顶栏、功能导航和固定可视高度外壳，使用 shared 本地 SVG |
| `frontend/src/app/WorkspaceModulePages.tsx`、`WorkspacePage.tsx`、`workspace-location.ts` | 12 个独立页面容器与 feature 公开入口组合；共享项目/快照元数据、section 和两个引用恢复、对象切换及单实例表单 |
| `frontend/src/features/projects/SourceWorkspace.tsx`、`SourceViewer.tsx`、`source-highlight.tsx` | 校验清单目录、手动固定、独立分段和只读文本着色 |
| `frontend/src/features/projects/SnapshotTimeline.tsx`、`SnapshotNameForm.tsx`、`snapshot-name.ts` | 快照名称和日期分行时间线、显式服务端命名与统一显示；UUID 仅用于资源归属 |
| `frontend/src/features/analysis/AnalysisBrowser.tsx` | API 清单、接口处理对象、前端请求来源与诊断；不挂载关系画布或候选决定 |
| `frontend/src/features/analysis/StaticGraphPanel.tsx`、`GraphDiagram.tsx`、`AnalysisEvidence.tsx` | 静态图、节点/边依据及覆盖预算说明；共享证据展示，不复制接口页 |
| `frontend/src/features/analysis/CandidateImpactPanel.tsx`、`ImpactPanel.tsx`、`RelationReviews.tsx` | 起点与影响路径、候选开关和人工决定；由专属候选影响页组合 |
| `frontend/src/features/learning/KnowledgePanel.tsx`、`LearningPathPanel.tsx` | 独立知识卡片、课程/目标与先修路径；无接口时可读全局卡片，不包含作答表单 |
| `frontend/src/features/learning/LearningPanel.tsx`、`AttemptReviewPanel.tsx` | 固定题、作答反馈/历史、重新练习与自评；由 app 与 labs 组合为练习页，不再读取知识卡片或课程 |
| `frontend/src/features/jobs/JobsPage.tsx`、`SystemStatusPage.tsx`、`SystemStatusSummary.tsx` | 历史、显式检查与检查摘要分别负责；查询和轮询随页面 active 停用，不作后台持续监控 |
| `frontend/src/shared/components/Icon.tsx` | 本地受控 SVG 图标与标识，不请求第三方资源 |

12 个页面分别承载工作台、导入、源码、API、关系图、快照与对比、候选影响、知识、练习与实验、模型讲解、系统状态、任务历史。工作台只保留准备摘要和下一步入口；`AnalysisOverview`、`KnowledgeSummary` 等既有摘要组件仍保留，但当前工作台不挂载完整图和知识区域。

功能页通过单实例 `hidden` 切换保留同一对象草稿，项目、快照、分析与接口变化时按键隔离。图节点选择保持当前模块；所属接口改变时清理旧预览、讲解、作答、实验、课程目标、panel 和 job，保留同快照源码位置。`section` 优先于旧选择；无 section 的 `panel=learning` 依据作答及课程/目标归属恢复练习或知识，独立作答/实验资源进入练习页。独立源码页在窗口宽度至少 1200px 时并排双窗口，位置仍沿用 URL 引用。

保持 `app → features → shared`；没有增加 API、依赖、迁移、运行能力或外发方式。工程状态和验证分别归属第四阶段计划 M21–M23；`.runtime/ui-redesign-20261001` 仅为忽略的原件/测试/截图证据，不是新记忆系统。[模块预览索引](previews/module-pages/index.html)保存生成设计图，与实际浏览器验收证据分别说明。

### M22 用户视角迭代职责

`projects/archive-validation.ts` 是表单与上传 API 共用的前端文件边界，实际归档解析与资源限制仍归后端。`ImportForm.test.tsx` 验证边界、移除、并发和未知恢复，不把替身响应当作真实导入。

`WorkspaceModulePages.tsx` 中的 `WorkbenchPage` 只基于 app 传入的已校验资源决定准备步骤与摘要；`WorkspacePage` 传递加载/失败状态并继续拥有 URL 和共享查询。`WorkspaceShell` 内部复用导航组件，承担窄屏原生模态菜单和品牌返回的焦点/历史行为。新增两份同目录测试分别验证首页状态与菜单交互，保留 `app → features → shared` 和原表单单实例。

本地 Git 按用户明确授权建立 main，现有工程分组留存基线，后续按功能提交；敏感配置、运行证据、IDE、依赖和构建物保持忽略。任务和实测只见[第四阶段计划 M22](phase-4-plan.md#user-review)，不建立其他项目记忆系统。

### M23 分页与系统模块职责

`shared/components/ContentPager.tsx`、`ContentPager.css` 负责同一内容树的可视页、焦点定位和尺寸观察，`content-pagination.ts` 只计算页范围；对应测试覆盖首尾、并列断点、尺寸变化与草稿。`app/pagination.css` 将原内部纵向滚动纳入页面分页，保持必要横向查看。快照命名复用共享分页，不复制表单；源码搜索展开文件入口。

jobs 公共出口新增 `SystemStatusPage`，检查提交、恢复与结果从 `JobsPage` 分离；历史保留原列表 API 和批次参数，沿 History API 保存上下文。`section=system` 与 `section=jobs` 独立，旧 `view=jobs` 继续有效。未新增后端、协议、依赖或持久化字段，任务与证据唯一见[第四阶段计划 M23](phase-4-plan.md#viewport-pagination)。

## 8. 修订记录

| 版本 | 日期 | 变更 | 实现状态 |
| --- | --- | --- | --- |
| v0.2 | 2026-09-28 | 建立目标目录、职责边界、跨栈命名规则、扩展流程和契约产物路径 | 文档已建立，目标工程目录尚未创建 |
| v0.3 | 2026-09-28 | 区分 M1-T01 实际工具文件与未来业务目录，记录隔离工具及验证入口 | 工具基线已建立，验证状态见阶段计划 |
| v0.4 | 2026-09-28 | 同步 wheel 缓存准备、独立验收环境及类型补丁工具文件 | M1-T01 工具验收通过，业务目录尚未建立 |
| v0.5 | 2026-09-29 | 记录基础应用、任务模块、服务组合、有限接口生成及验收脚本 | 实际任务状态见阶段计划；其他目标目录仍未建立 |
| v0.6 | 2026-09-29 | 记录独立示例、人工标注、隔离服务和聚焦验证入口 | 后续目标目录仍按任务创建 |
| v0.7 | 2026-09-29 | 同步 M1 公共 Schema、真实响应测试、生成漂移检查和命令归属 | 后续业务目录未建立 |
| v0.8 | 2026-09-29 | 建立 projects 模块、导入存储、受控文件读取及相关契约/测试 | 只覆盖 M2-T01；其他目标目录仍按任务创建 |
| v0.9 | 2026-09-29 | 同步 analysis 模块、公共分页及静态人工样例 | 图存储和后续业务未创建 |
| v0.10 | 2026-09-29 | 同步纯图模块、一对一图结果、API 和聚焦测试 | 只覆盖 M2-T03，前端工作区未创建 |
| v0.11 | 2026-09-29 | 同步重试协调、关联迁移、恢复测试及前端历史兼容；修正图操作计数 | 工作台 19 个操作，无新增依赖 |
| v0.12 | 2026-09-29 | 同步独立 TS 解析器、关联存储、工作区及隔离验收入口 | 仅 M3；其余目标模块仍未创建 |
| v0.13 | 2026-09-29 | 同步 M4 模块、版本化内容、工作区面板与隔离验收入口 | 验证见阶段计划，未推进 M5 |
| v0.14 | 2026-09-29 | 同步实验模块、内部契约、隔离验收配置与 HTTP 检查入口 | 验证见阶段计划；不宣布 v0.1 完成，不启动后续版本 |
| v0.15 | 2026-09-30 | 明确 v0.2 组件及阶段记录归属，修正契约操作汇总的旧计数 | 仅规划，无新增业务目录或生成产物 |
| v0.16 | 2026-09-30 | 同步用户自填 .env 的环境源 secret 启动配置，保留独立密钥文件模式 | 仅配置准备；真实启动和人工验收仍待执行 |
| v0.17 | 2026-09-30 | 按实际 Windows Compose 创建失败修正 .env 启动方式，改为仅 Worker 环境注入 | 原独立文件挂载保留，不输出容器配置或密钥 |
| v0.18 | 2026-09-30 | 同步三项模型配置、领取续期和旧预览兼容职责 | 无新业务模块、数据库或依赖变更 |
| v0.19 | 2026-09-30 | 修正当前模型兼容待验收的旧现状说明，引用首阶段计划的实际结论 | 目录、模块、契约与实现均未改变 |
| v0.20 | 2026-09-30 | 区分已有规则和评估产物与后续计划组件，保留 analysis/projects/jobs 职责 | 仅文档同步，正式验收见第二阶段计划 |
| v0.21 | 2026-09-30 | 同步人工决定表、API、前端候选组件及静态证据隔离职责 | 实际验证见第二阶段计划 |
| v0.22 | 2026-10-01 | 同步 diffs、影响算法、工作区和独立回归/升级/HTTP 检查入口；工作台 46 操作 | 模块边界、增量迁移和历史兼容均按实现记录 |
| v0.23 | 2026-10-01 | 同步 v0.3 学习路径、复习和固定系统实验职责及边界 | 实际状态、证据与限制仅见第三阶段计划 |
| v0.24 | 2026-10-01 | 同步 v1.0 恢复组件、显式构建/验收/资源脚本及演示/试用职责 | 不新增依赖、API、迁移或内容版本；验证见第四阶段计划 |
| v0.25 | 2026-10-01 | 同步 M21 主题、外壳、双源码及真实数据总览职责 | 依赖方向与既有 API 保持；验证见第四阶段计划 |
| v0.26 | 2026-10-01 | 增加用户要求的 test 导入材料及单一示例来源边界 | 核心源码按发布清单复制；验证见第四阶段计划试用补充记录 |
| v0.27 | 2026-10-01 | 同步 11 个模块页面容器、API/图/影响与知识/作答分工、单实例草稿及旧链接归属 | 不改契约、依赖或运行边界；实际模块验证唯一见第四阶段计划 |
| v0.28 | 2026-10-01 | 同步服务端快照名称与图内展示职责，当前契约 57 项 | 不改变源码存储或依赖；验证唯一见第四阶段计划 |
| v0.29 | 2026-10-02 | 同步共享导入校验、准备状态、模态导航及本地 Git 归属 | 不增加 API 或依赖；实际验证唯一见第四阶段计划 M22 |
| v0.30 | 2026-10-02 | 同步共享内容分页、12 个模块及系统检查/历史边界 | 无后端、契约或依赖变更；验证唯一见第四阶段计划 M23 |
