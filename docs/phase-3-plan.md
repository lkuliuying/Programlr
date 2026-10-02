# 项目解读实验室：第三阶段计划

| 项目 | 内容 |
| --- | --- |
| 文档版本 | v0.2 |
| 产品版本 | v0.3 学习能力增强 |
| 更新日期 | 2026-10-01 |
| 本文职责 | M11–M15 的唯一任务进度、验收证据和恢复入口 |

## 1. 授权与前置核对

用户明确授权“完成0.3版本的规划和开发”。以[路线图](roadmap.md)的五项学习增强能力为范围；不自动推进 v1.0，不追加真实模型调用，不更新已有实例或执行 Git 写操作。v0.1/v0.2 的历史结论保留在各自阶段计划，本计划不重复验收或改写。

2026-10-01 核对根 AGENTS、README、需求、结构、API 清单/规范及两端规范和实际 learning/labs/jobs 实现。目录没有 Git 元数据；非敏感工程副本与摘要保留在忽略目录 `.runtime/v03-development-20261001`，用于范围与差异审阅，不作为另一套任务状态。没有独立项目记忆文件，长期依据仍为既有项目文档。

## 2. 产品与实现边界

- 人工维护、版本化的知识先修图独立于允许环的代码依赖图。先修边方向为 prerequisite → dependent，发布前检查节点、引用、重复、自环及整体环；同版本漂移拒绝，历史保留。
- 当前功能的学习路径取指定课程目标的先修闭包，确定性拓扑排序；GET 只读取已发布内容，不入库、不调用模型。首批只映射已核对任务簿创建任务功能，其他项目明确无对应路径。
- 追加复习记录区分作答正确性、提示使用与用户自我判断；重新作答新增记录并关联同题/同版本/同工作区的原作答，不覆盖历史，不推断掌握程度或教育效果。
- 网络实验只探测 Worker 容器命名空间内 localhost:8000 与 task-board-api:8000，记录真实 DNS 地址、TCP 连接、失败类型和耗时；不接受外部地址或端口。
- 进程实验只启动固定可信 Python 文件的正常和超时两种模式，保存 PID、输出、返回码、终止与 wait 回收。Linux 子进程采用固定 CPU/地址空间/文件描述符限制；清理不确认时失败，不伪造成功。
- 新实验使用独立运行模型和既有 lab 任务协议；未知提交恢复原键，失败显式重试，Worker 失效后拒绝迟到发布。固定请求校验实验的现有 API 和观测形状保留。
- 复用现有依赖与内容加载命令，仅新增 learning/labs 增量迁移。原教学源码与示例摘要、首两阶段计划和锁文件保持不动。

## 3. 任务与退出条件

| 任务 | 实施内容 | 退出条件 | 状态 |
| --- | --- | --- | --- |
| M11-T01 | 需求 FR-13–FR-17、验收 AT-38–AT-49、接口 API-47–API-56 和本计划 | 编号及协议可追踪，无候选范围混入 | 完成 |
| M12-T01 | 纯 DAG 校验、内容发布、版本及路径读取 | 环/非法引用原子拒绝，先修顺序可验证，历史内容可读 | 完成 |
| M13-T01 | 复习模型/API、重新作答及学习界面 | 追加、幂等、同归属校验、提示与自评区分、刷新恢复 | 完成 |
| M14-T01 | 两项可信实验、任务/适配/API/界面 | 真实观测、资源限制、不可用/超时/清理失败/重复保护 | 完成 |
| M15-T01 | 综合回归、升级、HTTP/浏览器、文档和最终审阅 | 验收逐项有真实记录，未验证边界明确，差异范围一致 | 完成（参考环境范围） |

实施顺序为 M11 → M12 → M13 → M14 → M15。每项先完成聚焦测试，再进入依赖任务；检查失败不得标记通过。

## 4. 接口约定

API-47/48 为 GET knowledge-curricula 列表/详情；API-49 为 GET learning-paths，必须指定 analysis_id、endpoint_index、curriculum_id。响应绑定快照/分析/接口/课程版本，包含目标、先修闭包顺序、知识卡片与适用性，不写入路径缓存。

API-50/51 为 GET/POST attempt-reviews：列表按 attempt_id 必选筛选并按 created_at/id 倒序分页；提交包含 attempt_id、judgement（revisit/practicing/understood）及不超过 1000 字的 note，使用 Idempotency-Key，返回 201，重放 200，不同输入 409。ExerciseAttempt 增加可空 previous_attempt_id；输入可省略，不改变旧作答语义。

API-52/53 为 GET system-labs 列表/详情；API-54 为 POST system-labs/{lab_id}/runs，包含 snapshot_id、analysis_id、endpoint_index、lab_version 和 first/second 两个布尔预测，不接受任意配置。API-55/56 为 GET system-lab-runs 列表/详情。提交返回 lab Job（202/200）；结果含固定定义、预测、逐项观测、清理及嵌套任务；失败与部分观测仍可读取。使用既有来源/CSRF、错误对象、分页及任务重试约定。

## 5. 验证计划

1. DAG 的空配置、环、重复/非法边、未知节点、闭包、确定性、多目标及上限；内容版本漂移和事务回滚。
2. 复习及重新作答的合法/非法输入、跨归属、同键重放/冲突、并发、旧记录读取及前端实际交互。
3. 网络 DNS/TCP 的真实结果与不可用；进程正常/超时的真实 PID/输出/wait；适配畸形响应、终止失败、平台限制、任务失效与重复执行。
4. 独立 Linux/PostgreSQL 全量回归、迁移漂移检查、严格类型/lint/格式、契约生成校验及前端构建。
5. 隔离旧库增量升级与旧记录摘要、真实 Worker/HTTP/浏览器主线、刷新/键盘及窄窗口；结束清理仅针对验收资源。
6. 对照文件基线核对改动、受保护文件、文档链接/编号及契约一致性，记录已知限制。

## 6. 实际进度与证据

2026-10-01 完成 v0.3 五项能力及参考环境验收。不更新原有实例，不追加真实模型调用，不启动 v1.0。恢复时先核对下述记录及实际源码；不要重复开发已完成任务。

### 6.1 实现、取舍与复核

- M12：知识 DAG 独立于既有代码图，使用先修闭包与确定性堆拓扑排序。已发布课程绑定卡片/示例版本，同版本摘要漂移拒绝；读取不写数据库。新课程含 8 个知识点及 4 个目标，创建任务路径为 HTTP、React 状态、校验、序列化、ORM。
- M13：正确性、提示使用、自我判断分别保存。复习追加、并发同键去重；重新作答使用同题版本和完整工作区归属的原作答外键，省略/null 输入兼容旧摘要。浏览器真实追加自评后，原正确作答仍保留提示标记；重新练习新增错误作答且未使用提示，刷新可读原记录及关联。
- M14：旧请求校验实验与新系统实验分开持久化，复用既有 lab Job、幂等和重试。网络探测真实 DNS/TCP；固定进程真实输出、超时 SIGKILL 和 wait。Linux 父死亡信号、资源限制及 init 回收经实际进程测试验证。固定程序摘要绑定定义；清理无法确认则失败。
- M15：浏览器发现练习选择与实验任务同时存在时刷新面板歧义，增加受限 panel URL 枚举，移除与 URL 竞争的局部面板状态；回归及实际刷新/键盘/前进后退验证通过。Docker 白名单补齐课程与可信程序，构建和镜像内摘要检查通过。

手工复核观察点：在任务簿创建接口保存一次“使用了提示”的作答，再追加“自评已理解”并重新练习；原作答的提示标记不应改变，新作答应有独立提示状态及原记录关联。系统实验的预测与真实结果可以不同，进程超时观测应显示返回码 -9、实际 ready 输出和已 wait 回收。

### 6.2 实际命令与结果

以下均为已执行命令。根工作目录为 `F:\Program\Fall_Campus_Recruitment`；Python 使用 `.runtime/m1-t02-venv/Scripts/python.exe`，Node 使用 `.runtime/tools/node-v24.21.0-win-x64/node.exe`，Docker 使用 `C:/Program Files/Docker/Docker/resources/bin/docker.exe`。容器命令中的工作目录为 `/workspace/backend`。

| 工作目录 | 实际命令（省略固定可执行文件前缀） | 观察结果 |
| --- | --- | --- |
| backend | `python -B -m pytest apps/learning/tests/test_paths.py --ds=config.settings.test -q -p no:cacheprovider` | 19 项纯算法测试通过 |
| 根目录 | `python -B -X utf8 scripts/check_v03_backend.py --labs --docker <上述Docker路径> -- python -B -m pytest apps/labs/tests/test_system_adapter.py apps/labs/tests/test_system_labs.py --ds=config.settings.local -q -p no:cacheprovider --tb=short` | 13 项通过；实际 DNS/TCP、PID/输出、资源限制、父死亡回收及故障注入 |
| 根目录 | `python -B -X utf8 scripts/check_v03_backend.py --labs --docker <上述Docker路径> -- python -B -m pytest apps common tests --ds=config.settings.local -q -p no:cacheprovider --tb=short` | 完整后端 498 项通过，154.43 秒；13 条既有多线程 fork 弃用警告 |
| 根目录 | `python -B -X utf8 scripts/check_v03_backend.py --image learning-lab-backend:v03-verify --labs --docker <上述Docker路径> -- python -B -m pytest apps/labs/tests apps/learning/tests apps/jobs/tests/test_recovery.py apps/jobs/tests/test_contract.py tests/test_environment.py --ds=config.settings.local -q -p no:cacheprovider --tb=short` | 最终镜像依赖下补充回归 98 项通过，55.76 秒；与全量检查有重叠 |
| frontend | `node node_modules/vitest/vitest.mjs run` | 最终 14 文件、77 项通过，64.64 秒；面板恢复修复前为 76 项 |
| frontend | `node --test --test-concurrency=1 tooling/*.test.mjs` | 11 项工具测试通过 |
| backend | `python -B -m ruff check .`；`python -B -m ruff format --check .` | 通过；195 文件已格式化 |
| backend | `python -B -m mypy config common apps tests ../scripts/check_v02_backend.py ../scripts/check_v03_backend.py ../scripts/check_v03_stack.py ../scripts/check_v03_workspace.py ../scripts/check_v03_upgrade.py ../examples/system-labs/probe.py --platform linux --no-incremental` | 196 个源文件通过 |
| 根目录 | `python -B -m ruff check scripts/check_v02_backend.py scripts/check_v03_backend.py scripts/check_v03_stack.py scripts/check_v03_workspace.py scripts/check_v03_upgrade.py examples/system-labs/probe.py`；同文件 `ruff format --check` | 通过 |
| frontend | `node node_modules/typescript/bin/tsc --noEmit`；`node node_modules/eslint/bin/eslint.js . --max-warnings 0`；`node node_modules/prettier/bin/prettier.cjs --check .` | 最终全部通过 |
| backend | `python -B manage.py check --settings=config.settings.test`；`python -B manage.py makemigrations --settings=config.settings.test --check --dry-run` | 零检查问题；无迁移漂移 |
| 根目录 | `python -B -X utf8 scripts/check_contracts.py --node .runtime/tools/node-v24.21.0-win-x64/node.exe` | 三份 Schema、操作表及两套生成类型一致；协议测试 11/36/11 项通过，工作台 56 操作 |
| 根目录 | `python -B -X utf8 scripts/check_v03_backend.py --docker <上述Docker路径> -- env VERIFY_V03_UPGRADE=isolated-empty-database python -B /workspace/scripts/check_v03_upgrade.py` | 空库构造 v0.2 后增量升级通过，22 张旧表原列摘要一致；旧作答与实验 API 可读、课程发布成功；迁移 0.222 秒 |
| frontend | `node node_modules/vite/bin/vite.js build` | 最终通过；1562 模块，主 JS 553.69 kB / gzip 174.15 kB；保留 500 kB 构建警告 |
| 根目录 | `docker build --pull=false -f infra/docker/backend.Dockerfile -t learning-lab-backend:v03-verify .`；`docker build --pull=false -f infra/docker/frontend.Dockerfile -t learning-lab-frontend:v03-verify .` | 最终两端镜像构建通过；前端镜像同时执行 tsc 与生产构建 |
| 根目录 | `docker run --rm --pull never --init --network none --read-only --tmpfs /tmp --memory 512m --cpus 1 --pids-limit 128 --security-opt no-new-privileges:true --mount type=bind,source=F:/Program/Fall_Campus_Recruitment/.runtime/v03-development-20261001/image_smoke.py,target=/tmp/image_smoke.py,readonly learning-lab-backend:v03-verify python -B /tmp/image_smoke.py` | 镜像内课程/程序摘要、新任务 290/300 秒期限和正常/超时回收通过 |
| 根目录 | `python -B -X utf8 scripts/check_v03_stack.py start --docker <上述Docker路径>`；`python -B -X utf8 scripts/check_v03_workspace.py --origin http://127.0.0.1:5180 --evidence .runtime/v03-development-20261001/http-evidence.json` | 只读源码隔离实例的 HTTP/Worker 学习、复习、作答和两项实验主线通过；无模型调用 |
| 根目录 | `docker compose -p learning-lab-v03-verify -f compose.yaml -f infra/docker/compose.m5-verify.yaml -f infra/docker/compose.v03-verify.yaml config --quiet` | 组合语法通过，不输出实际配置 |
| 根目录 | `docker compose --env-file .runtime/v03-development-20261001/empty.env -p learning-lab-v03-package-20261001 -f compose.yaml -f infra/docker/compose.m5-verify.yaml -f infra/docker/compose.v03-verify.yaml --profile task-board up -d --no-build --pull never --wait --wait-timeout 90 api worker reconciler frontend task-board-api lab-reconciler` | 新独立项目的最终镜像、两套数据库、迁移/内容发布和服务健康检查通过 |
| 根目录 | `python -B -X utf8 scripts/check_v03_workspace.py --origin http://127.0.0.1:5180 --evidence .runtime/v03-development-20261001/package-http-evidence.json` | 已打包镜像的真实 HTTP/Worker 主线通过，无模型调用 |
| 根目录 | `python -B -X utf8 .runtime/v03-development-20261001/network_fault.py` | 核对自身 Compose 标签后断开实验网络，实际 DNS_FAILED、任务明确失败、两项观测和清理保存；finally 恢复网络，显式重试成功、旧记录不变，无模型调用 |
| 浏览器 | 独立 5180 实例实际操作与截图 | 路径、自评、重新作答、必填预测、错误预测/真实观测、刷新、Enter 切换、前进后退通过；768×900 窗口文档宽 753，无横向溢出 |

中途失败均已区分并复验：Vite 的沙箱 spawn EPERM、契约临时目录 WinError 5 和 WMI 权限问题在许可上下文通过；离线 Docker 构建缺少旧依赖缓存，既定官方源/锁文件构建通过。测试按钮可访问名称、面板双重状态、格式及测试 TypeScript 选项已修正。升级脚本初次使用不受信任 Host、镜像验收脚本模块路径、故障脚本旧版本输入和根目录 mypy 缺失项目配置分别修正验收调用后通过；未放宽生产校验、弱化断言或改变依赖。

### 6.3 验收追踪

| 验收 | 实际依据与结论 |
| --- | --- |
| AT-38/39 | test_paths.py、test_path_api.py：有效配置/目标、全图环、自环、重复/未知引用、上限及发布事务回滚通过 |
| AT-40/41 | 先修闭包/稳定顺序/不适用、同版本漂移拒绝、旧版本可读、GET 无写入；真实 HTTP 与浏览器课程路径通过 |
| AT-42/43 | test_reviews.py 与前端 LearningV03/LearningPanel：自评追加、同键/并发/冲突、同题版本及跨归属拒绝；真实旧摘要 null 重放和重新作答通过 |
| AT-44/45 | 实际 Worker 的 localhost 解析 ::1/127.0.0.1 后连接拒绝，服务名 DNS 后 TCP 成功；真实断网 DNS_FAILED 后失败/观测/清理可读。超时与畸形输入另以适配测试验证 |
| AT-46/47 | 实际正常 PID/stdout/0 返回码，超时 ready/-9/wait；Linux 资源限制、父死亡信号和 init 回收测试。终止/回收失败及不支持平台为明确注入用例，未冒称真实权限破坏 |
| AT-48 | 同键和并发提交/重复领取、投递失败、领取失效后拒绝迟到结果通过；实际断网后显式重试新建成功运行，原预测和旧记录保留 |
| AT-49 | 22 张表合成历史升级、原记录读取、最终 77 项前端回归、实际浏览器恢复、镜像启动及文档/范围核对通过 |

### 6.4 参考环境、资源与限制

- Windows x64 宿主，实测 CPU 为 13th Gen Intel Core i7-13700K（16 核/24 逻辑处理器）；Docker Desktop Linux amd64 引擎 29.4.0，固定 Python 3.13.15 / Node 24.21.0。此处只报告当前参考环境。
- 真实主线导入内置相关的 9 个源码文件，图 42 节点/49 边，无截断；HTTP 中两项实验端到端单次耗时分别为 0.464/0.684 秒。不是任意项目规模或 SLA 承诺。
- 只读源码验收 API/Worker/核对容器各限制 1 CPU、512 MiB、128 PID；cgroup v1 实测峰值分别 168.14/194.39/74.02 MiB，采样时 PID 数 5/4/3。cgroup v2 文件不可用，记录为 null 后按实际 v1 读取，未当作零资源。
- 新内容由编码代理结合已有人工基准和官方技术依据复核；未进行新的独立人工教学内容审阅或用户教育效果试验。系统实验只支持固定可信程序和当前 Linux 容器，不推广为任意代码沙箱；原生 Windows/ARM/其他框架及大项目容量未验证。
- 故障注入覆盖真实网络不可用和显式重试；任务失效/清理失败为聚焦测试，父死亡回收为真实独立进程测试。本版未对正在运行的日常 Worker 执行故障测试。
- 前端主包超过 Vite 500 kB 建议阈值，构建成功且警告保留；本版不顺带重构拆包。原运行实例未升级；启用操作见 README。

### 6.5 范围、文档与交付审阅

对照 377 个非敏感工程文件基线，39 个原文件修改、37 个工程文件新增，无删除；backend.Dockerfile 因最初枚举不含无扩展名文件，单独审阅唯一必要 COPY 新可信程序改动。86 个受保护文件摘要未变，包括依赖清单/锁文件、原教学源码、解析工程、原题/卡片/请求实验、根 Compose 及首两阶段计划。工作区没有 Git 元数据，不初始化或执行 Git 写操作。

同步 AGENTS、README、需求、路线图、结构、API 清单/规范、前后端规范及新会话入口；任务与实际证据只在本计划维护。发现旧文档中 v0.3 尚规划、当前 46 个操作及恢复入口描述与现状冲突，依据实际 Serializer/Schema/类型/测试修正为 v0.3 入口及 56 操作；历史修订与首两阶段计划保留。

临时副本、完整范围清单、差异、HTTP/故障/资源证据及截图位于忽略目录 `.runtime/v03-development-20261001`，不记录秘密、不作为并行记忆或进度来源。没有独立项目记忆文件，也未创建新的记忆系统。交付前已核对自身验收资源清理与完整改动，结果如下。

### 6.6 最终交付核对

2026-10-01 最终审阅已有文件差异及新增模块，未发现不相关实现、弱化测试、调试入口或新增秘密。实际运行 `python -B -X utf8 .runtime/v03-development-20261001/review.py` 和 `final_checks.py`；工程范围仍为修改 39、新增 37、删除 0，86 个受保护文件摘要不变。Markdown 相对文件/锚点、需求/验收/API 唯一编号、新 Python 注释及语法核对通过；完整逐文件职责见第 7 节。

最后只调整 README 实验范围、修订表排版和新增任务的中文类型说明；该任务文件 Ruff/格式/mypy 聚焦检查通过，后端镜像再次构建成功并复查镜像内课程/程序摘要和真实进程回收。未改变业务逻辑或依赖。实际浏览器截图保留在 `.runtime/v03-development-20261001/browser-v03.png`。

自身源码验收栈通过 `check_v03_stack.py stop` 关闭；打包项目先核对自身项目标签，再用原三个 Compose 文件和同一 `-p learning-lab-v03-package-20261001` 执行 `down --volumes --remove-orphans`，仅删除本次新建验收数据。随后实际查询 `learning-lab.check=v03`、`learning-lab.check=v03-browser` 和上述 Compose 项目的容器/网络，及项目数据卷，结果为空；源码栈状态为 closed=true。原日常实例及其历史卷未修改，验收镜像保留供本地启用。

已读原 AGENTS、README、首两阶段计划和相关八份核心设计文档；更新本版受影响的十份既有文档并新增本计划。通过实际 Schema/类型、源码、测试和升级证据修正当前版本/56 操作/恢复边界的旧描述，历史证据仍只在原阶段计划维护。未发现独立项目记忆源，未新建记忆系统。

## 7. 本版变更文件索引

下表仅列实际工程变更，职责逐项对应本版授权目标。运行证据和工程副本留在忽略目录，不作为工程新增文件或新记忆源。

| 文件 | 操作 | 本版职责 |
| --- | --- | --- |
| [.dockerignore](../.dockerignore) | 修改 | 将课程内容与可信实验程序纳入镜像白名单。 |
| [AGENTS.md](../AGENTS.md) | 修改 | 同步 v0.3 状态和第三阶段计划入口。 |
| [README.md](../README.md) | 修改 | 说明五项新能力、升级边界、独立启动与验收命令。 |
| [backend/apps/explanations/tests/test_contract.py](../backend/apps/explanations/tests/test_contract.py) | 修改 | 核对 56 个操作及十个新增操作标识。 |
| [backend/apps/jobs/retries.py](../backend/apps/jobs/retries.py) | 修改 | 按系统实验运行归属分派既有 lab 重试。 |
| [backend/apps/jobs/tests/test_contract.py](../backend/apps/jobs/tests/test_contract.py) | 修改 | 扩展实际 URL 契约集合断言。 |
| [backend/apps/labs/api/urls.py](../backend/apps/labs/api/urls.py) | 修改 | 注册五个系统实验操作。 |
| [backend/apps/labs/models.py](../backend/apps/labs/models.py) | 修改 | 增加独立系统实验运行记录。 |
| [backend/apps/labs/tasks.py](../backend/apps/labs/tasks.py) | 修改 | 注册固定系统实验任务。 |
| [backend/apps/learning/api/serializers.py](../backend/apps/learning/api/serializers.py) | 修改 | 增加重练关联字段，省略/null 兼容旧幂等摘要。 |
| [backend/apps/learning/api/urls.py](../backend/apps/learning/api/urls.py) | 修改 | 注册课程、路径和自评接口。 |
| [backend/apps/learning/content.py](../backend/apps/learning/content.py) | 修改 | 在既有内容事务内发布课程。 |
| [backend/apps/learning/models.py](../backend/apps/learning/models.py) | 修改 | 增加不可变课程、自评与原作答关联。 |
| [backend/apps/learning/services.py](../backend/apps/learning/services.py) | 修改 | 校验同题版本/工作区关联并新增作答。 |
| [backend/apps/learning/tests/test_learning.py](../backend/apps/learning/tests/test_learning.py) | 修改 | 同步新增三张知识卡片的实际数量。 |
| [backend/config/settings/base.py](../backend/config/settings/base.py) | 修改 | 为系统实验保留非模型任务的软/硬期限。 |
| [contracts/openapi.yaml](../contracts/openapi.yaml) | 修改 | 从实际实现导出 56 个操作及新增字段。 |
| [docs/api-catalog.md](../docs/api-catalog.md) | 修改 | 登记 API-47 至 API-56 与已实现操作表。 |
| [docs/api-conventions.md](../docs/api-conventions.md) | 修改 | 同步课程版本、追加历史及系统实验契约。 |
| [docs/backend-guidelines.md](../docs/backend-guidelines.md) | 修改 | 记录 DAG、可信程序、资源限制和清理职责。 |
| [docs/codex-task-prompt.md](../docs/codex-task-prompt.md) | 修改 | 增加第三阶段恢复范围，防止自动推进下一版。 |
| [docs/frontend-guidelines.md](../docs/frontend-guidelines.md) | 修改 | 记录路径、自评、预测、响应校验及 URL 恢复。 |
| [docs/project-structure.md](../docs/project-structure.md) | 修改 | 同步新增模块、内容、脚本和依赖方向。 |
| [docs/requirements.md](../docs/requirements.md) | 修改 | 增加 FR-13 至 FR-17、AT-38 至 AT-49。 |
| [docs/roadmap.md](../docs/roadmap.md) | 修改 | 同步本版已实现状态与验收入口。 |
| [frontend/src/app/WorkspacePage.test.tsx](../frontend/src/app/WorkspacePage.test.tsx) | 修改 | 覆盖面板显式选择、刷新和前进后退。 |
| [frontend/src/app/WorkspacePage.tsx](../frontend/src/app/WorkspacePage.tsx) | 修改 | 接入新面板/运行结果并以 URL 恢复选择。 |
| [frontend/src/app/workspace-location.ts](../frontend/src/app/workspace-location.ts) | 修改 | 校验课程、目标、系统运行和受限面板参数。 |
| [frontend/src/features/jobs/api/jobs-api.ts](../frontend/src/features/jobs/api/jobs-api.ts) | 修改 | 识别系统实验的成功结果地址。 |
| [frontend/src/features/labs/LabPanel.test.tsx](../frontend/src/features/labs/LabPanel.test.tsx) | 修改 | 补充系统实验读取依赖，保留原实验回归。 |
| [frontend/src/features/labs/LabPanel.tsx](../frontend/src/features/labs/LabPanel.tsx) | 修改 | 组合系统实验面板与独立历史。 |
| [frontend/src/features/learning/LearningPanel.test.tsx](../frontend/src/features/learning/LearningPanel.test.tsx) | 修改 | 覆盖重练重置提示并关联原作答。 |
| [frontend/src/features/learning/LearningPanel.tsx](../frontend/src/features/learning/LearningPanel.tsx) | 修改 | 组合路径、自评、历史和独立重练表单。 |
| [frontend/src/features/learning/api/learning-api.ts](../frontend/src/features/learning/api/learning-api.ts) | 修改 | 读取可空关联并兼容旧响应。 |
| [frontend/src/shared/api/generated/schema.d.ts](../frontend/src/shared/api/generated/schema.d.ts) | 修改 | 从保存的 Schema 生成实际前端类型。 |
| [frontend/src/shared/api/validation.ts](../frontend/src/shared/api/validation.ts) | 修改 | 允许复习分页的作答筛选键。 |
| [frontend/src/shared/hooks/useIdempotentOperation.ts](../frontend/src/shared/hooks/useIdempotentOperation.ts) | 修改 | 识别重练归属冲突并保留恢复协议。 |
| [scripts/check_v02_backend.py](../scripts/check_v02_backend.py) | 修改 | 提取可复用验收参数，v0.2 默认行为保持。 |
| [infra/docker/backend.Dockerfile](../infra/docker/backend.Dockerfile) | 修改 | 复制固定可信实验程序。 |
| [backend/apps/labs/api/system_serializers.py](../backend/apps/labs/api/system_serializers.py) | 新增 | 封闭校验固定预测、定义与观测字段。 |
| [backend/apps/labs/api/system_views.py](../backend/apps/labs/api/system_views.py) | 新增 | 提供系统实验提交及只读历史接口。 |
| [backend/apps/labs/migrations/0002_systemlabrun.py](../backend/apps/labs/migrations/0002_systemlabrun.py) | 新增 | 增量创建系统实验运行表。 |
| [backend/apps/labs/system_adapter.py](../backend/apps/labs/system_adapter.py) | 新增 | 固定调用可信程序，限制输出并终止/wait 回收。 |
| [backend/apps/labs/system_definition.py](../backend/apps/labs/system_definition.py) | 新增 | 校验可信定义、程序摘要和样例适用性。 |
| [backend/apps/labs/system_services.py](../backend/apps/labs/system_services.py) | 新增 | 协调幂等提交、领取检查点、观测和显式重试。 |
| [backend/apps/labs/tests/test_system_adapter.py](../backend/apps/labs/tests/test_system_adapter.py) | 新增 | 验证真实 DNS/TCP、进程限制及清理失败。 |
| [backend/apps/labs/tests/test_system_labs.py](../backend/apps/labs/tests/test_system_labs.py) | 新增 | 验证接口、并发、任务失效和历史保留。 |
| [backend/apps/learning/api/path_serializers.py](../backend/apps/learning/api/path_serializers.py) | 新增 | 校验课程查询、自评输入及只读输出。 |
| [backend/apps/learning/api/path_views.py](../backend/apps/learning/api/path_views.py) | 新增 | 提供课程、先修路径和追加自评操作。 |
| [backend/apps/learning/migrations/0002_exerciseattempt_previous_attempt_attemptreview_and_more.py](../backend/apps/learning/migrations/0002_exerciseattempt_previous_attempt_attemptreview_and_more.py) | 新增 | 增量创建课程/自评和可空重练关联。 |
| [backend/apps/learning/paths/__init__.py](../backend/apps/learning/paths/__init__.py) | 新增 | 界定学习路径模块。 |
| [backend/apps/learning/paths/graph.py](../backend/apps/learning/paths/graph.py) | 新增 | 纯函数校验完整 DAG 并计算确定性先修顺序。 |
| [backend/apps/learning/paths/publication.py](../backend/apps/learning/paths/publication.py) | 新增 | 绑定内容版本并原子发布、拒绝同版本漂移。 |
| [backend/apps/learning/paths/services.py](../backend/apps/learning/paths/services.py) | 新增 | 检查功能适用性并组装只读学习路径。 |
| [backend/apps/learning/reviews.py](../backend/apps/learning/reviews.py) | 新增 | 追加自评及笔记，校验幂等摘要和并发重复。 |
| [backend/apps/learning/tests/test_path_api.py](../backend/apps/learning/tests/test_path_api.py) | 新增 | 覆盖路径接口、版本、只读与事务回滚。 |
| [backend/apps/learning/tests/test_paths.py](../backend/apps/learning/tests/test_paths.py) | 新增 | 覆盖环、引用、上限、闭包和稳定拓扑。 |
| [backend/apps/learning/tests/test_reviews.py](../backend/apps/learning/tests/test_reviews.py) | 新增 | 覆盖自评/重练的归属、历史及并发幂等。 |
| [content/knowledge/learning-systems.json](../content/knowledge/learning-systems.json) | 新增 | 新增先修、网络和进程三张知识卡片。 |
| [content/labs/container-network.json](../content/labs/container-network.json) | 新增 | 定义 localhost 与服务名两项固定预测。 |
| [content/labs/subprocess-lifecycle.json](../content/labs/subprocess-lifecycle.json) | 新增 | 定义正常与超时进程的固定预测。 |
| [content/paths/task-board-foundations.json](../content/paths/task-board-foundations.json) | 新增 | 发布八个知识点、四个功能目标的课程。 |
| [docs/phase-3-plan.md](../docs/phase-3-plan.md) | 新增 | 维护本版唯一规划、验收、限制及变更索引。 |
| [examples/system-labs/probe.py](../examples/system-labs/probe.py) | 新增 | 实现固定可信 DNS/TCP 和 Linux 子进程探测。 |
| [frontend/src/features/labs/SystemLabPanel.test.tsx](../frontend/src/features/labs/SystemLabPanel.test.tsx) | 新增 | 验证预测必填、真实观测和归属拒绝。 |
| [frontend/src/features/labs/SystemLabPanel.tsx](../frontend/src/features/labs/SystemLabPanel.tsx) | 新增 | 展示固定实验预测、历史、失败与清理观测。 |
| [frontend/src/features/labs/api/system-labs-api.ts](../frontend/src/features/labs/api/system-labs-api.ts) | 新增 | 校验系统实验实际响应、结果归属与完整性。 |
| [frontend/src/features/learning/AttemptReviewPanel.tsx](../frontend/src/features/learning/AttemptReviewPanel.tsx) | 新增 | 追加自评/笔记并恢复未知提交原操作。 |
| [frontend/src/features/learning/LearningPathPanel.tsx](../frontend/src/features/learning/LearningPathPanel.tsx) | 新增 | 显式选择课程/目标并展示先修与卡片。 |
| [frontend/src/features/learning/LearningV03.test.tsx](../frontend/src/features/learning/LearningV03.test.tsx) | 新增 | 验证先修展示、自评提交及分页归属。 |
| [frontend/src/features/learning/api/paths-api.ts](../frontend/src/features/learning/api/paths-api.ts) | 新增 | 调用并校验课程、路径和复习响应。 |
| [infra/docker/compose.v03-verify.yaml](../infra/docker/compose.v03-verify.yaml) | 新增 | 组合独立 5180 镜像验收环境。 |
| [scripts/check_v03_backend.py](../scripts/check_v03_backend.py) | 新增 | 复用隔离后端入口并开启 init 回收。 |
| [scripts/check_v03_stack.py](../scripts/check_v03_stack.py) | 新增 | 管理仅属于自身标签的只读源码验收环境。 |
| [scripts/check_v03_upgrade.py](../scripts/check_v03_upgrade.py) | 新增 | 在独立空库验证旧历史的增量升级。 |
| [scripts/check_v03_workspace.py](../scripts/check_v03_workspace.py) | 新增 | 验证真实回环 HTTP/Worker 主线及无新增模型任务。 |
