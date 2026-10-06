# 项目解读实验室：第四阶段计划

| 项目 | 内容 |
| --- | --- |
| 文档版本 | v0.11 |
| 产品版本 | v1.0 稳定个人作品 |
| 更新日期 | 2026-10-04 |
| 本文职责 | M16–M27 及试用补充交付的唯一进度、验证证据和恢复入口 |

## 1. 授权与前置核对

用户明确授权“规划并完成1.0版本的开发”，并回答“暂无，先完成开发并准备试用材料”。按[路线图](roadmap.md)第 6 节完成稳定性、质量与资源评估、演示及试用材料；不进入候选扩展、不发送邀请、不追加真实模型调用、不更新已有实例。前三阶段的历史验收保留在各自计划。

2026-10-01 已读取根 AGENTS、README、需求、路线图、第三阶段计划、结构及相关 API/两端规范；实际目录没有 Git 元数据。没有独立项目记忆文件，既有项目文档继续承担长期依据。409 份非敏感工程副本与摘要保存在忽略目录 `.runtime/v1-development-20261001`，仅用于本次差异审阅，不是平行进度系统。未读取或复制真实 `.env`、凭据或业务数据。

## 2. 边界与验收

- 保留本地单用户、源码只读、固定可信实验、56 项 API、三项模型配置和单次外发确认。
- 页面渲染异常提供原地址重新加载及任务查询入口，不展示原始错误内容、不自动重复写入。
- 验收栈使用独立 Compose 项目、空环境文件和 127.0.0.1:5181；启动拒绝端口或资源冲突，停止前核对自身容器/网络/卷的项目标签，默认保留卷。
- 资源评估只使用无敏感的标准样例及确定性合成源码，记录重复次数、规模、运行配置、完整耗时和容器资源口径；没有可读峰值时为未知，不能写成零。
- 真实用户试用需要实际参与和记录；编码代理回归、合成任务和浏览器验收不替代真实用户或独立教学内容审阅。工程开发完成与真实试用退出条件分别记录。
- 不改变锁文件、依赖、Schema、解析支持规则、实验定义、教学内容版本或前三阶段计划。

## 3. 任务与退出条件

| 任务 | 内容 | 退出条件 | 状态 |
| --- | --- | --- | --- |
| M16-T01 | 规划、需求/验收及阶段入口 | 范围、归属、前置与试用边界明确 | 已完成 |
| M17-T01 | 页面异常恢复及独立验收生命周期 | 恢复可操作，资源冲突/归属/失败安全处理有测试 | 已完成 |
| M18-T01 | 统一 HTTP 主线及资源评估 | 真实 Worker 闭环，明确规模与测量口径，报告可读 | 已完成 |
| M19-T01 | 演示、架构与算法、失败复盘、试用材料 | 可复现步骤和观察表完整，未参与者不伪造结论 | 已完成 |
| M20-T01 | 完整回归、浏览器及最终审阅 | 测试、构建、范围与文档核对有实际证据 | 已完成 |
| M20-T02 | 小范围真实用户试用 | 授权项目、等难任务、求助/误解记录及核心问题结论 | 等待实际参与与记录 |

## 4. 验证方案

先执行新增组件/脚本聚焦测试，覆盖正常与异常渲染、资源归属拒绝、状态异常、启动失败、清理失败、资源未知及合成输入边界。再执行两端类型/lint/格式、56 项契约、后端 PostgreSQL/Redis/实验回归、前端测试和构建。

独立镜像启动后复用 v0.1–v0.3 的真实 HTTP/Worker 检查，不启用模型。当前知识卡片严格匹配发布清单，三类练习核对适用性、答案保密、正确反馈与同键重放；M5 使用 `--labs-only`，不依赖历史五卡片假设。测量 9/100/500 文件各三次导入/分析、可读内核内存峰值及明确环境。浏览器核对主线、键盘、刷新和窄窗口。结束只清理本次创建资源；差异依据基线复核。实际命令与结果仅记于下节。

## 5. 实际进度与证据

### 5.1 实际实现与验收归属

`AppErrorBoundary` 位于 app 根层；捕获渲染异常后只给通用提示和恢复入口，React 的捕获错误日志仅写固定诊断码。异步请求错误继续使用原有反馈，不自动提交任务。

`check_v1_release.py` 管理本机独立镜像、Compose 生命周期和验收编排；`v1_acceptance.py` 负责合成输入、当前教学内容检查、完整 HTTP 耗时和 cgroup 读数。没有新增后端业务、API、依赖、迁移或内容版本；源码只读和外发确认规则保留。

| 用例 | 实际证据 | 结论 |
| --- | --- | --- |
| AT-50 | 正常渲染、失败提示、秘密文本不回显、不自动重载、显式恢复和任务链接的两项组件测试 | 通过 |
| AT-51 | 状态/端口/归属/继承镜像标签/远程上下文/环境文件/启动及清理失败聚焦测试，实际隔离启动和自身清理 | 通过 |
| AT-52 | v0.2 候选/对比/影响，v0.3 路径/复习/重新练习/网络与进程，当前 8 张卡片/3 类练习，请求校验 201/400/400/400 与 1/0/0/0、历史和幂等的真实 HTTP/Worker | 通过；未启用模型 |
| AT-53 | 9/100/500 文件各三次真实导入/分析，完整计时和资源报告；cgroup v1/v2/未知值测试 | 通过，适用范围见 5.3 |
| AT-54 | 演示步骤、架构/算法/失败说明、A/B 近似难度任务和提示/顺序/误解观察空表 | 材料已完成，不代表真人试用 |
| AT-55 | 两端全量回归、契约、静态检查、构建、浏览器与最终范围审阅 | 通过 |
| AT-56 | 参与者 0，当前没有实际反馈 | 未执行；按用户决定后续开展 |

### 5.2 实际检查命令与结果

以下 `python` 使用 `.runtime/m1-t02-venv/Scripts/python.exe`（3.13.15），`node` 使用 `.runtime/tools/node-v24.21.0-win-x64/node.exe`（24.21.0）；不是要求另装全局工具。根目录为 `F:\Program\Fall_Campus_Recruitment`，backend/frontend 行在各自子目录执行。

| 工作目录 | 命令或实际检查入口 | 观察结果 |
| --- | --- | --- |
| 根目录 | `git status --short` | 没有 Git 元数据；未初始化，采用文件摘要/副本审阅 |
| 根目录 | `python -B -m pytest scripts/test_check_v1_release.py scripts/test_v1_acceptance.py -q -p no:cacheprovider --basetemp .runtime/v1-pytest-final` | 32 项通过，最后一轮 0.25 秒 |
| 根目录 | `python -B -m ruff check --config backend/pyproject.toml scripts/check_v1_release.py scripts/v1_acceptance.py scripts/test_check_v1_release.py scripts/test_v1_acceptance.py` | 通过 |
| 根目录 | 同上四文件 `python -B -m ruff format --check --config backend/pyproject.toml` | 四文件格式通过 |
| backend | `python -B -m mypy ../scripts/check_v1_release.py ../scripts/v1_acceptance.py ../scripts/test_check_v1_release.py ../scripts/test_v1_acceptance.py --platform linux --no-incremental` | 四文件严格类型通过 |
| frontend | Vitest `run`，含 `src/app/AppErrorBoundary.test.tsx` | 15 个文件、79 项通过；新增组件两项已聚焦通过 |
| frontend | `tsc --noEmit`、`eslint . --max-warnings 0`、`prettier --check .` | 类型、lint、格式均通过 |
| frontend | Node `--test --test-concurrency=1` 的 tooling 测试 | 11 项通过 |
| frontend | Vite `build` | 1563 模块构建成功；JS 554.52 kB/gzip 174.48 kB、CSS 11.45 kB/gzip 2.99 kB；保留 500 kB 警告 |
| 根目录 | `python -B -X utf8 scripts/check_contracts.py --node .runtime/tools/node-v24.21.0-win-x64/node.exe` | 两侧 Schema、56 项操作、生成类型及 11/36/11 项契约检查通过 |
| 根目录 | `python -B -X utf8 scripts/check_v03_backend.py --image learning-lab-backend:1.0.0 --labs --docker 'C:/Program Files/Docker/Docker/resources/bin/docker.exe' -- python -B -m pytest apps common tests --ds=config.settings.local -q -p no:cacheprovider --tb=short` | 隔离 PostgreSQL/Redis/固定实验：498 项通过，152.13 秒，13 条原有多线程 fork 弃用警告 |
| backend | `python -B manage.py check --settings=config.settings.test`；`python -B manage.py makemigrations --check --dry-run --settings=config.settings.test` | 系统检查无问题；没有待生成迁移 |
| 根目录 | `python -B -X utf8 scripts/check_v1_release.py start --build --docker 'C:/Program Files/Docker/Docker/resources/bin/docker.exe'` | 三个镜像显式构建，独立 5181 栈就绪；未加载真实配置 |
| 根目录 | `python -B -X utf8 scripts/check_v1_release.py check --docker 'C:/Program Files/Docker/Docker/resources/bin/docker.exe'` | 综合 HTTP 主线 12.616 秒，资源评估通过，报告 status=passed |
| 浏览器 | In-app 浏览器，真实 5181 工作区 | 源码/学习/实验可读，Enter 打开 TaskSerializer 8–30 行；刷新恢复行号与已保存进程结果；768×900 时内容宽 753，无横向溢出；错误日志 0 |
| 根目录 | `python -B -X utf8 scripts/check_v1_release.py stop --remove-test-data --docker 'C:/Program Files/Docker/Docker/resources/bin/docker.exe'`，随后按项目标签只读核对 | 本次容器/网络/卷均为 0，state=stopped；原 5177 日常栈仍运行 |
| 根目录 | `python -B -X utf8 .runtime/v1-development-20261001/review_v1.py` | 409 份基线中 12 份修改、397 份不变，10 个必要新增文件，无删除、范围外修改或断开的本地文档文件链接 |

运行期间的环境与实现失败均如实区分：Windows 沙箱 `spawn EPERM`/`WinError 5` 在许可上下文复验通过。根目录缺少 Django 插件模块路径导致 mypy 插件初始化错误，改在既有 backend 工作目录、沿用项目配置后通过；新增测试格式修正后通过，不改变检查标准。

首次 Compose 构建使独立回归容器继承镜像项目标签，服务选择出现歧义。已改为显式 Docker 构建，并增加实际容器归属校验和负向测试；没有删除身份不明容器。首次统一检查遇到历史 M4 五张卡片断言，未修改旧检查或削弱断言；改为当前内容清单严格校验，再复用 M5 实验部分。失败报告写明阶段和异常位置，不复制原始异常内容；最终重新运行综合主线通过。

### 5.3 资源观测与解释

本轮报告：`.runtime/v1-verify/report.json`，北京时间 2026-10-01 10:06:14 完成。Windows AMD64，24 个逻辑 CPU；Docker Linux x86_64、24 CPU、可用内存 16,623,607,808 字节、Engine 29.4.0。API/Worker/核对进程分别限制 1 CPU、512 MiB、128 PID；镜像摘要和实际读数见报告。

| 规模 | 源码字节 / 行 | ZIP 字节 | 导入中位秒（最小–最大） | 分析中位秒（最小–最大） |
| --- | --- | --- | --- | --- |
| 标准 9 文件 | 22,863 / 711 | 10,199 | 0.2399（0.2386–0.2584） | 0.6788（0.6761–0.6951） |
| 合成 100 文件 | 29,041 / 893 | 28,571 | 0.2435（0.2418–0.2498） | 0.6743（0.6740–0.6853） |
| 合成 500 文件 | 56,632 / 1,693 | 109,762 | 0.8865（0.8830–0.8992） | 0.8863（0.8831–0.8941） |

每档三个暖缓存、单用户串行样本；耗时含 HTTP 提交、排队、真实执行、读取及 0.2 秒轮询误差。合成新增的是独立小模块，不代表复杂真实项目或最大容量。各档当前静态图 42 节点/49 边、未截断，但覆盖 complete=false 及诊断仍按实际返回保留，不宣称运行轨迹完整。

本环境读到 cgroup v1 生命周期内核内存峰值：API 190,287,872 字节（约 181.5 MiB）、Worker 240,734,208 字节（约 229.6 MiB）、核对进程 71,213,056 字节（约 67.9 MiB）。各峰值包含本次容器启动和该栈验收，发生时刻不同，不能相加冒称同时总峰值。其他环境 v2 或不可读值按实测报告，未知为 null。模型调用 0，用量/费用 null，未做本轮计费评估。

浏览器观察与截图保存在 `.runtime/v1-development-20261001/browser-v1.json`、`browser-v1.jpg`；实际正常/超时 PID 166/167、返回码 0/-9、输出 ready/completed 与 ready，均 wait 回收。工程记录不能替代独立人工审阅或真实用户反馈。

### 5.4 最终范围及文档一致性

实际复核 12 个修改文件的完整差异和 10 个新增工程文件；409 份原始非敏感基线中 397 份保持摘要一致，无删除、依赖/锁文件/生成契约/迁移/内容/示例改动，前三阶段计划也保持原文件。新增或实质修改的注释及文档字符串为简体中文，没有调试后门、原始秘密、根目录临时文件或意外工程产物。验证副本、测试缓存、报告及截图都在既有忽略目录 `.runtime`，未建立并行记忆或进度来源。

范围检查最初把无后缀的旧隐藏工具配置误列为新增；只读核对其写入时间均早于本轮基线，按原副本白名单匹配后通过，未删除或修改这些配置。本地文档文件链接均可解析；原始根目录无 Git 元数据，未初始化或执行 Git 写操作。

已读长期依据为 AGENTS、README、需求、路线图、前三阶段计划、结构、API 清单/契约、两端规范和任务提示词。同步根入口、需求与 AT-50–56、结构与恢复组件/独立验收职责、原契约边界、演示/试用材料及本计划唯一状态。发现 README ZIP 上限写成 25 MiB，与 `backend/apps/projects/types.py` 的 ImportLimits 和 `archive.py` 校验的 20 MiB 不符，核对后改为 20 MiB；旧模型“尚未复验”描述与首阶段已有真实验收记录矛盾，查证后校正，未追加真实调用。API 契约与后端规范的适用阶段头部遗漏已实现 v0.3，也依据当前模块和 56 项契约核对校正至当前阶段。

本轮 M16-T01 至 M20-T01、AT-50 至 AT-55 在上述参考环境和有限样例范围内完成。M20-T02/AT-56 按用户决定等待真实参与，不计为工程未实现或已通过真人试用；后续执行需要真实记录和相应授权，不自动开始候选功能。

## 6. 风险与未验证范围

真实用户试用、其他模型/架构/框架、新宿主冷启动下载和任意项目容量未验证。当前工程工作不代表普遍教育效果、计费或性能承诺。模型保持关闭，既有真实兼容结论仅见首阶段计划。Vite 包大小警告和原有 fork 弃用警告已保留，未为去除警告改依赖、解析方式或拆包。

本轮不新增数据库迁移；此前版本的增量升级结论仅见第二/第三阶段计划，不能称作本轮新的已有实例升级。独立演示已关闭，复现时按演示文档重新启动；没有把原 5177 实例更新至 v1.0。

<a id="ui-redesign"></a>
## 7. M21：参考图工作台与双主题专项

### 7.1 授权、范围和恢复

2026-10-01 用户明确要求实施已确认计划：所有现有前端页面统一重排；深色默认且记住手动选择；第二源码窗口手动固定；尽量还原参考图并适配窗口。路线边界见总体路线图 6.3。仅改变前端展示及 URL 选择，不新增后端 API、依赖、迁移、任意代码运行或模型调用。M16–M20 的历史与真人试用待进行状态保留。

相关非敏感前端/文档原件与 SHA-256 基线位于忽略目录 `.runtime/ui-redesign-20261001`，用于差异审阅，不是独立项目记忆。没有 Git 元数据，未初始化 Git；未读取环境或凭据。既有前端 ZIP 25 MiB 与后端 20 MiB 不一致作为范围外发现保留，不顺带改变导入规则。

### 7.2 任务及退出条件

| 任务 | 内容 | 退出条件 | 状态 |
| --- | --- | --- | --- |
| M21-T01 | 路线与 UI 需求、基线 | 范围及唯一验证归属明确，原件可比较 | 已完成 |
| M21-T02 | 语义主题、首屏引导与偏好 | 双模式、存储异常、CSP 和恢复页可用 | 已完成 |
| M21-T03 | 外壳、文件树、双源码及 URL | 响应式布局、独立分段和旧链接兼容 | 已完成 |
| M21-T04 | 关系/影响/快照/学习与任务呈现 | 真实数据、限制和单实例表单保留 | 已完成 |
| M21-T05 | 回归、浏览器与文档核对 | AT-57–63 有实际证据，无无关变更 | 已完成；参考环境与未验证项见下节 |

### 7.3 验证方案

聚焦验证主题持久化/非法值/存储异常，文件树筛选与双窗口分段，跨快照拒绝、旧地址和前进/后退，图预览与候选/截断，主题切换不清空输入或重复提交。运行既有 typecheck、lint、format:check、前端完整测试、api:types:check 和 build；复用独立 5181 验收入口且关闭模型，不更新 5177 日常实例。两种主题分别检查 1672×941、1920×1080、1440×900、1280×800、768×900、390×844，保存同一数据状态截图，核对键盘/焦点/弹层/长内容/加载/失败/空状态/减少动画。

### 7.4 实际记录

#### 7.4.1 实现与验收对应

`ThemeProvider` 统一 CSS 语义变量和 Ant Design；同源外部 `theme-init.js` 在 React 前读取合法主题偏好，不放宽 CSP。`WorkspaceShell` 提供统一导航、当前快照搜索、主题及任务入口；原有业务表单各自保留一个实例，导航切换只隐藏对应区域。切换项目、快照或接口仍按归属重置上下文。

`SourceWorkspace` 从已接收文件生成可折叠目录，手动固定第二文件；两窗使用同一 `SourceViewer` 的身份/摘要/行号校验，各自最多读取 200 行。`section` 与 `file2/start2/end2` 使用 History API，旧参数继续恢复。源码着色仅为行内词法展示，使用 React 文本节点，不执行或转换为 HTML。

关系和影响总览按现有结构化结果分组及 SVG 连线，最多展示 12 个节点和 24 条边；文字列表与画布来自同一组边。完整关系沿用原查询预算。快照、卡片版本和模型标签均取真实数据；基础检查仅展示已加载任务范围内的显式检查和实际完成时间，不宣称实时监控。

| 验收 | 实际证据 | 结论 |
| --- | --- | --- |
| AT-57 | 三项主题测试覆盖默认/非法值/读写失败/切换与偏好恢复；打包页首屏外部脚本及 CSP；浏览器浅色刷新恢复 | 通过 |
| AT-58 | 三项文件树/双源码/着色测试，原三项 SourceViewer 边界/身份/摘要测试；实际固定、关闭、路径筛选及手机源码页签 | 通过 |
| AT-59 | 三项 URL 测试及入口迟到响应/上下文/旧记录回归；实际双引用刷新、关闭后退、无效引用前进/后退 | 通过 |
| AT-60 | 两项图测试覆盖预算、选中节点、人工确认/排除、画布与文字边一致及空图；既有候选/未匹配/截断入口测试 | 通过，不声称静态覆盖完整 |
| AT-61 | 双主题六档截图、页面宽度、手机 Enter/Escape/焦点和 Ctrl+K、路径过滤；浏览器 CSSOM 核对减少动画规则 | 布局及操作通过；未切换操作系统动画偏好 |
| AT-62 | 主题测试确认未重建表单且未提交；实际答案 8–14 行经主题、源码/学习和任务导航后保留；外发/确认原测试保留 | 通过；本轮模型调用 0 |
| AT-63 | 最终构建资产与同源页面逐字节一致；真实 HTTP/Worker 回归、显式基础检查、自身资源清理及日常镜像摘要核对 | 通过；未更新 5177 |

#### 7.4.2 实际命令与结果

工作目录和固定 Python/Node 路径沿用 5.2。下列 `npm` 由固定 Node 执行 `frontend` 的 `../.runtime/tools/node-v24.21.0-win-x64/node_modules/npm/bin/npm-cli.js`，子进程 PATH 指向同一工具目录；没有安装或升级依赖。

| 工作目录 | 实际检查入口 | 观察结果 |
| --- | --- | --- |
| frontend | `npm run typecheck` | 通过 |
| frontend | `npm run lint` | 通过，最大警告 0 |
| frontend | `npm run format:check` | 通过 |
| frontend | `npm run test -- --run` | 19 个文件、91 项通过，87.82 秒；原有测试保留，新增 12 项 |
| frontend | Vitest 聚焦 `WorkspacePage.test.tsx`、`SourceWorkspace.test.tsx`、`SourceViewer.test.tsx` | 最终焦点/展示调整后 3 个文件、14 项通过，25.10 秒 |
| frontend | `npm run api:types:check` | 通过，生成契约保持原件 |
| frontend | `npm run build` | 1573 模块成功；JS 587.16 kB/gzip 184.36 kB，CSS 27.09 kB/gzip 6.26 kB；保留 500 kB 警告 |
| 根目录 | `python -B -X utf8 scripts/check_v1_release.py start --build --docker 'C:/Program Files/Docker/Docker/resources/bin/docker.exe'` | 独立 5181 栈就绪，模型关闭；后续仅在该栈重建前端以核对最终样式 |
| 根目录 | `python -B -X utf8 scripts/check_v1_release.py check --repeats 1 --docker 'C:/Program Files/Docker/Docker/resources/bin/docker.exe'` | 报告 passed；v0.2/v0.3/M5 真实 HTTP 与 Worker 主线 13.228 秒，9/100/500 文件每档一次回归；不替代历史三次资源评估 |
| 根目录 | 固定 Python `urllib.request` 读取 5181 HTML、响应头及所引用资产 | 同源、外部主题脚本、无内联脚本、原 CSP 和最终 dist 内容一致；记录于 `csp.json` |
| 浏览器 | In-app 浏览器的双主题六档截图及实际操作 | 页面均无横向溢出；正常期间控制台错误 0；详见 7.4.3 |
| 根目录 | `python -B -X utf8 scripts/check_v1_release.py stop --remove-test-data --docker 'C:/Program Files/Docker/Docker/resources/bin/docker.exe'` 及只读归属核对 | 自身容器/网络/卷均 0，状态 stopped；5177 容器标识及实际镜像摘要不变且仍运行 |
| 根目录 | `python -B -X utf8 .runtime/ui-redesign-20261001/review_ui.py` | 93 份基线，21 份修改、72 份不变、15 份新增，无删除；本地文档链接及修改范围通过 |

实现期间的类型、定位及上下文测试失败已修正并复验；没有削弱断言或跳过测试。Windows 沙箱的 `spawn EPERM` 和 Docker 访问限制在获准的本机子进程权限下通过，未改变测试标准或业务保护。

#### 7.4.3 浏览器与证据保存

浏览器数据使用本次独立验收导入的教学项目。主窗为 `backend/apps/tasks/api/views.py` 第 36–122 行，固定窗为 `frontend/src/features/tasks/TaskBoard.tsx` 第 1–200 行；两主题使用同一项目、快照及分析。填写未提交答案 8–14 行后切换主题、源码/学习、任务入口及返回，两个输入仍为 8 和 14。手机以 Enter 打开目录，以 Escape 关闭并返回「项目结构」按钮；导航选择后焦点返回菜单，Ctrl+K 聚焦当前快照搜索，`serializers.py` 筛选显示 1/9 文件。

| 请求窗口 | 实际窗口 | 深色/浅色的页面宽度核对 | 源码形式 |
| --- | --- | --- | --- |
| 1672×941 | 1672×942 | scrollWidth=clientWidth=1662 | 双窗并排 |
| 1920×1080 | 1920×1080 | scrollWidth=clientWidth=1920 | 双窗并排 |
| 1440×900 | 1440×900 | scrollWidth=clientWidth=1430 | 主/固定页签 |
| 1280×800 | 1280×800 | scrollWidth=clientWidth=1270 | 主/固定页签 |
| 768×900 | 768×900 | scrollWidth=clientWidth=758 | 文件抽屉、辅助面板切换 |
| 390×844 | 390×844 | scrollWidth=clientWidth=380 | 导航抽屉、单列和源码页签 |

第一档浏览器高度有 1 px 取整差异，按实际值记录。代码和图仅在自身面板滚动。无效的重复 `start2` 显示「工作区地址无效」及返回入口，后退恢复两窗，前进重新显示明确提示。主题刷新恢复为浅色。显式基础检查完成时间为北京时间 2026-10-01 12:05:01，数据库/队列/Worker 均来自该次通过结果。

本轮证据均在 `.runtime/ui-redesign-20261001`：`browser-ui.json`、深浅两主题各六张截图、`draft-light.jpg`、`drawer-filter-light.jpg`、`invalid-reference-light.jpg`、`frontend-checks-final.log`、`http-report.json`、`csp.json`、`cleanup.json`、`review.json` 及 `ui.diff`。它们是可复核的验收材料，不是新记忆或并行进度文件。

#### 7.4.4 最终范围、文档同步与限制

完整差异仅包含前端 app/features/shared 的相关展示、索引、样式和测试，外部首屏脚本/HTML，以及 AGENTS、README、需求、路线图、结构、前端规范及本计划。93 份原件的 72 份保持摘要一致；没有修改依赖、锁文件、后端、迁移、生成契约、教学内容、示例或前三阶段计划，没有删除文件或执行 Git 写操作。已有非敏感原件及摘要保留，不覆盖既有工作。

长期依据已读 AGENTS、README、需求、总体路线图、项目结构、前端规范、API 清单及第四阶段计划相关章节；没有独立项目记忆文件。本专项将 FR-21/AT-57–63、主题和首屏安全、组件职责、双引用恢复、图预算与检查历史口径同步到现有文档，M21 进度与验证唯一在本文。没有发现本专项实现与已同步文档矛盾；既有 ZIP 25/20 MiB 差异明确保留为范围外问题。

减少动画的媒体规则已在打包页 CSSOM 中核对，但当前浏览器工具不提供操作系统偏好模拟，未更改用户系统设置。未进行其他浏览器、实际移动设备、真实模型外发或真人试用；M20-T02/AT-56 继续等待真实参与。源码着色为轻量行内词法，跨行字符串仍以原文为准；环境摘要只覆盖已加载的任务页。既有包大小警告保留，不扩展为拆包或依赖调整。独立 5181 栈已关闭，5177 日常实例保持原容器和镜像，未宣称已升级。

<a id="trial-test-project"></a>
### 7.5 用户追加：页面试用测试项目

2026-10-01 用户要求“请给我一份测试项目，放到test目录下”。核对 `test` 原本不存在，已有可信任务簿和发布清单一致；按当前页面试用场景提供只读导入材料，不另建可运行应用或扩展解析规则。

新增 `test/README.md`、`test/task-board.zip` 及 `test/task-board/` 的 9 份核心源码，均来自 `examples/task-board`，保持 `task-board/1.0.0` 发布清单中的路径、字节和 SHA-256。ZIP 根目录直接包含 `backend/`、`frontend/`，根路由为 `backend/config/urls.py`。目录副本不独立维护业务逻辑，完整应用的配置、依赖与测试仍在原示例；未打包依赖、缓存、凭据、用户记录或标准答案。

| 工作目录 | 实际命令 | 观察结果 |
| --- | --- | --- |
| 根目录 | `.runtime/m1-t02-venv/Scripts/python.exe -B -X utf8 .runtime/test-project-20261001/verify_test_project.py` | ZIP CRC、根路径、UTF-8、源码与发布摘要及副本一致；6 份 Python AST 语法通过；复用实际 `inspect_archive`/`prepare_archive`，仅写入内存，接收 9、排除/跳过/拒绝均 0 |
| 根目录 | `.runtime/tools/node-v24.21.0-win-x64/node.exe .runtime/test-project-20261001/verify_typescript.cjs` | 使用已有 TypeScript 编译器解析 3 份 TS/TSX，语法错误 0；未安装依赖 |
| 根目录 | `.runtime/m1-t02-venv/Scripts/python.exe -B -X utf8 .runtime/test-project-20261001/verify_delivery.py` | 14 份基线中仅 3 份说明文档修改、11 份原件不变；test 新增 11 份文件，本地文档链接及专项锚点通过，无删除或 Git 初始化 |

实际源码 22,863 字节、711 行，ZIP 10,184 字节，低于现有 20 MiB 导入上限。ZIP SHA-256 为 `c757a168143167913778d5fd5f4858df62e3ff5176df64a88fa283cdb9751a76`。检查脚本、结果和相关 14 份非敏感原件摘要在忽略目录 `.runtime/test-project-20261001`，不是新的项目记忆或进度系统。

同步 README 的试用入口、项目结构的 `test` 职责和单一示例来源边界；没有独立项目记忆文件。原示例及教学内容保持原文件，未改工作台前后端、契约、依赖、数据库或运行实例，未替用户创建作答/实验/模型记录。本次未重新运行完整应用构建或 HTTP/Worker 主线；直接验证导入预处理和源码语法，运行与真实用户试用结论仍沿用各自实际记录，不将本次材料交付标记为 M20-T02/AT-56 通过。

<a id="independent-module-pages"></a>
### 7.6 用户追加：11 个独立模块页面与预览

#### 7.6.1 授权、设计与实现

2026-10-01 用户明确要求实施已确认的独立页面计划，先生成全部模块的深色预览，再进入页面改造，使用 `test/task-board.zip` 作为内容依据。先生成并展示 11 张设计图，随后拆分前端；没有增加后端 API、依赖、迁移、导入源码执行或真实模型调用。

[预览索引](previews/module-pages/index.html)包含工作台、项目导入、源码阅读、API 分析、静态关系图、快照与对比、候选影响、知识与学习、练习与实验、模型讲解及系统与任务。设计采用 1440×900 桌面布局比例，工具生成的原图为 1586×992，未将原始像素尺寸冒称为 1440×900。`manifest.json` 记录实际尺寸及 SHA-256。图片为设计示意，源码摘录、输入响应、服务连接和模型问题不能替代运行结果或新增接口承诺；实际页面只读取现有契约中的信息。未伪造第二份快照、作答、实验、模型历史或学习完成度。

`WorkspaceModulePages.tsx` 提供 11 个独立命名页面，`WorkspacePage` 为组合入口，只共享外壳与经过归属校验的项目、快照、文件上下文。工作台仅展示准备摘要与下一步入口；项目与快照选择、上传只在导入页，双源码只在源码页。API、图与候选影响分别使用 `AnalysisBrowser`、`StaticGraphPanel`、`CandidateImpactPanel`；知识卡片与课程路径归 `KnowledgePanel`，固定作答与回顾归 `LearningPanel`，和 `LabPanel` 同属练习与实验页的局部页签。讲解和基础检查/任务各有独立主体，缺少项目、快照、分析、接口时使用所属模块自己的引导。

同一上下文中的表单保持单实例，隐藏切页及主题切换保留草稿，不自动提交；项目、快照、分析、接口变化仍按资源归属清理。旧 `panel=learning` 的练习或作答链接归练习与实验，带课程目标的链接归知识与学习，显式 `section` 优先。图跨接口清理旧面板及任务；查看全图清理接口专属对象但保留同快照源码引用。全图遗漏所选候选时有界回退当前接口图，使人工提交的原幂等恢复入口仍可用，保留截断提示。单快照项目明确提示需导入第二份，判断使用分页总数。系统页关闭后停用任务列表/结果查询与轮询。源码页 ≥1200 CSS 像素采用双窗口，较窄窗口保留原页签/抽屉。

#### 7.6.2 实际命令和观察

`npm` 仍由 `.runtime/tools/node-v24.21.0-win-x64/node.exe` 执行相邻 `node_modules/npm/bin/npm-cli.js`，子进程 PATH 指向同一目录。Python 仍使用 `.runtime/m1-t02-venv/Scripts/python.exe`；辅助脚本和非敏感基线位于既有忽略目录 `.runtime/module-pages-20261001`。

| 工作目录 | 实际检查入口 | 观察结果 |
| --- | --- | --- |
| frontend | `npm run typecheck` | 通过 |
| frontend | `npm run lint` | 通过，最大警告 0 |
| frontend | `npm run format:check` | 通过 |
| frontend | `npm test -- --run` | 21 个文件、111 项通过，90.06 秒；覆盖页面/URL、单实例草稿、既有幂等/迟到响应、分析分工和候选回退 |
| frontend | `node_modules/vitest/vitest.mjs run src/features/projects/SnapshotTimeline.test.tsx`（固定 Node） | 后续明确快照提示的 3 项通过；验证单快照、总数 2 但单条分页、空列表 |
| frontend | `$env:DEBUG_PRINT_LIMIT='600'; & '../.runtime/tools/node-v24.21.0-win-x64/node.exe' node_modules/vitest/vitest.mjs run src/app/WorkspacePage.test.tsx src/app/workspace-location.test.tsx src/features/projects/SnapshotTimeline.test.tsx` | 最终 3 个文件、23 项通过，33.05 秒；包含后续新增的快照分页、404 和加载状态测试，原有断言保留，切页与恢复 POST 为 0 |
| frontend | `npm run api:types:check` | 通过，现有生成类型与本地契约一致 |
| frontend | `npm run build` | 最终 1578 模块成功；JS 592.46 kB/gzip 185.69 kB，CSS 31.27 kB/gzip 6.97 kB；保留原 500 kB 警告 |
| 根目录 | `python .runtime/module-pages-20261001/save_previews.py` | 11 个不同 PNG 摘要、原始尺寸及静态图片索引 |
| 根目录 | `python .runtime/module-pages-20261001/refresh_frontend.py` 和 `rebuild_final.py` | 按已有锁文件只构建前端；先保留旧镜像，仅更新归属已核实的 5181 验证 frontend，其他 5 个服务标识不变，绑定仍为 127.0.0.1:5181 |
| 根目录 | `python .runtime/module-pages-20261001/import_test_project.py` | 直接导入真实 ZIP，接收 9、排除/跳过/拒绝均 0；显式分析根路由，实际 POST 接口 index=6；模型任务前后均 0 |
| 根目录 | `python .runtime/module-pages-20261001/check_http_final.py` | 最终前端 HTML/主题脚本/JS/CSS 与 dist 逐字节一致，CSP 保持，3 类固定题适用且未暴露答案，作答和模型任务数均 0 |
| 浏览器 | In-app 浏览器，全部导航、双主题及桌面/平板/窄窗口 | 66 个组合均只有当前模块 h1 和主体；页面无横向溢出；双源码并排、刷新和前进/后退恢复通过 |
| 根目录 | `python .runtime/module-pages-20261001/review_modules.py` | 非敏感基线摘要、完整 diff、文件范围、预览清单和本地文档链接核对通过；未初始化 Git |

已有 Windows 沙箱子进程 `spawn EPERM` 由获准的同一测试命令执行权限解除；没有修改测试标准或保护。四份入口/规范文档的 Prettier 告警与修改前基线相同，未扩展为整份长文档格式化。一次重复构建被镜像摘要保护拒绝，查证是本轮已记录的前一次构建，更新辅助脚本的已知摘要检查后正常完成。浏览器批量 AX 读取曾超时，改为每页 DOM 核对及分批采集后完整 66 组通过；这些工具中断未当作产品通过证据。

#### 7.6.3 浏览器、测试数据与实际范围

测试项目只创建一次，ZIP 直接读取现有字节；创建、导入和分析预先保存各自幂等键，未换键重发。只调用项目创建、源码导入、显式静态分析三个写入口；没有提交作答、讲解、候选人工决定、实验或基础检查。真实图返回 42 个节点、49 条边，覆盖限制仍为部分静态结果。创建接口的固定练习确实适用，作答历史为空，未把初始答案视为学习记录。

浏览器初次 1440×900 检查时双源码窗口各宽 494 CSS 像素，位于不同列。后续工具视口发生缩放，六档完整遍历的实际 CSS 视口为桌面 1398×874、平板 746×874、窄窗口 379×819，两主题一致；请求尺寸分别为 1440×900、768×900、390×844。按实际值存档，没有将请求值冒称为测量值；源码/工作台双主题六张对应截图及原始桌面双窗截图亦保留。

填写未提交的代码位置 8/14，经 11 个模块与主题切换后仍保留；组件回归同时确认 POST 为 0、作答组件仅一个实例。导入页的项目名称及 API 页根路由草稿也有跨模块/主题不提交的回归。浏览器双源码地址经刷新、前进和后退恢复，比较页的单快照提示和禁用提交可见。旧链接及缺少前置的各模块引导由实际 Vitest 验证。

最终审阅又核对失效快照与加载状态：依赖快照的模块在读取中展示自己的状态，读取失败时引导重新选择/重试及导入，不错误要求先选接口。浏览器用不存在的快照 UUID 取得 404，源码页明确提示并可进入导入页；没有触发提交。知识页的选择器修正为实际 `learning-module`，浏览器测得知识正文最大宽度 1100px、卡片上边距 18px。前端格式检查在新增测试编辑期间曾报该文件格式告警，完成格式化后最终全量 `npm run format:check` 通过；最终相关 23 项测试及类型检查亦通过。

证据保存在 `.runtime/module-pages-20261001`：`test-project.json`、`frontend-runtime.json`、`http-final.json`、`browser-modules.json`、`browser-responsive-complete.json`、`browser-responsive-extra.json`、`browser-history.json`、`browser-invalid-snapshot.json`、截图、`module-pages.diff` 及 `review.json`。当前 5181 本地验证入口保留用于查看本次页面，旧前端镜像有本地备份；本轮没有更新 5177 日常容器。7.4 中已关闭的栈是历史验收记录，不能据此推断后来重新启用的验证实例仍关闭。

#### 7.6.4 文档同步与限制

已读根指令、README、需求、项目结构、前端规范及本阶段相关历史记录；没有独立项目记忆文件，不新建记忆系统。同步 AGENTS、README、结构、前端规范中的当前模块职责、旧链接和单实例草稿约束，本节唯一维护本次状态与验证。保留前三阶段及 M16–M21 历史结论，未将设计图或工程回归标记为真实用户试用通过。原来的工作台与源码、API 与图、知识路径与作答共用主体已由当前组合和回归证据核对后分离。

未修改依赖、锁文件、后端、迁移、契约、教学内容或测试 ZIP，未删除文件或执行 Git 写操作。现有前端上传提示/校验 25 MiB 与后端 20 MiB 差异继续作为已知范围外问题；设计图采用已核实的后端 20 MiB。静态分析接口 DTO 没有结构化请求/响应 schema，实际 API 页通过视图/序列化器源码证据核对，不硬编码任务簿字段或伪造通用解析能力。设计图服务路径属于源码阅读示意，当前关系图仍只展示现有分析返回。未调用真实模型、运行导入源码或执行真实用户试用；保留包大小警告，不顺带拆包或升级依赖。

最终非敏感基线核对：80 份原件中 17 份修改、63 份摘要不变，无删除；新增 8 份相关前端文件及 13 份明确请求的预览资产（11 PNG、索引与清单）。完整差异经过模块代理和主代理复核，新增测试未弱化原断言，当前本地文档链接全部存在。辅助脚本、测试缓存、生成 dist 与验证数据留在原忽略/运行范围，不列为新增业务或项目记忆文件。

<a id="browser-comments"></a>
### 7.7 用户追加：浏览器注释调整与服务端快照命名

#### 7.7.1 范围与实现

用户提交 7 条浏览器注释，要求修正快照时间线重叠、删除侧栏宣传和全局项目横幅、快照显示名称、选择框缩至五分之一，以及关系页删除上下说明区域并在图内显示关系。查证当时 Snapshot 没有 name 字段，用户明确选择服务端持久命名，授权新增字段、接口与迁移。实施前读现有指令、需求、结构、两端规范、API 约定/清单及本阶段；当前无 Git 元数据或独立项目记忆文件，沿用现有文档。

`WorkspaceShell` 删除宣传块，`WorkspacePage` 删除项目横幅；项目信息仍在工作台和导入模块。所有工作台原生 select 宽度为区域的 20%，保持字体、高度和标签；文本输入、复选框和文本区不属于这次下拉选择框调整。时间线改成名称、真实日期与文件数分行，长名称可换行。

`projects/0002_snapshot_name` 增加 max_length=200、默认空名称字段；历史源码、摘要、UUID、时间、归属和关联保持。API-57 `PATCH /api/v1/snapshots/{snapshot_id}/` 只接受 name JSON，拒绝空、类型错误、额外字段、超长和 C0/C1 控制字符，沿用 Origin/CSRF，不创建任务或改变导入 archive 幂等协议；重复相同名称自然幂等，并发以最后成功保存为准。OpenAPI 和前端类型从实现生成，契约检查纳入 PATCH，不手改生成类型。

`SnapshotNameForm` 在导入和对比模块共享一个默认折叠实例，显式保存服务端名称，关闭、切模块和主题保留草稿。成功后先取消旧详情/分页请求，再同步缓存，迟到旧 GET 不回退名称。列表、时间线、对比选择/历史/结果使用真实名称，旧空名称显示未命名及真实时间；UUID 仍用于内部归属和任务技术详情。

主/固定源码窗口及对比两侧源码同样显示真实名称，原文件身份、摘要及跨快照引用校验保留。名称长度按 Unicode 字符计数，与服务端 200 字符边界一致；不将 JavaScript UTF-16 长度当作字符数而拒绝合法表情名称。

关系页屏幕阅读器标题保留，视觉直接为画布。`StaticGraphPanel` 只读取 graph，删除额外分析摘要/诊断查询及上下区域。`GraphDiagram` 完整模式绘制所有返回节点/边，每条关系有独立可聚焦标签；节点和边共用一个可关闭图内依据区，来源可定位源码。范围/版本折叠在工具栏，候选/确认/排除与截断可识别；后端 100 节点/200 边预算、compact 12/24 模式及 API 页诊断保留。

修正全图点接口节点自动缩回局部图的行为：只有全图关系页保留 endpoint=null 并更新 node；其他模块和已有接口范围的跨接口清理不变。原 URL 校验支持带 node 的全图，刷新恢复仍有效。

#### 7.7.2 实际验证

固定 Node/npm 和 Python 路径沿用 7.6；无依赖或锁文件变化。工作目录为命令表第一列。

| 工作目录 | 实际命令或检查 | 观察结果 |
| --- | --- | --- |
| frontend | `npm test -- --run --configLoader native --pool threads` | 最终 24 文件、131 项通过，111.17 秒；保留原断言，覆盖命名缓存竞态、Unicode边界、草稿、源码名称及全图范围 |
| frontend | `npm run typecheck`、`npm run lint`、`npm run format:check` | 全量通过，lint 最大警告 0 |
| frontend | `npm run build` | 最终 1581 模块成功，JS 596.64 kB/gzip 187.06 kB、CSS 33.97 kB/gzip 7.41 kB；保留 500 kB 警告 |
| backend | `python -B -X utf8 manage.py spectacular --settings=config.settings.test --file ../contracts/openapi.yaml --validate --fail-on-warn` | 生成并校验真实 57 项工作台契约 |
| frontend | `npm run api:types` | 从本地契约生成，未手改声明 |
| frontend | `npm run api:types:check` | 最终本地契约和生成声明一致 |
| 根目录 | `python -B -X utf8 scripts/check_contracts.py --node .runtime/tools/node-v24.21.0-win-x64/node.exe` | 三服务契约/清单及两套前端类型一致；契约测试 11+37+11 项通过 |
| 根目录 | `python -B -X utf8 -m unittest discover -s scripts -p test_check_contracts.py -v` | 4 项通过，包含 PATCH 清单漂移拒绝 |
| 根目录 | `python -B -X utf8 scripts/check_v03_backend.py --docker 'C:/Program Files/Docker/Docker/resources/bin/docker.exe' -- python -B -m pytest apps/projects/tests apps/explanations/tests/test_contract.py --ds=config.settings.local -q -p no:cacheprovider --tb=short` | 隔离 Linux/PostgreSQL 96 项通过，21.65 秒；校验字段、CSRF/来源、内容不变与旧数据可逆迁移 |
| backend | `python -B -m ruff check apps/projects apps/explanations/tests/test_contract.py ../scripts/check_contracts.py ../scripts/test_check_contracts.py` 及对应 `ruff format --check` | 通过，25 文件格式保持 |
| frontend | 固定 Node `node_modules/vitest/vitest.mjs run src/features/projects/SnapshotNameForm.test.tsx --configLoader native --pool threads` | 6 项通过，3.86 秒；200个emoji可保存，201字符拒绝且无写请求 |
| frontend | 固定 Node `node_modules/vitest/vitest.mjs run src/app/WorkspacePage.test.tsx src/features/analysis/ComparisonSnapshotNames.test.tsx --configLoader native --pool threads` | 有效 fixture 的 22 项通过，39.97 秒；不改变原断言 |
| 根目录 | `python -B -X utf8 .runtime/browser-comments-20261001/update_reference.py`、`update_frontend_final.py`、`verify_http.py`、`review_changes.py` | 本地升级、运行资产与源码不变及非敏感差异核对通过；范围见下节 |

首轮名称来源测试未真正发送不可信 Origin：测试辅助客户端的默认 credentials 覆盖了单次参数。核对既有辅助实现后改用显式客户端请求，分别验证 ORIGIN_REJECTED 与 CSRF_REJECTED，最终同组通过，没有弱化保护。沙箱 Windows 子进程 spawn EPERM、Docker socket 和 TemporaryDirectory 权限限制在获准的同一检查命令权限下解除；没有修改测试标准。阶段状态以最终观察为准。

前端默认命令在早期两次全量分别通过 126 项/116.25 秒、130 项/118.89 秒；后续新增 Unicode 及修正 fixture 后，子代理提升执行工具未返回结果，停止该等待且不当作通过。最终 native 配置加载器仍读取原 vitest.config.ts、threads 使用同一测试与断言，规避 Windows 沙箱 forks 的 spawn EPERM，131 项全部执行；没有修改配置、隔离要求、断言或超时。后端名称 Serializer 的只读实检确认 200 个 Unicode 表情接受、201 个表情及普通字符均拒绝，未写数据库。

#### 7.7.3 本地页面与最终核对

本轮只使用 7.6 已导入的 `test/task-board.zip` 测试项目，没有重新导入或重算分析。通过页面显式保存唯一名称“任务簿源码基线”，服务端详情和列表一致，刷新后仍显示；快照除 name 外的全部元数据及 9 份文件清单逐项与命名前基线相等，模型任务和作答仍均为 0。真实页面与 dist 的主题脚本、JS、CSS 逐字节相等，原 CSP 保持。

66 个模块/主题/尺寸组合通过：每次只有当前模块的 h1 和主体、没有全局横幅或侧栏宣传、页面无横向溢出，原生 select 的最大宽度均为 20%。请求视口为 1440×900、768×900、390×844，实际 CSS 视口分别为 1398×874、746×874、379×819，两主题一致；已恢复原浏览器视口。原 1653×928 页面中比较选择框从约 1104px 缩至约 223px，当前父区域约 1115px，比值为 0.20；两次测量父区域有小幅变化，未把它们冒称同一固定宽度。

关系页原接口范围显示 10 个节点/10 条边，查看全图后显示全部返回的 42 个节点/49 条边。键盘 Enter 打开关系依据、关闭依据和源码跳转通过；全图选中接口节点及刷新后仍为 42/49，URL 保留 node 而无 endpoint。图面板上沿约在 72 CSS 像素，不再有原大块说明或下方诊断区；画布内部滚动，证据在图内查看。双源码窗口分别显示真实 views.py 与 TaskBoard.tsx，以及同一服务端名称，无短编号。命名草稿经 11 模块与主题切换仍保留，表单只有一个实例，时间线继续显示已保存名称；之后将未提交输入恢复到真实名称并关闭，没有再次保存。

更新前核对既有验证资源归属、镜像摘要、回环端口及全部任务无排队/运行状态，保留旧镜像。`update_reference.py` 按锁文件构建两端，暂停独立 Worker/核对进程，显式应用唯一 `projects/0002_snapshot_name` 迁移，更新已有 5181 验证的 API/Worker/核对进程/前端；示例 API 和实验核对服务标识不变。后续 `update_frontend_final.py` 只更新同一验证 frontend，其余 5 个服务标识不变；没有删除数据卷或更新 5177 日常容器。

生成契约经过结构比对：原 56 个操作对象完全相等，仅增加 snapshots_rename、命名输入 Schema 和 Snapshot.name。审阅修正两处仅测试 fixture 的错误归属/null 范围和两侧相同摘要，保持原断言；资源就绪等待使用实际图 region，不通过增大超时或跳过测试掩盖失败。一次辅助脚本使用了不支持的作答查询字段，修正为 analysis_id/endpoint_index 后实际只读 HTTP 核对通过；一次 npm 入口路径写错，使用固定 Node 相邻的 npm-cli.js 后完整回归通过。中途工具/测试失败均不作为通过证据。

最终原件基线共 140 份，其中 18 份既有 Python 缓存单独识别为生成物；122 份源码/契约/文档原件中 41 份修改、81 份摘要不变，无删除，新增 7 份相关源码或测试。未初始化 Git。完整差异由主代理和模块代理复核；133 个本地文档文件链接存在，既有 11 张预览图片摘要与清单保持。本轮证据、差异、完整变更清单、截图及非敏感原件只放在既有忽略目录 `.runtime/browser-comments-20261001`，不成为新的项目记忆系统。

已读并同步 AGENTS、README、需求、结构、前后端规范、API 规范/清单与本阶段。核对发现当前契约计数及早期 UI 预算/断点/无新增后端边界描述落后于用户追加范围，已按实际 57 操作、独立源码布局、图内展示和明确授权的名称迁移修正，历史验证结论保留。无独立项目记忆文件。未改依赖、锁文件、安全中间件、模型策略、教学源码或 test ZIP；保留静态预算、单快照无法生成真实差异及既有构建包大小告警，不将工程检查当作真人试用。


<a id="user-review"></a>
## 8. M22 用户视角审阅与迭代（2026-10-02）

### 8.1 授权、基线与验收范围

用户明确授权自主审阅和迭代功能、视觉与交互，并要求先配置 Git、分批提交现有项目、同步文档和路线图。已读取 AGENTS、README、需求、路线图、项目结构、前端规范及本阶段计划；没有独立项目记忆文件，继续使用既有文档。此前“无 Git”的记录是当时事实，本轮已建立本地 main；不推送或配置远程，不调用模型、不运行导入源码、不替代真实试用。

500 份非敏感工程文件在 `.runtime/user-review-20261002/baseline-inventory.json` 留存路径/大小/SHA-256；既有 `.env`、运行数据、依赖、缓存保留并忽略，新加 `.idea/` 忽略。扫描未发现指定凭据格式或敏感路径。沿用既有 Git 身份，core.autocrlf=false 保留文件字节，core.whitespace 的 cr-at-eol 识别现有 Windows 行尾；不进行全库行尾转换。

| 基线提交 | 内容 | 文件数 |
| --- | --- | --- |
| d407674 | 文档与运行配置 | 49 |
| 7bb8622 | 后端、解析器、教学内容与契约 | 217 |
| c0b3d8a | 11 个模块的前端工作台 | 108 |
| 57a7874 | 教学样例、验证脚本与测试输入 | 126 |

提交后的 500 个 Git blob 与清单逐项摘要一致，基线工作区干净。基线 `git diff --cached --check` 的两处原有 EOF 空行分别位于 `docs/previews/module-pages/index.html` 与 `examples/task-board/backend/pyproject.toml`，保留原件，没有为通过检查重排无关文件。其余组通过。后续改动使用 `git diff --check` 单独校验。

### 8.2 迭代任务

| 任务 | 目标 | 状态 |
| --- | --- | --- |
| M22-T01 | Git 配置、原件核对、四批基线 | 已完成 |
| M22-T02 | 导入限制一致、立即反馈、显式提交和恢复 | 已完成；组件边界和真实浏览器导入通过 |
| M22-T03 | 从真实页面审阅引导、视觉层级和导航，按证据改进 | 已完成；状态、草稿和模态键盘复核通过 |
| M22-T04 | 综合回归、浏览器检查、文档一致性与本地提交 | 已完成；前端、真实主线与最终范围核对见 8.5–8.7 |

### 8.3 导入改进及聚焦验证

原 `ProjectNavigator` 提示和 `importArchive` 校验是 25 MiB，核对后端 `ImportLimits.archive_bytes`、`.env.example` 的默认值均为 20 MiB，前端现统一为 20 MiB。`archive-validation.ts` 供表单和 API 入口复用；扩展名、空文件、超限立即说明原因，在摘要计算与写入恢复键之前阻止无效输入。选中文件显示真实名称与字节数，可移除并返回文件控件焦点；未选择/无效文件禁用提交，处理中不能更换文件。前端校验不替代后端归档校验，定制后端更小上限仍以服务端拒绝为准。

未知结果继续保留原幂等键与摘要，移除已选文件不代表取消服务端任务；重新选同一内容才能恢复，不能自动重试。按钮用显式可访问名称隔离组件库加载图标。没有更改 API、Schema、后端限制、导入只读策略或模型策略。

固定工具：根目录 `.runtime/tools/node-v24.21.0-win-x64/node.exe`（24.21.0），`.runtime/m1-t02-venv/Scripts/python.exe`（3.13.15）。frontend 命令通过该 Node 执行。

| 工作目录 | 实际命令或检查 | 观察结果 |
| --- | --- | --- |
| frontend | `node node_modules/vitest/vitest.mjs run --configLoader native --pool threads`（改动前） | 24 文件、131 项通过，135.69 秒 |
| frontend | `node node_modules/typescript/bin/tsc --noEmit`、`node node_modules/eslint/bin/eslint.js . --max-warnings 0`（改动前） | 通过 |
| frontend | `node node_modules/vitest/vitest.mjs run src/features/projects/ImportForm.test.tsx src/app/WorkspacePage.test.tsx --configLoader native --pool threads` | 工作区 20 项通过；新增 7 项中恢复用例首次因 jsdom 文件控件原生校验未触发表单而失败 |
| frontend | `node node_modules/vitest/vitest.mjs run src/features/projects/ImportForm.test.tsx --configLoader native --pool threads` | 修正文件事件测试入口后发现加载图标改变按钮名称；补显式 aria-label 后 7 项通过，4.86 秒，保留全部断言 |
| frontend | `node node_modules/typescript/bin/tsc --noEmit`（导入改进后） | 通过 |

运行环境恢复与最终浏览器结果在后续段落记录；未完成的验收不能沿用历史结果冒称本轮通过。

### 8.4 首页与窄屏导航迭代

审阅发现：首次进入时原工作台展示多项尚未读取的统计，却缺少清楚的首个动作；点击品牌使用整页链接会丢失当前上下文和未提交草稿；窄屏导航仅覆盖部分页面，缺少背景隔离与焦点约束。

`WorkbenchPage` 现在按无项目、仅项目、有快照、已选分析四种状态提供唯一主要入口，以三步准备清单说明当前进度。统计只在已有快照时展示；加载和不可用状态由共享查询传入。保留现有配色、字体与独立模块，使用主内容/准备清单布局和窄屏单列，不恢复已移除的宣传或全局横幅，不自动选择根路由或启动任务。

`WorkspaceShell` 使用原生模态 dialog，导航项共用同一组件；开启聚焦当前模块，Tab/Shift+Tab 在首尾循环，关闭、Escape、遮罩均结束模态并返回按钮焦点，放大到桌面后解除模态。打开时暂停背景滚动并屏蔽搜索快捷键的背景跳转。品牌普通点击沿现有 History API 返回工作台，项目/快照及表单实例保留，修饰键点击沿用链接行为。没有新依赖、接口、迁移或业务存储变化。

### 8.5 最终前端验证

以下命令工作目录均为 `frontend`，PATH 首项为已固定的 `.runtime/tools/node-v24.21.0-win-x64`，不修改工具版本、锁文件或测试配置。

| 实际命令 | 观察结果 |
| --- | --- |
| `node node_modules/vitest/vitest.mjs run --configLoader native --pool threads --reporter=default --reporter=json --outputFile.json=../.runtime/user-review-20261002/final-vitest.json` | 27 文件、151 项全部通过，237.59 秒；原 131 项保留，新增 20 项 |
| `node node_modules/vitest/vitest.mjs run src/app/WorkspacePage.test.tsx src/app/WorkspaceShell.test.tsx src/app/WorkbenchPage.test.tsx --configLoader native --pool threads --reporter=json --outputFile=../.runtime/user-review-20261002/final-navigation.json` | 导航组件最后调整后的 33 项全部通过，无跳过 |
| `node node_modules/typescript/bin/tsc --noEmit` | 通过 |
| `node node_modules/eslint/bin/eslint.js . --max-warnings 0` | 通过，警告 0 |
| `node node_modules/prettier/bin/prettier.cjs --check .` | 全量通过 |
| `node tooling/generate-api-types.mjs --check` | 本地契约与前端类型一致 |
| `node node_modules/vitest/vitest.mjs run src/app/WorkspaceShell.test.tsx --configLoader native --pool threads` | 最后导航调整后 6 项通过，5.16 秒 |
| `node node_modules/vite/bin/vite.js build --configLoader native` | 1582 模块构建通过；JS 601.07 kB/gzip 188.55 kB、CSS 37.54 kB/gzip 8.08 kB |

中途失败均已定位：jsdom 缺少原生 dialog 方法，测试局部补充并在清理时还原，真实背景隔离另以浏览器验证；首页异步摘要等待实际数据；两个原关系图用例改为先等待真实图 region，再在区域内查询按钮，未增大超时或删除业务断言。类型检查发现测试误用了 Playwright 的 exact 选项，已移除；lint 拒绝渲染函数内传递访问 ref 的回调，改为独立导航组件，事件中访问 ref。最终检查均重新执行通过。

保留既有 500 kB 构建告警；`LearningV03.test.tsx` 中合成数据重复 key 的 React 警告也仍存在，该文件及学习实现未改动，测试通过但不能称全程无警告。不通过拆包、放宽规则或屏蔽日志掩盖这些问题。

### 8.6 运行环境恢复与真实浏览器

最初 Docker Linux 引擎和 5181 不可用，Desktop 日志报告 `dockerInference` 监听文件无法访问。普通启动、停止未恢复；核实后只终止本轮启动失败的 Desktop 进程并重新启动。尝试将旧监听文件改名留存也失败，没有移动该文件、清空目录、修改配置或删除数据卷。随后引擎恢复，最终提升权限的 `docker version` 确认 Server 29.4.0/desktop-linux；沙箱内读取 named pipe 的 permission denied 单独属于权限限制，不能据此判断引擎仍故障。

只恢复原 `learning-lab-v1-verify-8e9c1a0a0101` 的已核对容器。恢复脚本检查容器/网络/卷的 Compose 标签、5181 回环绑定、空模型配置和健康状态；原容器身份保留。随后给旧前端镜像加备份标签，沿用 `infra/docker/frontend.Dockerfile` 和锁文件构建，仅更新该项目 frontend，其他服务身份不变。模型仍关闭，未执行迁移、更新日常实例或修改旧快照。

| 工作目录 | 实际命令或检查 | 观察结果 |
| --- | --- | --- |
| 根目录 | `& 'C:/Program Files/Docker/Docker/resources/bin/docker.exe' version` | 沙箱首次 named pipe 拒绝；提升后的同一只读命令取得 Client/Server 29.4.0 |
| 根目录 | `& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 .runtime/user-review-20261002/restore_reference.py` | 9 个既有运行服务恢复，模型关闭、数据保留 |
| 根目录 | `& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 .runtime/user-review-20261002/update_reference_frontend.py` | 仅验收 frontend 改变；JS/CSS/theme-init 三项资产与已测本地产物逐字节相同，CSP 存在，旧快照与文件保持 |
| 根目录 | `& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 .runtime/user-review-20261002/verify_runtime.py` | 真实 9 文件与 ZIP 摘要一致、7 个接口、42 节点/49 边；新项目只有 1 次导入和 1 次分析，模型任务/作答均 0，原教学快照保持 |

最后一个辅助核对脚本首次将仅 POST 的快照分析路径用于 GET，得到 405；查证 `AnalysisNavigator` 和 `queryJobs` 后改为原任务查询 `kind=analysis&snapshot_id=…`，重新核对通过，未改产品接口或放宽断言。

浏览器先在临时 5182 开发入口验证展示与键盘，明确该阶段无可用 API；环境恢复后在更新后的 5181 完成真实主线，不能把早期页面显示当作后端证据。以新项目“用户视角验收 2026-10-02”验证：非 ZIP、0 字节、20 MiB+1 字节均显示具体原因且禁用提交；移除后焦点回到文件控件；选择 10,184 字节的 `test/task-board.zip`，经品牌返回再进入导入，文件仍保留；显式导入成功接收 9 文件，再显式选择 `backend/config/urls.py` 提交分析成功。

首页分别显示项目已开、快照就绪、分析已选的主要入口，真实文件数为 9/6/3（全部/Python/前端），刷新保留同一项目、快照和分析。进入 POST 接口、关系图后“查看全图”显示 42/42 节点和 49/49 边，URL 清除 endpoint；源码页实际读取 views.py 和固定的 TaskBoard.tsx，后者按 200 行分段。已有静态诊断和部分覆盖提示保持，没有将图等同于运行链路。

两主题的桌面与窄屏首页、模态菜单已实际查看。请求视口为 1280×800、390×844，实际 CSS 视口为 1243×777、379×819；文档宽度不超过实际视口。键盘正反向循环、Escape、遮罩关闭、焦点返回、放大窗口解除模态通过；有快照且搜索可用时，菜单中的 Ctrl+K 仍不移焦到背景。品牌返回保留项目名称草稿；合成草稿已清空，未提交。最终恢复浏览器原尺寸，保留 5181 供查看。

证据仅放在忽略的 `.runtime/user-review-20261002`：`browser-workflow.json`、`http-verified.json`、`runtime-restored.json`、`runtime-updated.json`、测试 JSON、原件清单及 01–11 实际截图。其中 01–08 是开发入口的视觉/键盘证据，09–11 是真实验收入口，不能混淆。重启后的 HTTP/Worker 主线是本轮实测，不沿用昨日的 ready 标记。

### 8.7 文档同步与最终边界

已读并同步 AGENTS、README、需求、路线图、项目结构、前端规范及本阶段计划。新增 FR-22/AT-64–66，记录准备引导、20 MiB 前端边界、未知恢复、模态导航和品牌返回；本节唯一记录进度与证据。路线图 6.3 的组合布局和“没有新增 API”落后于先前已完成的独立模块/API-57，经源代码、现有契约及 7.7 历史核对后校正，未改写历史验收结论。旧“无 Git”仅是历史状态，本轮授权和当前 main 另行说明；没有建立独立记忆系统。

本轮本地工程验收不代表真实用户试用、任意项目识别率、其他浏览器或平台兼容、真实供应商质量或容量承诺。后端和依赖未变化，因此没有重复全量后端/固定实验回归；未知网络结果恢复以组件受控测试验证，没有人为断开真实服务。后续优先观察真人在根路由选择和首个接口上的卡点，再决定增强，不自动扩展产品边界。

最终在根目录执行 `& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 .runtime/user-review-20261002/verify_review.py`：500 个基线 Git blob 与原件清单逐项相等；基线之后 14 份原文件修改、486 份保持、新增 4 份前端源码/测试，无删除或意外路径；112 个本地文档文件链接存在。`git diff 57a7874 --check` 通过，指定凭据格式扫描无命中，跟踪清单未包含敏感配置、运行数据、依赖、IDE 或构建产物，没有远程。完整差异保存在忽略证据目录，暂存前按明确路径逐项核对。

导入反馈提交为 `3c6d4f5`，首页与导航连同本节记录以 `feat: 改进项目准备引导与窄屏导航` 单独提交；精确提交哈希以本地 `git log` 为准。四个基线提交保留在前，没有合并或改写历史。临时 5182 开发进程已停止，最终可查看入口为已核验的 5181；旧前端镜像备份保留在本地，不删除测试数据卷。

<a id="viewport-pagination"></a>
## 9. M23 全模块分页与系统职责拆分

### 9.1 授权、审阅与实现

2026-10-02 用户追加要求：页面内容显示不全时通过分页查看，不向下滚动；审阅所有页面，并拆为系统状态、任务历史两个模块。开工前核对 main 的 `6558d19`，工作区干净，读取 AGENTS、README、需求、路线图、结构、前端规范和本计划。沿用本地提交授权，没有配置远程、推送或发布。

旧页面实际 CSS 视口为 1243×777 时，导入、API、快照对比、知识、系统任务文档高度分别达到 820、1093、858、2072、1793px；双源码、文件树和关系画布还有独立纵向滚动。系统检查表单和历史记录共用一个页面，职责混杂。以上是本轮浏览器观察，不是生成预览。

外壳固定为可视高度，标题和底部内容页码保持可见。共享 `ContentPager` 保留同一 DOM、组件与表单状态，按实际高度、文字行和控件边界分页；并列内容没有共同断点时承接跨页部分，跨界短块在能完整容纳的页出现。窗口、展开与异步内容变化会重新计算，选择新资源或数据批次回到首页；焦点、原生校验和正文翻页键可定位内容。观察器仅在激活时运行，卸载释放；不把页码写入业务存储。

源码继续按原接口每段最多 200 行读取，再按可视区域分页。窄屏长行换行，文件树展开参与分页；搜索展开入口。宽源码和关系图保留必要横向查看。图内依据改为内容块，选择后自动聚焦并显示所在页。快照命名的小面板复用分页，草稿不复制。

`SystemStatusPage` 负责显式基础检查、原幂等键恢复、进度和结果；`JobsPage` 负责历史列表及结果入口。侧栏共 12 个模块，旧 `?view=jobs` 继续进入任务历史。每批最多 20 条记录，再按屏幕分页；切换批次保留项目、快照和分析，浏览器历史可回退。系统摘要仅依据已加载的最近 20 条记录范围，不是持续监控。没有新增 API、Schema、依赖、锁文件变更或模型调用方式。

| 任务 | 目标 | 状态 |
| --- | --- | --- |
| M23-T01 | 审阅全部模块、确定分页边界与系统拆分 | 已完成；实际溢出与原调用路径核对 |
| M23-T02 | 共享分页、源码/图/表单适配及独立系统页面 | 已完成；复用原数据与提交协议 |
| M23-T03 | 行为回归、双主题和多尺寸真实浏览器 | 已完成；证据见 9.2–9.3 |
| M23-T04 | 文档同步、完整差异审阅与本地提交 | 已完成；范围与交付边界见 9.4 |

### 9.2 实际测试与构建

工具沿用 Node 24.21.0 与 Python 3.13.15，路径见 8.3；前端命令在 `frontend` 执行，PATH 首项为固定 Node 目录。

| 实际命令或检查 | 观察结果 |
| --- | --- |
| `node node_modules/vitest/vitest.mjs run --configLoader native --pool threads --reporter=default --reporter=json --outputFile=../.runtime/pagination-review-20261002/final-vitest.json` | 最终 29 文件、165 项全部通过，328.04 秒，无跳过；覆盖分页首尾、并列断点、焦点/尺寸/草稿、12 模块、系统拆分、恢复与旧链接 |
| `node node_modules/typescript/bin/tsc --noEmit` | 通过 |
| `node node_modules/eslint/bin/eslint.js . --max-warnings 0` | 通过 |
| `node node_modules/prettier/bin/prettier.cjs --check .` | 通过 |
| `node tooling/generate-api-types.mjs --check` | 前端类型与本地契约一致，57 项 API 未改动 |
| `node node_modules/vite/bin/vite.js build --configLoader native` | 1587 模块构建通过；JS 597.52 kB/gzip 187.93 kB、CSS 40.94 kB/gzip 8.67 kB |

中途类型检查发现目标版本不支持 `toReversed`、任务类别索引类型不明确以及测试误用 Playwright 的 `exact` 选项，均已修正。补充的 42 项聚焦回归一度有 2 项工作区测试超时：先查询大范围按钮，而快照/练习导航还在异步加载。改为先等待对应导航区域或命名文本，再保留原按钮和业务断言；没有增加超时、跳过用例或放宽断言，最终全量重新通过。格式问题修正后重新检查。

仍有原来的 500 kB 构建提醒，以及 `LearningV03.test.tsx` 合成数据重复 key 的 React 警告；该测试通过，不称全程无警告。分页组件的 jsdom 几何替身只验证行为，真实排版另见浏览器证据。

### 9.3 本地运行与浏览器证据

先在 5182 开发入口验证，随后更新既有 `learning-lab-v1-verify-8e9c1a0a0101` 的 5181 独立验收前端。沿原 Dockerfile/锁文件构建，备份镜像 `learning-lab-frontend:pagination-backup-1b9e40a1de3e` 保留。仅 frontend 容器改变，其他服务身份、原快照和文件保持；JS、CSS、theme-init 三项运行资产与本地已测构建逐字节相同，CSP 保持。未更新日常实例或远程资源。

根目录实际执行：

- `& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 .runtime/pagination-review-20261002/update_reference_frontend.py`：仅本地验收 frontend 更新，身份、回环端口、资产、CSP 与原数据核对通过。
- `& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 .runtime/pagination-review-20261002/verify_runtime.py`：9 文件摘要仍与教学 ZIP 一致，7 接口、42 节点/49 边保持；原项目仍只有一次导入与一次分析，模型任务和作答均 0，原命名快照保持。

浏览器在系统状态显式执行一次固定检查，任务 `f54d90c1-7c87-467d-9bcc-c7c3b3fc7362` 成功，结果的 database/queue/worker 均为 passed。总任务从 10 增至 11，仅新增该次检查；原有失败分析记录保留。历史结果跳转到系统状态并保留项目与快照。未调用模型、重新导入、重复分析或提交练习。

| 浏览器复核 | 实际观察 |
| --- | --- |
| 桌面、窄屏、较矮窗口 × 双主题 × 12 模块 | 请求视口 1280×800、390×844、1280×480，实际 CSS 分别为 1243×777、379×819、1243×466；72 条记录均无文档横纵溢出，翻页栏在窗口内，已读内容没有内部纵向滚动 |
| 首尾与控件可达 | 桌面全部模块逐页检查；矮窗口和窄屏对源码、API、关系、练习、知识逐页核对，参与检查的控件、短段落及源码行均能在某页完整显示；闭合 details 的隐藏说明不当作遗漏，展开后重算并完整显示 |
| 长源码与完整图 | 窄屏固定 TaskBoard.tsx 第 1–200 行分为 9 个内容页；“下一段”回到内容首页，第 201–265 行分为 3 页，末行和分段按钮可达。全图 42 节点/49 边分为 5 页，93 个受检元素全部可达；末页选择 readPending 自动回到含完整依据的首页，保留全图范围 |
| 草稿与命名 | 项目名称合成草稿在翻页、切换任务历史后保留，随后清空，未创建项目；较矮窗口快照命名表单及翻页栏均在窗口内，未保存名称 |
| 导航与搜索 | 390×480 矮窄窗口菜单全部 12 个入口在可视区域，选择后关闭；源码搜索回到首页并展开文件入口，原双窗口资源保留 |

浏览器和几何观察仅针对当前教学样例、受控状态及本机 IAB。编辑中的 textarea 保留原生光标/输入行为，横向查看仍用于宽源码和关系画布；没有将任意超长文本或其他浏览器推广为已验收。系统结果仅代表单次检查，不保证持续可用。

证据保存在忽略目录 `.runtime/pagination-review-20261002`：`before.json`、`final-viewports.json`、`final-content-coverage.json`、`final-vitest.json`、`runtime-updated.json`、`http-verified.json` 及 `after-*.jpg`。早期开发入口记录和中途失败保持原样，不冒充最终验收。截图包含独立系统状态、任务历史桌面/窄屏和源码末段。

### 9.4 文档同步与交付边界

已读并同步 AGENTS、README、需求、路线图、项目结构、前端规范和本阶段计划。FR-23/AT-67–69 明确分页、草稿/焦点与系统职责；当前入口和模块数量改为 12，历史 11 模块预览及 M21/M22 记录保留历史标识，原纵向滚动与抽屉要求明确由当前分页规则替代。README 启动说明中的旧“系统与任务”经现有路由和页面核对后校正。没有独立项目记忆文件，不另建记忆系统。

本次仅改前端及相关文档，保留后端、契约、依赖、锁文件与既有数据；没有重跑未改后端的全量回归。真实用户试用仍未进行，真实模型输出和未提供的项目内容不在本轮验收内。既有大包及合成 key 警告记录为限制，不顺带改动配置。完成此次用户追加要求后停止，不启动路线图候选。

根目录实际执行 `& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 .runtime/pagination-review-20261002/verify_review.py`：以 `6558d19` 的 504 个原文件为基线，24 份修改、480 份摘要保持，新增 7 份，共 31 个变更文件；无删除或意外路径，118 个本地文档链接及新增锚点存在，指定凭据格式扫描无命中，远程为 0，`git diff 6558d19 --check` 通过。完整差异、清单和摘要保存在 `final-review.json` 与 `final-iteration.diff`。

本地提交使用 `feat: 全模块内容分页并拆分系统状态与任务历史`，精确哈希以 `git log` 为准，不改写已有提交。临时 5182 开发进程已停止；浏览器恢复默认尺寸，5181 独立验收入口保留供复核。

## 10. M24：参考 attack_verify 的前端整体改造

### 10.1 授权、现状与实施范围

2026-10-03 用户明确要求实施已确认的 M24 计划：参考 `F:\Program\Python\attack_verify\web_project` 新版首页、项目列表和分区导航，统一全部 12 个独立模块的样式、布局、组件和交互。采用顶部四分类、分类所属二级侧栏、蓝灰双主题、桌面紧凑表格和窄屏记录卡；保留可视区域分页、单实例草稿和既有业务能力。参考代码用于提取视觉与操作规则，未把参考项目的固定最小宽度、纵向滚动、页面销毁、路由或依赖迁入当前项目，也未宣称已验收参考项目实时浏览器画面。

实施前读取 AGENTS、README、需求、结构、前端规范、API 清单/契约与本阶段计划，并核对实际 React、TypeScript、Ant Design、TanStack Query 和测试入口。Git 基线为 `main` / `d50e751`，初始工作区干净；当前是 12 模块、57 项 API，早期“无 Git、11 模块”的记录属于历史状态。没有独立项目记忆文件，不另建记忆或任务进度系统。

| 任务 | 实际完成内容 | 状态 |
| --- | --- | --- |
| M24-T01 | CSS 语义变量与 Ant Design token 统一；四分类及所属侧栏；会话内最近模块、旧 section 链接及 History API；响应式顶栏和模态菜单 | 已完成 |
| M24-T02 | PageHeading、ContentState、RecordList；桌面 Ant Design Table 与窄屏卡共享数据/选择；完整行参与现有内容分页，明确记录批次和内容页码 | 已完成 |
| M24-T03 | 12 模块共用紧凑视觉与反馈；项目/API/差异/任务列表和页内详情；知识目录与正文、讲解三步骤和完整预览 | 已完成 |
| M24-T04 | 184 项回归及质量检查；72 组基础浏览器检查、完整预览和边界补查；隔离运行与文档同步 | 已完成 |

### 10.2 实现与变更文件

保留 `app → features → shared` 依赖方向。导航分类从既有 section 推导，未新增 URL 参数；工作台没有二级侧栏，其他分类首次进入 import、learning、system，随后恢复本次会话最后访问的所属模块。表单仍由原业务层持有，隐藏模块保持单实例；共享呈现组件不发起请求、不选择资源。RecordList 关闭 Table 内置分页且不设置纵向滚动，稳定行标识沿用资源 ID；窄屏只渲染卡片分支，不复制表单。

保留默认深色及已有偏好读取，使用系统中文字体、14px 正文、12px 辅助文字、20px 页面标题、32px 常用控件和 4/6px 圆角。原生业务下拉的区域宽度 20% 规则保留。减少动态效果、焦点、禁用与加载反馈统一；主按钮使用深蓝文字，最终浏览器测得浅色主题对比度 4.61、深色主题 6.33，默认/悬停/按下 token 均有不低于 4.5 的测试断言。

| 文件（均相对项目根目录） | 实际变更 |
| --- | --- |
| `frontend/src/app/ThemeProvider.tsx`、`ThemeProvider.test.tsx`、`global.css` | 主题语义变量、Ant Design 算法/token、偏好与主按钮对比度验证 |
| `frontend/src/app/WorkspaceShell.tsx`、`WorkspaceShell.test.tsx` | 顶部分类、二级导航、响应式外壳、历史与模态焦点验证 |
| `frontend/src/app/workspace-navigation.ts`、`workspace-navigation.test.ts`、`shell-redesign.css`（新增） | 分类映射、默认入口、会话访问记录和顶栏/侧栏样式 |
| `frontend/src/app/WorkspaceModulePages.tsx`、`WorkspacePage.tsx`、`WorkspacePage.test.tsx`、`module-redesign.css`（新增） | 统一标题、模块组合及全模块样式，验证 12 页、草稿与无隐式写入 |
| `frontend/src/shared/components/PagePresentation.tsx`（新增）、`Feedback.tsx`、`PageControls.tsx` | 页面标题、状态反馈、记录批次与内容分页文案 |
| `frontend/src/shared/components/RecordList.tsx`、`RecordList.css`、`RecordList.test.tsx`（新增） | 表格/卡片呈现、完整行边界、选择状态和尺寸切换测试 |
| `frontend/src/features/projects/ProjectNavigator.tsx`、`ProjectNavigator.css`、`ProjectNavigator.test.tsx`（后两者新增）、`SnapshotTimeline.test.tsx` | 项目与快照紧凑列表；创建、导入、命名与恢复流程保持；分页测试文案同步 |
| `frontend/src/features/analysis/AnalysisBrowser.tsx`、`ComparisonWorkspace.tsx`、`AnalysisV02.test.tsx`、`IndependentAnalysisPages.test.tsx`、`ComparisonSnapshotNames.test.tsx` | 接口/差异表与页内详情，诊断单独展开，来源定位与双侧源码保持 |
| `frontend/src/features/jobs/JobsPage.tsx`、`JobsPage.test.tsx`、`JobsPage.css`（新增） | 任务表/卡片与页内标识、错误、结果和重试关联 |
| `frontend/src/features/learning/KnowledgePanel.tsx`、`KnowledgePanel.test.tsx` | 知识目录与选中正文；用户选择后定位正文并切换所属内容页；取消迟到焦点 |
| `frontend/src/features/explanations/ExplanationPanel.tsx` | 三步确认流程、记录分页、整体操作区；源码片段和完整消息自动换行并参与内容分页 |
| `frontend/tooling/test-dom-setup.ts`（新增）、`frontend/vitest.config.ts` | 测试环境提供可清理的 resize-aware matchMedia，支持 Ant Design 与响应式回归 |
| `AGENTS.md`、`README.md`、`docs/requirements.md`、`docs/frontend-guidelines.md`、`docs/project-structure.md`、`docs/phase-4-plan.md` | 同步当前入口、FR-24/AT-70–74、组件职责和 M24 唯一验收记录 |

源码双窗口、每段 200 行、SVG 图范围与截断提示、候选/确认/排除、学习与练习流程、系统检查、外发确认和幂等恢复均沿用原实现。未改后端、57 项 API、生成 DTO、Schema、依赖、锁文件、认证/授权、部署配置或教学内容；未增加关系图缩放、编辑或新查询能力。

### 10.3 组件回归与质量检查

先执行导航/主题、共享列表/API/比较、项目/导入/任务、工作区/知识/讲解/分页的相关回归，随后冻结前端源码执行全量。最终 32 个测试文件、184 项测试全部通过，耗时 161.55s；覆盖旧链接和分类入口、草稿与无隐式 POST/PATCH、完整行分页、详情重测、校验焦点、尺寸变化、迟到响应、源码分段与模型确认。未修改可执行后端，因此未重复后端全量回归。

工作目录 `F:\Program\Fall_Campus_Recruitment\frontend`，实际最终命令如下，全部退出码为 0：

```powershell
$taskNode = 'F:\Program\Fall_Campus_Recruitment\.runtime\tools\node-v24.21.0-win-x64\node.exe'
& $taskNode node_modules/vitest/vitest.mjs run --configLoader native --pool threads --reporter=default --reporter=json --outputFile=../.runtime/m24-redesign-20261003/final-vitest.json
& $taskNode node_modules/typescript/bin/tsc --noEmit
& $taskNode node_modules/eslint/bin/eslint.js . --max-warnings 0
& $taskNode node_modules/prettier/bin/prettier.cjs --check .
& $taskNode tooling/generate-api-types.mjs --check
& $taskNode node_modules/vite/bin/vite.js build --configLoader native
```

构建转换 1595 个模块，产物 CSS 54.16kB、JS 1,028.08kB（gzip 318.81kB）。保留超过 500kB 的构建提示，不顺带改拆包或阈值。Vitest 的 jsdom 伪元素 getComputedStyle 提示保留；最初缺少 matchMedia 的失败由测试环境补足后解决，没有删除或弱化测试。中途主题文件变动与运行中的模块缓存造成的一次混合版本失败另存 `theme-mixed-vitest.*`，最终冻结源码重跑的 `final-vitest.*` 才作为验收依据。未把中途失败或开发入口截图当作最终通过证据。

### 10.4 隔离运行、真实浏览器与完整内容

Docker Desktop 原先停止，经官方 `docker desktop start` 恢复；仅恢复既有独立验收 Compose 项目 `learning-lab-v1-verify-8e9c1a0a0101` 的原服务。仅其 frontend 镜像/容器更新，旧镜像保留备份；未更新日常实例，未初始化、迁移或删除任何数据卷。实际入口 `http://127.0.0.1:5181`，最终 JS/CSS/theme-init 内容摘要与本地 dist 一致，CSP 保持；原项目和快照文件核对保持。5182 仅为本轮临时开发代理。

根目录实际运行固定 Python 的 `-B -X utf8` 命令：`.runtime/m24-redesign-20261003/resume_reference.py` 恢复原验收服务、`update_reference_frontend.py` 更新单一 frontend 并核对资源/资产、`verify_runtime.py` 只读核对原样例；均保存日志。原样例 9 个文件摘要与 `test/task-board.zip` 相同，7 个接口、完整图 42 节点/49 边保持；原项目仍只有一次导入、一次分析，原命名快照未变，总任务仍为既有 11 条，模型任务与作答记录均 0。本轮没有重新导入、分析、提交练习或执行新的系统检查。

为完整预览验收，先在浏览器显式准备一次预览，实际得到 MODEL_NOT_CONFIGURED 及请求标识。随后运行 `.runtime/m24-redesign-20261003/run_seed_preview.py`，只在该独立验收环境用现有源码生成一份确定性 ContextPreview：`9ae54508-7bec-4f95-bd78-1c05bcb93fcf`，标记“ M24合成预览-禁止外发”，目标 `https://m24-preview.invalid`、25598 字节、7 个源码片段和 2 条消息。配置覆盖仅存在于该 Python 进程，使用失败封闭的网络/模型/任务保护并核对原文件摘要与记录数量；未保存密钥或变更运行实例配置，未创建确认、讲解请求、输出或模型任务。重复核对使用同一预览 ID，没有重复创建；该材料是预览排版证据，不是供应商输出或真实模型质量验证。

浏览器使用本机 IAB 与真实 5181 资产；针对设备像素比校准设置值，记录的 **实际 CSS 视口** 为下表数值。最终基础矩阵 12 模块 × 双主题 × 3 尺寸共 72 组，逐页检查文档边界、页内窗口、完整行/控件/短段落覆盖及固定分页入口；所有组无文档横纵溢出、翻页入口可见、受检元素均至少在一页完整可达，桌面表格没有横向溢出。关闭 details 的内容按隐藏状态处理，展开后单独复核，未以隐藏 DOM 冒充已读内容。

| 浏览器复核 | 最终观察 |
| --- | --- |
| 1280×800、390×844、1280×480 × 双主题 × 12 模块 | 72 组全部通过；记录批次与内容页码分开，未产生隐式提交 |
| 768、900、1024、1199、1200、1600px 宽窗 | 表格及操作可达，无文档溢出；修复中等宽度任务类型列过窄，768px 下该列约 105px |
| 390×480 矮窄菜单 | 12 模块和关闭入口均在窗口内；双向 Tab 环、Escape 和关闭后返回触发按钮；扩大至 1200px 解除模态 |
| 导航、搜索、草稿与知识焦点 | 前进/后退恢复旧 section 与上下文；源码 Ctrl+K 定位搜索；140 字符未提交项目名称跨页/模块/主题/尺寸保留，随后清空且未创建项目；选择知识卡自动显示并聚焦正文所在页 |
| 完整图与长源码 | 42/42 节点、49/49 边的全图窄屏 5 页，94 个受检元素完整可达；末页选中 readPending 回到图内依据页。TaskBoard.tsx 201–265 行窄屏 3 页、72 个受检元素可达，末行和分段按钮完整显示 |
| 1200px 双源码边界 | 两窗口均显示，主文件 122 行与固定 TaskBoard 201–265 行独立分段；6 个内容页、246 个受检元素可达 |
| 全部片段与完整消息展开 × 三尺寸 × 双主题 | 分别 23、39、48 个内容页；9 个 pre 文本块均自动换行、宽度不溢出，分页可见区间连续覆盖全高度，无内部纵向滚动；完整控件与短段落检查无遗漏 |
| 模型确认区 | 本地勾选使保存按钮可用，生成仍禁用；取消勾选后恢复未确认状态，未点击保存或生成；模型外发次数 0 |
| 主按钮对比度 | 实际计算浅色 4.61、深色 6.33；悬停/按下 token 另由组件测试覆盖 |

完整消息检查以文本块的连续可见区间、换行宽度和首尾操作为证据，不宣称对任意内容执行逐字语义审阅。编辑 textarea 保留原生行为，宽源码与关系画布保留必要的横向查看能力。当前样例、受控错误/空态和本机浏览器证据不能推广成其他浏览器、任意超长数据或真人试用通过。

交付前再次只读核对 HTTP 样例及三份实时资产摘要，均保持；默认 Docker 命名管道权限拒绝后，主代理三个短只读提升命令实际通过：按项目标签查询运行容器、比对 network/volume 清单、在已核对的原 API 容器内执行 `SET TRANSACTION READ ONLY` 计数。8 个非 frontend 运行容器保留原 ID，3 个网络和 6 个卷身份保持；模型地址/ID/凭据配置均关闭，ContextConsent、ExplanationRequest、Explanation、模型 Job 均 0，总 Job 11，本轮合成预览恰为 1。子代理较长的追加查询未返回并已终止，其限制保留为历史，不用该未完成调用作为通过证据；最终结论来自随后实际成功的主代理查询。

全部日志、截图和只读核对材料位于既有忽略目录 `.runtime/m24-redesign-20261003`：`final-vitest.json/.log`、`final-build.log`、`runtime-updated.json`、`http-verified.json`、`final-runtime-review.json`、`synthetic-preview.json`、`browser-matrix.json`、`content-coverage.json`、`medium-wide-check.json`、`menu-check.json`、`draft-check.json`、`long-name-draft.json`、`history-single-module.json`、`knowledge-focus.json`、`full-graph-mobile.json`、`long-source-end-mobile.json`、`preview-final-*.json`、`preview-controls-summary.json`、`contrast-final.json` 和 `final-desktop.png` / `final-mobile.png`。中途失败及修正前材料保留原始记录，最终验收以明确标记 final 的材料为准。

### 10.5 文档同步与限制

已同步 AGENTS、README、需求、前端规范、结构说明及本计划；FR-24/AT-70–74 明确分类导航、统一呈现、草稿/分页/焦点和模型边界。修正当前文档中原绿色主色、全模块侧栏等不再适用的现行说明，依据实际 token、分类映射及 12 个页面核对；保留 M21–M23 的历史记录，不重复维护 M24 进度。未建立独立项目记忆文件。

真实用户试用仍待进行；真实模型质量、其他供应商和未提供内容未验证。JS 大包提示和 jsdom 伪元素提示保留。本轮未执行提交、分支、推送、发布或日常实例更新；不自动进入后续候选功能。

根目录实际执行 `& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 .runtime/m24-redesign-20261003/verify_review.py`：以 `d50e751` 的 511 个原文件为基线，29 份修改、482 份摘要保持，新增 12 份，共 41 个变更路径；无删除或意外路径，106 个本地文档目标及 23 个锚点有效，UTF-8 可读，指定凭据格式扫描无命中，远程为 0，`git diff d50e751 --check` 通过。清单、摘要与完整 tracked 差异保存为 `final-review.json`、`final-m24.diff`；新增文件另按本节清单逐份审阅。临时 5182 开发进程已停止，浏览器视口覆盖已解除；5181 独立验收入口保留供复核。

<a id="m25-workbench"></a>

## 11. M25：图片风格首页与配套功能

### 11.1 授权、基线与实际范围

2026-10-03 用户明确要求实施已确认的 M25 计划。以提供的深蓝工作台图片为构图依据，重构首页并推广顶栏、面板、主操作和图标规则；其他 11 个模块保留主体布局。新增全部本地项目名称/当前快照路径/当前接口方法与路径搜索、真实终态任务的显式已读和精确课程版本的用户阅读记录。账号、登录、头像菜单、源码全文搜索、关系图新能力和模型外发均不在本轮范围。

初始为 `main` / `d50e751`，已有 41 个未提交 M24 文件。修改前将它们逐份复制到 `.runtime/m25-home-20261003/baseline`，并在 `before.json` 保存 523 个工程文件摘要；本轮增量按这一基线核对，不能把未变的 M24 文件重复计入 M25。未提交、创建分支、推送或部署日常实例。读取 AGENTS、README、需求、前端规范、结构、API 清单/契约及本阶段计划；项目未指定独立记忆文件，不建立新记忆系统。

| 任务 | 实际完成内容 | 状态 |
| --- | --- | --- |
| M25-T01 | 两项 GET 搜索、终态通知与读水位、课程精确版本进度、三表迁移、严格输入及后端测试；62 项契约与生成 DTO | 已完成 |
| M25-T02 | 图片首页五区域、本地 React/DRF SVG、68px 顶栏、8px 公共面板、双主题白字主按钮、真实底栏与高度计算 | 已完成 |
| M25-T03 | 200ms/组合输入搜索、分组记录分页/取消、通知可见轮询与显式写入恢复、课程阅读、任务按 ID/结果归属导航 | 已完成 |
| M25-T04 | 前后端全量及质量检查、72 组浏览器矩阵、完整预览/源码/模态/草稿复核、隔离资源保护与文档同步 | 已完成 |

### 11.2 实现与精确职责

首页从成功读取的项目、已发布快照和绑定该快照的分析计算准备阶段。Hero 的主要入口随准备阶段变化；四个快捷入口为准备项目、导入源码、查看分析和开始学习，只导航。最近项目按创建时间取前三项，读取最新已发布快照及其真实分析任务；不虚构宿主路径或访问时间。课程取实际发布的前三门以内；本机验收库只有一门，显示真实的 `0 / 8` 阅读进度。四项统计在当前样例为源码文件 9、接口 7、前端请求 3、静态确认关联 2；缺失/失败显示未读取，不当作零。

≥1440px 使用 2.4∶1 的 Hero/准备区、四列快捷入口和三列下部面板；较小桌面快捷入口两列，中等窗口分区上下排列，窄屏单列/原模态菜单。低于 600px 隐藏装饰和品牌副标题；底栏参与可用高度。CSS 与 Ant Design 主操作使用 `#1767d8` / 白字、hover `#1b6bd5`、active `#1359bb`，实测两主题默认对比度均 5.29，三种状态另有组件断言。正文 14px、辅助 12px、首页面板标题 18px、宽窗 Hero 40px；局部紧凑排版保证参考视口的五区域都在同一内容页可达。

搜索只在项目和接口列表显式允许 `q`，最多 200 字符；接口在筛选前保留原 index。文件来自成功读取的完整当前快照清单。三个结果组各有记录分页，沿用每批 20 条，无关键词不查询；关闭、关键词、批次或上下文改变取消原请求。当前顶栏使用唯一直接输入框和非模态下拉结果，同一内容树继续分页；Ctrl/Meta+K 聚焦输入，Escape 收起并保持输入焦点，外部点击或焦点离开收起，原源码筛选框独立保留。M25 初始模态验收保留为历史，本轮追加验证见 11.6。

通知 GET 由 `succeeded/failed` Job 派生，不创建记录。可见时每 5 秒读取，后台暂停；打开/查看不自动已读。单条仅接受 `{read:true}`，全部已读推进至本次列表 `as_of`，单调且拒绝未来时间；后完成的任务保持未读。未知 PATCH 结果读取核实，不自动重发。跨批次所选任务独立按 ID 读取；进入结果前核对实际资源、任务与项目/快照归属，选择改变取消旧操作。

课程阅读使用独立 `course` URL，无需项目/接口；原 `curriculum/goal` 的适用路径语义保留。进度绑定课程实体及精确 card 版本，显式标记/撤销已阅读，GET 零写入；不继承新版本，不影响练习、自评、先修关系或掌握程度。未知写入同样读取核实。新增三个本地单用户状态表；两份迁移只建表，不修改原 Job、源码、快照或教学内容。

| 文件组（相对根目录，精确增量另见验收清单） | 实际变更 |
| --- | --- |
| `backend/apps/projects/api/views.py`、`analysis/api/views.py`、`common/api.py`、`common/schema.py` 及两项搜索测试 | 严格分页/搜索参数、服务端筛选、稳定原索引 |
| `backend/apps/jobs/models.py`、`notifications.py`、`api/notification_serializers.py`、`api/notification_views.py`、迁移 `0004`、通知/契约测试、`backend/config/urls.py` | 派生通知、单条/全部已读、水位并发与路由 |
| `backend/apps/learning/models.py`、`progress.py`、`api/progress_serializers.py`、`api/progress_views.py`、`api/urls.py`、迁移 `0003`、`tests/test_progress.py` | 课程版本记录、归属、显式状态与并发唯一性 |
| `backend/apps/explanations/tests/test_contract.py`、`contracts/openapi.yaml`、`scripts/check_contracts.py`、`scripts/test_check_contracts.py`、生成 `schema.d.ts` | 保留旧契约断言并同步 57→62，新增五操作，无删除 |
| `frontend/src/app/WorkbenchDashboard.*`、`RecentProjects.tsx`、`WorkbenchPage.test.tsx`、`WorkspaceModulePages.tsx`、`WorkspacePage.*` | 首页纯呈现与业务组合、真实资源/统计、单实例与导航回归 |
| `frontend/src/app/WorkspaceShell.*`、`ThemeProvider.*`、`global.css`、`shell-redesign.css`、`module-redesign.css` | 公共外壳、主题/对比度、响应式和面板规则 |
| `frontend/src/app/WorkspaceSearch.*`、`WorkspaceSearchBoundary.test.tsx`、`workspace-location.ts`、`job-result-location.*`、`JobResultRoutes.test.ts` | 搜索分组/取消/键盘、独立课程参数、结果归属及迟到响应 |
| `frontend/src/shared/components/WorkspaceDialog.*`、`shared/api/validation.ts` | 同树分页模态、焦点和接口特定分页过滤白名单 |
| projects/analysis 的 `api` 与 `index.ts`、`projects/SourceWorkspace.tsx`，explanations/labs 的 `index.ts` | 搜索与解析复用、源码独立筛选、保留业务边界 |
| jobs 的 `NotificationControl.*`、`api/notifications-api.*`、`JobsPage.*`、`JobsPageSelection.test.tsx`、`index.ts` | 真实通知、显式恢复、独立任务详情/焦点与结果入口 |
| learning 的 `CourseReader.*`、`CourseSummary.tsx`、`api/course-api.*`、`api/learning-api.ts`、`index.ts` | 独立课程阅读、精确版本进度、首页摘要 |
| AGENTS、README、需求、结构、前端规范、API 清单/契约规范、本计划 | 当前行为与职责同步；本节唯一维护 M25 进度和证据 |

维持 `app → features → shared`、React/Ant Design/TanStack Query/DRF 及原 History API。没有新增依赖、服务、锁文件变动、账户归属或 Worker 行为。新增五操作为通知列表、单条已读、全部已读、课程进度读取和卡片标记；工作台/示例/实验配置操作数为 62/3/7。

### 11.3 自动化回归与质量检查

先运行聚焦搜索/通知/课程及前端交互测试。最终隔离 PostgreSQL 全量后端为 **550 passed、13 warnings、181.27s**；警告来自现有多线程进程 fork。首次全量唯一失败为旧讲解契约测试仍固定 57 操作，修正为 62 并增加五个新增 ID 断言后重跑；没有弱化旧契约检查。最终前端 **42 文件、240 测试通过、254.21s**。中途两项失败是读取链/RAF 焦点未等待，保留原可见性与焦点断言补齐等待，两文件聚焦 33 项和最终全量均通过。

根目录执行固定 Python；隔离 runner 创建随机测试库/网络、禁用模型配置，完成后清理自身临时资源，不使用日常数据卷：

```powershell
$taskPython = '.runtime/m1-t02-venv/Scripts/python.exe'
& $taskPython -B -X utf8 scripts/check_v03_backend.py --docker 'C:/Program Files/Docker/Docker/resources/bin/docker.exe' --labs -- python -B -m pytest apps common tests --ds=config.settings.local -q -p no:cacheprovider --tb=short
& $taskPython -B -X utf8 scripts/check_contracts.py --node '.runtime/tools/node-v24.21.0-win-x64/node.exe'
& $taskPython -B -m unittest discover -s scripts -p test_check_contracts.py
```

完整契约检查验证三份 OpenAPI/操作清单 62/3/7、两套生成 DTO/TypeScript、工作台契约 11+37 和示例契约 11 项，退出 0。默认沙箱写临时目录曾发生 PermissionError，随后主代理明确提升运行同一检查通过；保留原失败日志，不降低检查。后端本任务 24 文件 Ruff/check/format、209 文件 Linux 平台 mypy、`makemigrations --check --dry-run --settings=config.settings.test`、spectacular validate/fail-on-warn 和脚本五项单测均通过；无迁移漂移。

前端目录执行以下命令，均退出 0；最后两次 CSS 密度修正继续通过格式、生产构建和真实浏览器，无可执行交互改动：

```powershell
$taskNode = 'F:/Program/Fall_Campus_Recruitment/.runtime/tools/node-v24.21.0-win-x64/node.exe'
& $taskNode node_modules/vitest/vitest.mjs run --configLoader native --pool threads --reporter=default --reporter=json --outputFile=../.runtime/m25-home-20261003/final-all-vitest.json
& $taskNode node_modules/typescript/bin/tsc --noEmit
& $taskNode node_modules/eslint/bin/eslint.js . --max-warnings 0
& $taskNode node_modules/prettier/bin/prettier.cjs --check .
& $taskNode tooling/generate-api-types.mjs --check
& $taskNode node_modules/vite/bin/vite.js build --configLoader native
```

最终构建 1608 模块，CSS 66.41kB、JS 1058.80kB（gzip 326.54kB）。保留超过 500kB 提示、jsdom 伪元素 getComputedStyle 提示和既有 fork 警告，不调整阈值、关闭隔离或弱化测试。

### 11.4 隔离运行与真实浏览器

唯一验收项目仍为 `learning-lab-v1-verify-8e9c1a0a0101`、入口 `http://127.0.0.1:5181`。更新脚本先检查标签、回环端口、六卷、原记录/源码摘要和模型关闭，备份旧镜像；使用独立 `m25-verify-8e9c1a0a0101` 标签，仅迁移 jobs/learning 的指定两份迁移并更新 api/worker/reconciler/frontend。没有再次加载教学内容。随后两次仅 frontend 刷新分别保存独立证据，保护其余八服务、两库全部行和原镜像标签。日常实例和原数据卷未更新或删除。

最终只读核对：原 26 表的主键、行数、行摘要均保持（迁移表仅新增指定两条，原行保持）；源码 40 文件及摘要保持，独立教学库保持，五个原服务 ID/镜像、3 网络和 6 卷保持，其他日常容器保持。新三表各 1 条，分别来自浏览器显式单条已读、全部已读水位和课程标记后撤销；总 Job 保持 11，ContextConsent/ExplanationRequest/Explanation/模型 Job 四项均 0，模型配置关闭。实时 HTML/JS/CSS/theme-init 摘要与本地 dist 一致，CSP 保留。

本机 IAB 设置值按 DPR 校准，并等待浏览器实际布局；证据中的视口均为实际 CSS 数值。72 基础组为 12 模块 × 双主题 × 1280×800、390×844、1280×480，逐页受检，无文档横纵溢出、分页入口不可见、桌面记录表横溢出或受检元素遗漏。

| 复核项 | 实际结果 |
| --- | --- |
| 1680×940 参考首页 | 深/浅色均可达；最终深色首页 1 内容页，45 个受检元素均在首页完整显示，五区域构图；全部数字/课程/项目来自实际资源 |
| 768/900/1199/1200/1600×800 | 首页、源码、任务各逐页补查；无受检遗漏；1200 双窗口 1–122/1–200 行分为 8 页，末段双窗口 6 页、247 元素可达 |
| 390×480 菜单 | 12 模块及关闭在窗口内；Shift+Tab/Tab 首尾循环、Escape 返回菜单触发按钮、扩大到 1200 解除模态 |
| 草稿与 History | 140 字符未提交项目名经分页、模块、主题、搜索/通知模态后保持，最后清空未创建；同一侧栏两模块的前进后退保留独立 course 参数 |
| 搜索 | tasks 返回 7 文件/4 接口；GET tasks 定位原 index 3；ArrowUp 显示并聚焦末项 POST，Escape 返回搜索触发；TASKBOARD 大小写匹配定位完整文件 1–265；中文项目名定位导入模块 |
| 通知 | 历史 11 未读；显式单条后 10、全部后 0，刷新仍 0；查看原系统任务及已保存结果进入系统状态，未执行新检查 |
| 课程 | 独立 course URL 无项目/接口可读；0/8→显式标记 1/8→刷新仍 1/8→撤销 0/8；未改练习或先修关系 |
| 全图与长源码 | 全图 42 节点/49 边，390×844 共 5 页、94 元素可达；固定 TaskBoard 201–265 行共 3 页、72 元素可达。早期末段加载中测量保留，不作为最终证据 |
| 完整预览 × 三尺寸 × 双主题 | 沿用 M24 已存在的合成预览，不创建新预览；7 片段/2 消息共 9 pre，26/41/57 内容页，连续区间覆盖全高度、无宽度溢出或内部纵向滚动 |
| 模型确认区 | 只本地勾选/取消；保存按钮可用但生成仍禁用，保存/提交点击 0；模型外发 0 |

服务端/组件测试另覆盖超过首批的项目/接口、局部失败、中文组合、取消/迟到响应、任务跨批详情、未知 PATCH 读取恢复、读取失败、并发窗口、版本隔离、非法 card、严格输入和已读期间新任务完成。浏览器验收库仅 4 项目/7 接口/1 发布课程，不把这些自动化边界冒称真实浏览器大数据或多版本人工试用。完整 pre 按连续可见区间和换行宽度验证，不代表逐字语义审阅或模型质量。

证据全部在忽略目录 `.runtime/m25-home-20261003`：`before.json`、`baseline/`、`backend-full-observed.json`（实际工具完成回执）、`final-all-vitest.json/.log`、`contracts-passed.log`、`final-build.log`、`runtime-updated.json`、两份 `frontend-refresh-*/status.json`、`final-runtime-review.json`、`browser-matrix.json`、`content-coverage.json`、`home-reference-final.json`、`boundary-checks.json`、`menu-check.json`、`draft-check.json`、`history-final.json`、`search-*.json`、`notifications-persistence.json`、`notification-result.json`、`course-persistence.json`、`independent-course.json`、`full-graph-mobile.json`、`long-source-end-mobile-final.json`、`dual-source-1200-end.json`、`preview-blocks-*.json`、`preview-confirmation.json`、`contrast-final.json` 和 `final-desktop*.png` / `final-mobile.png`。中途失败/加载中测量保留原始材料，最终结论只用明确 final 或最终通过结果。

### 11.5 文档与交付边界

同步 AGENTS、README、FR-25/AT-75–83、前端规范、结构、API 清单/规范和本阶段计划。当前 57→62 操作、M25 白字主色/8px 公共面板与独立课程职责经代码/Schema/浏览器核对后更新；M21–M24 历史原样保留。未指定独立记忆，不另建；临时验收材料不写入长期记忆。

交付前根目录执行固定 Python `-B -X utf8 .runtime/m25-home-20261003/verify_review_m25.py`，按 M25 初始摘要和逐份 M24 备份核对授权增量、完整差异、UTF-8、8 文档链接/锚点、指定凭据格式、依赖/锁/环境/基础设施保护、HEAD/main/索引与 diff。实际结果、精确文件清单和完整增量分别保存在 `final-review.json`、`changed-files.md`、`final-m25.diff`，与 Git 对 HEAD 的 M24+M25 总差异明确分开。

真实用户试用、真实模型输出、其他浏览器及任意未提供内容仍未验证。单用户状态未加账户归属；未来多用户需要另行迁移规划。未提交、推送、发布或更新日常实例，不启动路线图候选。浏览器视口覆盖在交付前解除，5181 隔离入口保留复核。

### 11.6 用户追加：顶栏搜索直接输入

2026-10-03 用户要求按图片采用直接输入的搜索框，取消点击后放大再输入。修改前保存既有文件副本、非敏感工程摘要和 Git 状态于 `.runtime/search-inline-20261003`，保留原 M24/M25 未提交工作。沿用 PLAN → EXECUTE → TEST → DELIVER，范围仅为搜索交互、样式、必要测试和说明；不修改后端、API、依赖、数据、现有运行容器或 Git 历史。

`WorkspaceShell.searchControl` 挂载唯一 `WorkspaceSearch`，`WorkspacePage` 继续负责已有资源归属和三类选择导航。输入始终位于顶栏，聚焦/输入后下方展开非模态结果；尺寸不随展开变化，双主题深色顶栏使用白色输入文字。结果复用 `ContentPager` 和独立记录分页，宽度限制在视口内，高度按实际输入区底边计算。Ctrl/Meta+K 聚焦，已聚焦时也可展开；上下箭头选择，Escape 收起并返回同一输入；外部点击或焦点离开收起，Tab 不困在结果内。中文组合期间不处理 Escape/方向键。200ms 防抖、200 Unicode 字符、空关键词零查询、请求取消/迟到隔离、完整文件清单和原接口 index 均保持。

以下前端命令工作目录为 `frontend`；`N` 表示固定工具 `../.runtime/tools/node-v24.21.0-win-x64/node.exe`，进程 PATH 首项为同一 Node 目录。

| 实际命令 | 观察结果 |
| --- | --- |
| `N node_modules/vitest/vitest.mjs run src/app/WorkspaceSearch.test.tsx src/app/WorkspaceSearchBoundary.test.tsx src/app/WorkspaceShell.test.tsx src/app/WorkspacePage.test.tsx --configLoader native --pool threads --reporter=default --reporter=json --outputFile=../.runtime/search-inline-20261003/vitest.json` | 4 文件、42 项通过；85.29 秒，含原工作区/草稿/导航回归 |
| `N node_modules/vitest/vitest.mjs run src/app/WorkspaceSearch.test.tsx src/app/WorkspaceSearchBoundary.test.tsx src/app/WorkspaceShell.test.tsx --configLoader native --pool threads --reporter=default --reporter=json --outputFile=../.runtime/search-inline-20261003/vitest-final.json` | 补充关闭后快捷键/点击重新展开及组合输入 Escape 断言后，3 文件、19 项通过；14.15 秒 |
| `N node_modules/typescript/bin/tsc --noEmit` | 最终通过；首次并行检查读到尚未更新的旧测试参数，测试同步后复跑通过 |
| `N node_modules/eslint/bin/eslint.js src/app/WorkspaceShell.tsx src/app/WorkspaceSearch.tsx src/app/WorkspacePage.tsx src/app/WorkspaceShell.test.tsx src/app/WorkspaceSearch.test.tsx src/app/WorkspaceSearchBoundary.test.tsx --max-warnings 0` | 通过 |
| `N node_modules/prettier/bin/prettier.cjs --check src/app/WorkspaceShell.tsx src/app/WorkspaceSearch.tsx src/app/WorkspacePage.tsx src/app/shell-redesign.css src/shared/components/WorkspaceDialog.css src/app/WorkspaceShell.test.tsx src/app/WorkspaceSearch.test.tsx src/app/WorkspaceSearchBoundary.test.tsx` | 通过 |
| `N node_modules/vite/bin/vite.js build --configLoader native` | 最终构建通过；仍提示已有大于 500 kB 的主包，不在本轮拆包 |

普通沙箱测试启动报 Windows `spawn EPERM`，在允许子进程的执行环境使用同一固定工具重跑后通过；未调整测试配置或弱化断言。jsdom 报伪元素 `getComputedStyle` 未实现提示，测试仍通过；排版以真实浏览器为依据。临时预览使用忽略目录内配置，仅代理既有 5181 的只读 API；初次代理 Host 未改写导致 403，限定临时配置改为 `changeOrigin:true` 后真实读取通过，未放宽后端保护。

浏览器实际 CSS 视口为 1398×874、971×680、379×819、379×466（工具请求 1440×900、1000×700、390×844、390×480）。四组结果面板均位于视口内，无页面横向溢出、无搜索 dialog。观察直接输入、同焦点 Ctrl+K 重新展开、上下箭头、Escape、真实 Shift+Tab 退出、窄屏导航及双主题；两主题输入文字最终均为 `rgb(255, 255, 255)`。原项目名称结果可导航，已有快照文件 `backend/apps/tasks/api/views.py` 可定位源码，已有分析 `GET /api/v1/tasks/` 保留原 `endpoint=3` 定位；全程没有创建项目、分析、模型请求或学习/通知写入。截图在浏览器工具回执中展示，测试 JSON 位于本节忽略目录。已解除浏览器视口覆盖，临时预览仅用于本轮验证。

项目未指定独立记忆文件。读取 AGENTS、README、前端规范、需求、结构及本阶段记录；同步 README、FR-25/AT-77、前端规范、结构和本节，将当前模态搜索描述改为直接输入及非模态下拉；原 M25 初始模态验收保留为历史，不覆盖其他阶段证据。真实用户试用、其他浏览器及日常容器中的更新仍未执行。

根目录实际执行 `& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 .runtime/search-inline-20261003/review.py`：本轮只修改 13 份关联工程文件，其余 545 份初始文件摘要保持，无新增非忽略工程文件；完整增量保存为 `task.diff`，`git diff --check` 通过。最终源码、测试、文档与原状态分别复核；临时预览退出，不替换既有 5181 服务。全局旧上下文曾称项目非 Git，当前 Git 状态和现行 AGENTS 已核对为有本地工程基线，以当前证据为准。

### 11.7 用户追加：重启并加载新版搜索框

2026-10-03 用户明确要求重启项目。核对当前九个运行服务、既有前端刷新脚本和 11.6 的已验证构建后，仅重建并替换唯一验收项目 `learning-lab-v1-verify-8e9c1a0a0101` 的 frontend，使 `http://127.0.0.1:5181` 加载直接输入搜索框；单纯重启旧镜像不能加载源码改动。其他八服务、后端迁移和数据不在本次重启范围。

根目录实际执行 `& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 '.runtime/m25-home-20261003/refresh_frontend.py' --execute`，退出 0。独立证据目录 `.runtime/m25-home-20261003/frontend-refresh-20261003T082912683157Z` 的 `status.json` 为 passed：仅 frontend 替换，其他八服务 ID/镜像、两库全部记录、迁移、导入源码、网络、六卷和受保护镜像标签保持，模型配置继续关闭。实时 HTML、`theme-init.js`、`index-S-HO-hAh.js`、`index-vH5nXGob.css` 与 11.6 的本地 dist 字节一致，CSP 保留。

真实浏览器访问 5181 后，顶栏直接输入“用户视角”返回既有项目；页面只有一个搜索输入、没有搜索 dialog，下拉结果展开，Escape 收起后焦点仍在同一输入。仅执行页面读取与搜索，没有项目、任务、模型、通知或学习记录写入。本次沿用 11.6 的源码测试，未重复运行不受运行刷新影响的单元测试；不将运行刷新推广为真实用户试用或其他浏览器兼容验收。长期行为说明与源码未再改动，仅在本阶段计划补充运行状态和验证记录。

### 11.8 用户追加：输入后匹配，空输入隐藏

2026-10-03 用户追加两张搜索参考图，要求输入后匹配相应结果，未输入时不显示下拉。本轮以 11.7 后的工程状态保存八份相关文件副本和 558 份非敏感工程摘要于 `.runtime/search-keyword-20261003`；范围为搜索组件、两份搜索测试及五份相关说明。沿用现有查询、分页、导航和视觉，不增加热度数据、外部搜索、接口或依赖。

`WorkspaceSearch` 使用当前关键词非空、组合输入结束及防抖 query 与当前输入一致的条件控制下拉、aria-expanded、请求启用和取消。空值或纯空白时聚焦、点击、Ctrl/Meta+K、上下箭头不展开；输入完成 200ms 防抖后显示当前词对应结果，清空立即隐藏并取消请求，换词期间不显示旧词结果。移除空输入提示面板。外部 pointerdown 继续按 open 监听，防止防抖期间点击离开后延迟弹出；高度测量按实际展开状态执行。中文组合、Unicode 上限、局部失败、原接口索引和分组分页保持。

以下实际命令工作目录为 `frontend`，`N` 仍为固定 Node `../.runtime/tools/node-v24.21.0-win-x64/node.exe`；Vitest 和构建进程 PATH 首项为同一 Node 目录。

| 实际命令 | 观察结果 |
| --- | --- |
| `N node_modules/vitest/vitest.mjs run src/app/WorkspaceSearch.test.tsx src/app/WorkspaceSearchBoundary.test.tsx src/app/WorkspaceShell.test.tsx src/app/WorkspacePage.test.tsx --configLoader native --pool threads --reporter=default --reporter=json --outputFile=../.runtime/search-keyword-20261003/vitest.json` | 4 文件、46 项通过，87.53 秒；保留工作区草稿、模块及导航回归 |
| `N node_modules/vitest/vitest.mjs run src/app/WorkspaceSearch.test.tsx src/app/WorkspaceSearchBoundary.test.tsx src/app/WorkspaceShell.test.tsx --configLoader native --pool threads --reporter=default --reporter=json --outputFile=../.runtime/search-keyword-20261003/vitest-final.json` | 外部点击修正和防抖边界断言后，3 文件、24 项通过，16.24 秒 |
| `N node_modules/typescript/bin/tsc --noEmit` | 首轮及最终均通过 |
| `N node_modules/eslint/bin/eslint.js src/app/WorkspaceSearch.tsx src/app/WorkspaceSearch.test.tsx src/app/WorkspaceSearchBoundary.test.tsx --max-warnings 0` | 首轮及最终均通过 |
| `N node_modules/prettier/bin/prettier.cjs --check src/app/WorkspaceSearch.tsx src/app/WorkspaceSearch.test.tsx src/app/WorkspaceSearchBoundary.test.tsx` | 首轮及最终均通过；仅三份改动代码文件执行格式写入 |
| `N node_modules/vite/bin/vite.js build --configLoader native` | 首轮及最终均通过；最终 1608 模块，CSS 66.88kB、JS 1059.71kB（gzip 326.76kB） |

首轮 jsdom 仍提示伪元素 getComputedStyle 未实现，最终构建仍提示已有大于 500kB 的主包；不修改测试配置、隔离或阈值。本轮没有失败的源码检查，排版及显示状态另以真实浏览器核对。

沿用用户在 11.7 的本地重启授权，根目录实际执行 `& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 '.runtime/m25-home-20261003/refresh_frontend.py' --execute`，退出 0；独立证据目录 `.runtime/m25-home-20261003/frontend-refresh-20261003T083841480456Z/status.json` 为 passed。仅 frontend 更新，其余八服务、两库全部记录、迁移、导入源码、网络、六卷和受保护标签保持，模型配置继续关闭。实时 HTML、theme-init、`index-B5rGQAA3.js` 和 CSS 与本地最终 dist 字节一致，CSP 保留。

真实浏览器直接访问 5181，空框聚焦、Ctrl+K 和 ArrowDown 后没有下拉；输入“用户视角”显示既有匹配项目。清空立即观察到 panelCount=0、aria-expanded=false 且输入焦点保持；纯空白后 Ctrl+K 仍无面板或 dialog。没有创建项目、任务、模型请求或通知/学习写入。源码测试覆盖中文组合、空白、清空取消两路 GET、迟到响应和防抖期间外部点击，浏览器检查不冒称其他浏览器或真实用户试用验收。

未指定独立项目记忆文件。读取现行 AGENTS、README、前端规范、需求、结构和本阶段计划；同步五份相关说明，将当前“聚焦即展开”规则改为有效关键词匹配后展开，11.6/11.7 保留为历史。完整本轮增量及既有工程保护结果由根目录固定 Python 执行 `.runtime/search-keyword-20261003/review.py`，保存至 `task.diff` 和 `final-review.json`；不建立新的长期记忆系统或执行 Git 提交。

### 11.9 用户浏览器批注：搜索提示、焦点和浅色顶栏

2026-10-03 用户要求修复三处浏览器批注：去掉搜索框 Ctrl K 提示、点击输入后的内部蓝框，以及浅色模式顶栏仍为深色。修改前在 `.runtime/header-polish-20261003` 保存七份相关文件副本、558 份非敏感工程摘要与 Git 状态。浏览器确认原输入内部 outline 为蓝色 solid，切换后的根主题已为 light，但顶栏仍为深色渐变和白字；ThemeProvider 的切换逻辑正常，根因为外壳颜色固定和全局 focus-visible 样式继承。

实际全局搜索和外壳回退搜索均移除 kbd 提示，Ctrl/Meta+K 功能继续保留。`shell-redesign.css` 仅覆盖顶栏搜索 input 的 outline/box-shadow，整个搜索框通过 focus-within 改变边框颜色，结果按钮及其他表单控件继续沿用全局焦点规则。顶栏颜色由原深色变量和浅色覆盖维护，搜索背景、文字、辅助文字、导航选中/悬停、状态点及按钮悬停同步使用变量；深色原配色保持。未修改 ThemeProvider、持久化、搜索查询、分页或接口。

以下实际命令工作目录为 `frontend`，`N` 表示固定 Node `../.runtime/tools/node-v24.21.0-win-x64/node.exe`；Vitest 和构建 PATH 首项为同一 Node 目录。

| 实际命令 | 观察结果 |
| --- | --- |
| `N node_modules/vitest/vitest.mjs run src/app/WorkspaceSearch.test.tsx src/app/WorkspaceSearchBoundary.test.tsx src/app/WorkspaceShell.test.tsx src/app/ThemeProvider.test.tsx --configLoader native --pool threads --reporter=default --reporter=json --outputFile=../.runtime/header-polish-20261003/vitest.json` | 4 文件、29 项通过，19.91 秒；提示移除断言及既有搜索/外壳/主题回归保持 |
| `N node_modules/typescript/bin/tsc --noEmit` | 通过 |
| `N node_modules/eslint/bin/eslint.js src/app/WorkspaceSearch.tsx src/app/WorkspaceShell.tsx src/app/WorkspaceSearch.test.tsx src/app/WorkspaceShell.test.tsx --max-warnings 0` | 通过 |
| `N node_modules/prettier/bin/prettier.cjs --check src/app/WorkspaceSearch.tsx src/app/WorkspaceShell.tsx src/app/shell-redesign.css src/app/WorkspaceSearch.test.tsx src/app/WorkspaceShell.test.tsx` | 通过，没有执行格式写入 |
| `N node_modules/vite/bin/vite.js build --configLoader native` | 通过；1608 模块，CSS 67.41kB、JS 1059.64kB（gzip 326.74kB）；保留既有大于 500kB 主包提示 |

沿用既有本地重启授权，根目录执行 `& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 '.runtime/m25-home-20261003/refresh_frontend.py' --execute`，退出 0。`.runtime/m25-home-20261003/frontend-refresh-20261003T085129506100Z/status.json` 为 passed：仅 frontend 更新，其他八服务、两库全部记录、迁移、导入源码、网络、六卷和受保护标签保持，模型配置关闭。实时 HTML、theme-init、`index-Duy_LhlB.js` 和 `index-Cu5w68yy.css` 与本地构建字节一致，CSP 保留。

真实浏览器在实际 CSS 视口 1243×699 重新加载 5181 后，搜索提示计数为 0；两主题鼠标聚焦、浅色 Tab 和 Ctrl+K 后输入内部 outlineStyle=none、boxShadow=none，焦点仍为同一搜索输入。深色整体搜索边框为 rgb(169,185,210)，浅色为 rgb(89,89,89)。浅色顶栏白底 rgb(255,255,255)、输入深色 rgb(38,38,38)、搜索底色 rgb(245,247,250)、选中导航底色 rgb(230,244,255)，刷新后保持；深色顶栏恢复原渐变。两主题无页面横向溢出。输入“用户视角”仍返回既有匹配项目，清空立即隐藏；仅进行读取、搜索和主题切换，没有业务写入。浅色截图在浏览器工具回执展示，已恢复验证前深色偏好。

未发现独立项目记忆文件。读取现行 AGENTS、README、需求、结构、前端规范和本阶段记录，更新前端规范及本节；11.6 的两主题深色顶栏验收保留为历史，以本节的随主题配色作为当前规则。核对代码、测试及实际计算样式后解决该说明差异，不修改其他阶段或新建长期记忆系统。工程增量和保护检查由根目录固定 Python 执行 `.runtime/header-polish-20261003/review.py`，保存 `task.diff` 和 `final-review.json`；真实用户试用及其他浏览器兼容不由本次检查替代。


<a id="m26"></a>
## 12. M26 补齐三条主线、精简教学扩展

### 12.1 授权、范围与工程保护

2026-10-03 用户明确要求 IMPLEMENT 已确定计划。当前只实现项目管理→统一工作区→操作日志，以及ZIP/目录导入、自动扫描/根发现、独立知识、共享接口图、按确认生成模型讲解、内部永久删除和退役历史兼容。保留React/DRF/Celery/PostgreSQL，不引入新服务或状态框架。范围不包含真实模型调用、已有实例更新、Git写操作或远程发布。

实施前只读核对AGENTS、长期文档、实际源码/调用路径、测试、配置和Git状态。在忽略的.runtime/m26-mainline-20261003保存557份非敏感工程文件副本、SHA256清单及Git状态；保留M24/M25等既有未提交工作。没有读取完整秘密文件或建立新记忆系统。

### 12.2 实现与主要取舍

- jobs独立OperationLog及历史任务摘要回填、稳定错误/阶段/重放事件；common集中退休写/任务执行与资源隔离；保留历史模型和必要GET。
- projects目录清单/前后端路径预算、确定性内部归档、持久来源及同限额重试；analysis独立SourceScan/SnapshotPreparation，扫描/分析关联事务后投递。根发现不运行设置，只有多根要求选择。
- learning真实AST/包声明扫描与版本卡片，packaging26.3直接依赖；未知事实未映射，知识不依赖接口成功。共享接口图按源码位置建立符号hub，无向遍历，保留原代码依赖方向和明确截断。
- MainlineWorkspace三入口、联动源码/面板、双主题/分页/URL/草稿；退役URL解释原功能。讲解模板1.1.0注入实际保留范围知识，旧确认失效、旧结果可读。
- DeletionRequest持久内部清单与阶段/尝试，删除事务按Project→Snapshot→DeletionRequest→Job锁顺序，其他发布按Project→Snapshot→Job；先清理内部文件再依赖数据库结果，失败保持隔离可继续。比较整条清理保留另一侧，原ZIP/目录、全局卡片与其他项目保护。
- 75项契约包含历史退休入口；增量迁移不drop旧表/不重算旧结果。README、AGENTS、需求/结构/API及前后端规范同步，当前Git“未初始化”说明按实际main状态修正。

### 12.3 最终验证记录

M26 工程实施与下列参考环境验证完成。验证不更新已有 5181/默认实例，不调用真实模型，不执行 Git 写操作。以下命令实际执行并观察退出 0；`P` 为根目录 `.runtime/m1-t02-venv/Scripts/python.exe`，`N` 为 `.runtime/tools/node-v24.21.0-win-x64/node.exe`，`D` 为 `C:/Program Files/Docker/Docker/resources/bin/docker.exe`。前端命令在 `frontend` 执行并使用 `../` 工具路径；后端静态命令在 `backend` 执行。

| 实际命令或检查 | 最终观察结果 |
| --- | --- |
| 根目录 `P -B -X utf8 scripts/check_v03_backend.py --docker D -- python -B -m pytest apps common tests --ds=config.settings.local -q -p no:cacheprovider --tb=short` | 隔离 Linux/PostgreSQL 完整回归 **639 passed，188.91s**；独立随机资源清理完成，含删除/日志/历史 GET 隔离、真实解析子进程及退役队列防护 |
| `N node_modules/vitest/vitest.mjs run --configLoader native --pool threads` | 前端完整 **45 文件、253 passed，270.43s**；此前默认配置同样 253 passed，258.19s |
| `N node_modules/vitest/vitest.mjs run src/app/WorkspacePage.test.tsx src/features/analysis/GraphDiagram.test.tsx src/features/projects/MainlineProjects.test.tsx src/features/learning/SnapshotKnowledge.test.tsx --configLoader native --pool threads` | 最终分页高度修正后 **4 文件、24 passed，17.49s** |
| `N node_modules/typescript/bin/tsc --noEmit`；`N node_modules/eslint/bin/eslint.js . --max-warnings 0` | 完整类型与 lint 通过；类型同时由最终契约检查执行 |
| `N node_modules/vite/bin/vite.js build` | 最终生产构建通过，1596 模块，CSS 66.01kB、JS 967.35kB/gzip305.22kB；保留已有大于500kB提示 |
| 根目录 `P -B -X utf8 scripts/check_contracts.py --node .runtime/tools/node-v24.21.0-win-x64/node.exe` | 三份服务契约、75/3/7项操作表及两套生成类型一致；11+37+11项无业务数据库契约测试通过 |
| `P -B -m ruff check config common apps tests` 与 `P -B -m ruff format --check config common apps tests` | 241 文件通过，没有批量格式写入 |
| `$env:MYPYPATH='F:\Program\Fall_Campus_Recruitment\scripts'; P -B -m mypy config common apps tests --platform linux --no-incremental` | **241源文件无错误**；既有脚本导入使用明确搜索路径 |
| `P -B manage.py check --settings=config.settings.test`；`P -B manage.py makemigrations --check --dry-run --settings=config.settings.test` | 系统检查无问题，没有待生成迁移 |
| 根目录 `P -B -m pytest scripts/test_check_m26_workspace.py scripts/test_check_contracts.py -q -p no:cacheprovider` | **17 passed、4 subtests passed**，含11项生命周期资源归属/state防护及6项契约脚本检查 |
| 根目录 `P -B -X utf8 .runtime/m26-mainline-20261003/verify_http_flow.py` | 最终 API 加载稳定代码后，真实 HTTP/Linux Worker **10项检查 passed**；自身随机项目完整清理 |

根目录实际执行 `P -B -m ruff check scripts/check_m26_workspace.py scripts/test_check_m26_workspace.py scripts/check_contracts.py scripts/test_check_contracts.py` 和 `P -B -m mypy scripts/check_m26_workspace.py scripts/test_check_m26_workspace.py --strict --no-incremental`，四份脚本 lint 和两份生命周期脚本严格类型检查通过。前端读取 `.runtime/m26-mainline-20261003/frontend-paths.json` 的43个本轮增量路径，实际执行 `N node_modules/prettier/bin/prettier.cjs --check @m26Paths`，观察全部符合格式。

根目录实际执行 `P -B -X utf8 .runtime/m26-mainline-20261003/review.py`：557份非敏感基线备份摘要正确，本轮修改120份、新增52份、无删除，其余437份基线字节不变；新增12个本地文档目标存在，指定凭据格式扫描无命中，`git diff --check`通过，HEAD/main与零远程保持。逐文件用途、完整增量和最终状态见忽略目录 `.runtime/m26-mainline-20261003/changed-files.md`、`task.diff`、`final-review.json`。记录不把既有M24/M25工作算成本轮新增。资源清理后实际执行 `P -B -X utf8 scripts/check_m26_workspace.py status --docker D`，观察 `stopped`；状态清单保留用于归属审计。

真实 HTTP 检查验证：原 ZIP 与原示例目录本次上传的9个源码文件摘要一致、7接口；唯一根自动ready、多根needs_root后选根ready、无根no_root仍有2知识卡；主动重扫/同键重放/当前扫描分析关联/旧结果读取；3接口经共享符号形成4节点3连接；超AST限额扫描真实失败，显式重试同输入仍失败，保留快照；错误删除摘要409不改资源，确认后项目和快照异步清理、隔离/删除读取410或404、同键重放200；失败/拒绝/重放日志及删除摘要保留。原ZIP完整SHA及原目录上传9文件聚合SHA前后不变。日志具体数量和 UUID 以 `http-flow-result.json` 为准，不保存凭据或csrf。

真实浏览器在独立5185验证 ZIP 项目名自动带出、导入后不手选根即自动进入9文件工作区、刷新保留对象、7接口与源码依据、当前接口知识筛选/卡片版本/命中定位、紧凑共享图与展开图、桌面源码对照、窄屏页签、两主题、内容翻页、导航Escape关闭后焦点恢复。删除预览未勾选时禁用，提交本轮一次性测试项目后成功清除项目/快照/文件URL上下文，4条原导入/扫描/分析/删除日志显示结果已删除，详情阶段和任务摘要保持可读。合法旧课程URL显示退役说明，不改写到无关页面。浏览器控制台未见 error。实际CSS桌面约1398像素、窄屏379×819，未见页面横向溢出；最终窄屏分页底部约770.68像素，处于可视区域。

浏览器自动化的目录chooser调用未取得文件选择成功结果，不能宣称原生目录选择已通过真实浏览器验收；目录清单组件测试及真实 HTTP/Worker 一致性和限额已通过。截图保存在同证据目录 `browser-workspace.png`、`browser-deleted-log.png`、`browser-narrow-final.png`。主题和临时视口已恢复，临时浏览器已关闭，独立栈的本次标签容器/网络/源码卷由生命周期stop清理；不移除已有实例资源。

失败轮与修复保留：首轮完整回归27失败/592通过，主要为退役入口旧夹具、迁移测试旧模型/恢复目标及无数据库传输测试的审计边界；次轮4失败/629通过为测试patch引用已删除服务导入，改监测实际底层解析器且保留零执行断言；后续1失败/634通过由ZIP夹具隐式当前时间戳跨两秒造成字节变化，受控时钟实际复现后固定夹具时间，原相同字节重放/不同字节冲突断言和产品实现保持。最后639项全通过。新read层身份/装饰器/历史删除隔离聚焦70通过；清理审阅后的评审/对比26通过；导入/归档并发49通过。Windows默认沙箱曾spawn EPERM，解除进程限制后同一测试通过；Ruff限定格式与新测试类型错误已修复，未弱化检查。保留既有jsdom伪元素和Python多线程fork警告，不将其描述成兼容或压力测试证据。

### 12.4 记忆一致性、取舍和限制

未发现独立项目记忆文件。读过AGENTS、README、需求、四阶段计划、结构、API清单/协议、前后端规范及本轮相关演示/试用/路线说明。同步当前三入口、退役范围、源码扫描/准备状态、知识身份/命中、模型知识版本、内部清理隔离与日志以及75项契约；结构文档旧“未初始化Git”经实际main和Git状态核对修正。M1–M25历史证据保留并明确历史范围，本轮进度只在M26维护，不写中央记忆或建立新进度系统。

主要取舍：保持静态源码依据，接口通过共享符号hub关联，不猜业务执行顺序；知识read先从全快照完整import事实确定同名包身份，再过滤命中位置，身份冲突unknown，同名本地模块不误配第三方卡。未知装饰器使用已存owner_ref定位到相应接口，模型仍只取最终保留snippet交集。删除隔离同时覆盖现行及保留的历史作答/路径/复习读取，原记录直到文件清理成功才清理。历史表保留而执行器/写入口退役，避免未删除旧数据失效。

手工复核点：导入后选择一个接口，点其知识/关系依据，应定位准确源码行；删除该一次性测试快照后，日志仍显示对象名称和结果已删除，原ZIP/目录摘要保持原样。

静态规则不覆盖所有动态URL/业务关系。未调用真实模型、未运行真人试用、未升级现有实例、未验证其他浏览器或全新宿主安装；长时间I/O、进程硬杀与导入/分析/删除全部交错未做压力实测。扫描失败的重试验证是同样无效输入继续明确失败，不冒称瞬态故障恢复成功。代理提前拒绝、浏览器未提交、数据库不可用时仍不能保证可靠应用日志。本轮工程验收不扩展上述边界。

### 12.5 用户授权重启5181试用实例

2026-10-03 用户追加“重启项目，我来进行核对和试用”，明确授权将本轮代码加载到现有本地实例。按实际容器标签、回环端口、原四层Compose配置和Git状态核对，目标仍为 `learning-lab-v1-verify-8e9c1a0a0101`、`http://127.0.0.1:5181/`；原前后端是M25镜像，普通restart不能加载M26。执行前给出保留数据、先备份再迁移及仅更新主服务的计划，未读取根.env或复制凭据卷。

根目录使用固定 `P`（同12.3）实际执行忽略目录 `.runtime/m26-restart-20261003/restart.py` 的 `prepare`、`build-cached`、`update`、`verify`，均显式指定本机Docker路径。prepare保存29表原列逐行摘要、原容器/镜像、6卷3网、60个内部源码/发布标记对象摘要及无活动Job基线。最初标准后端构建停留在重复下载锁定依赖，按本轮PID、父进程和唯一M26标签核对后主动中止，保留构建历史；随后逐一验证现有Linux镜像49项依赖集合与锁完全相同（Linux不装Windows条件colorama），复用旧镜像的已安装依赖层，仅载入当前backend/content，新前端仍按现有Dockerfile构建。原镜像标签不变，新标签为 `learning-lab-backend:m26-verify-8e9c1a0a0101` 与同名frontend标签；不升级依赖或安装全局工具。

迁移前停止同项目frontend/api/worker/reconciler和已退役的task-board-api/lab-reconciler，数据库/Redis进程及卷保持。旧教学会话未结束数量为0。以pg_dump自定义格式保存 `.runtime/m26-restart-20261003/database-before.dump`，150698字节，pg_restore目录可读取；不输出数据内容或复制秘密卷。实际 `python manage.py migrate --noinput` 四项均OK：projects0003、analysis0006、jobs0005、jobs0006；`load_learning_content`观察29张卡片，保留旧卡。Compose仅以 `up -d --no-deps --no-build --pull never --wait --wait-timeout 90 api worker reconciler frontend` 替换四个主服务，保留原PG/Redis/教学PG容器，旧教学执行容器保留但停止。

首次更新后的保护核查沿用旧工具“九服务均运行”的前提，将主动停用的教学API误报为缺失；没有重复执行迁移或启停。将本轮检查限定为四个活动主服务、按原标签核对两个已停止教学容器后，单独verify退出0。原29表所有旧列记录摘要保持（仅迁移表和KnowledgeCard允许新增），5项目、6快照、18任务保持；原源码60对象摘要、教学库全部记录、6卷3网以及其他实例容器保持。必要历史日志回填18条，模型配置保持关闭。

根目录实际 `P -B -X utf8 .runtime/m26-restart-20261003/verify_runtime.py --docker D` 退出0：项目/任务/操作日志/知识接口均HTTP200，计数分别5/18/18/29；Celery inspect ping返回pong，源码导入/扫描/分析/删除任务已注册；旧实验等任务名仅保留拒绝消息处理，不能执行业务。`manage.py check`无问题，`migrate --plan`无待执行迁移。实时HTML/JS/CSS/theme-init与本地已验证dist字节一致、CSP保留。对存量元数据的一次辅助读取因Windows默认GBK解码失败，使用既定 `-X utf8` 重跑退出0，未影响实例。

真实浏览器打开5181确认三个入口、ZIP/目录导入和五个原项目，新版页面控制台无error；只做页面读取，没有新增导入、删除或模型调用。页面已保留供用户试用，截图 `browser-ready.png`、基线/备份/迁移日志/保护结果/HTTP与Worker核查分别位于本轮忽略目录；运行结果以 `status.json` 和 `readiness.json` 为准。用户实际试用结论仍待用户反馈，模型配置仍关闭；已有快照不自动回填扫描，可在工作区显式重新识别。

同步检查只更新本节运行状态：读取AGENTS、README、Compose、当前迁移和内容加载实现及既有更新材料，没有业务源码或公共协议变化，不修改其他长期规范或建立记忆系统。12.3/12.4的“未更新现有实例”为本次追加授权之前的工程验收边界，保留为历史。本轮不执行Git写操作或远程发布。

### 12.6 追加：操作日志表格与四列筛选

2026-10-03 用户要求将操作日志改为表格，并在操作类型、结果、开始时间、结束时间四列进行筛选。实施前读取当前指令、API/前端规范和M26记录，核对源码与Git状态；在 `.runtime/operation-log-table-20261003` 保存当前相关文件基线，保护已有M24–M26修改。范围仅含日志读取API、表格/筛选、现有分页的portal焦点边界、生成契约、直接测试及规范同步，无模型、迁移、依赖或审计写逻辑改变。

表格保留对象/项目、稳定错误、结果已删除提示、日志详情、任务摘要及两级分页；四个列头打开独立筛选面板，两种时间各有可单端的起止范围，应用后重置批次和详情，支持单列清除与全部清除。窄屏仍为表格，通过内部横向滚动阅读；溢出时顶部横向位置滑杆让首内容页即可移动到右侧列。筛选弹层每次打开聚焦首控件，Escape和应用/清除后焦点回到筛选按钮，隐藏后销毁内容。ContentPager增加contains边界，portal焦点不改变正文内容页。去除被替代的日志列表布局样式，不调整其他业务模块。

查证原“结束时间”控件实际查询 `started_before`，只过滤创建时间上界。本轮保留旧字段/参数，新增 `started_at=created_at`（应用接收时间）、可空 `ended_at`（首次可靠终态审计时间）与 `ended_after/ended_before`。结束时间由已有事件在PostgreSQL查询层派生，再组合过滤、计数和分页；非终态/缺可靠事件为null，HTTP重放用本次首次response、内部重放用自身replayed，不能借用会改变的updated_at或原任务后续完成事件。历史legacy时间为摘要观测，损坏事件读取安全归一化但不回写，列表与详情GET零写。

日志列表在OperationLogsView.initial中先有界解析GET查询，允许完整组合筛选的9个字段及最多4096字符，再执行严格字段、重复值和时间校验；超限/非法输入返回400。该例外只影响日志列表，其他端点原全局5字段限制不变。

本轮实际执行（工具别名P/N/D同12.3）：

| 工作目录与命令 | 观察结果 |
| --- | --- |
| 根目录 `P -B -X utf8 scripts/check_v03_backend.py --docker D -- python -B -m pytest apps/jobs/tests/test_operation_audit.py apps/jobs/tests/test_operation_times.py --ds=config.settings.local -q -p no:cacheprovider --tb=short` | 隔离PG17.9 **56 passed，3.87s**，覆盖运行中空值、首次终态、重放稳定、坏JSON、含边界/时区/反序/重复参数、完整9字段组合及查询超限、分页前筛选、历史删除摘要及GET零写；临时资源清理完成 |
| frontend `N node_modules/vitest/vitest.mjs run src/features/jobs/OperationLogs.test.tsx src/shared/components/ContentPager.test.tsx src/app/WorkspacePage.test.tsx src/shared/components/RecordList.test.tsx --configLoader native --pool threads` | **4文件27项通过，14.89s**，验证四列组合请求、批次复位/条件保留、单端时间、反序零请求、清除、详情、横向位置控制、键盘焦点和portal焦点不改变内容页；DOM测试不替代真实布局验收 |
| frontend `N node_modules/typescript/bin/tsc --noEmit`；`N node_modules/eslint/bin/eslint.js . --max-warnings 0`；`N node_modules/prettier/bin/prettier.cjs --check src/features/jobs/OperationLogs.tsx src/features/jobs/OperationLogFilters.tsx src/features/jobs/OperationLogs.test.tsx src/features/jobs/OperationLogs.css src/app/mainline.css src/shared/components/ContentPager.tsx src/shared/components/ContentPager.test.tsx` | 均退出0 |
| backend `P -B -m ruff check apps/jobs/operation_times.py apps/jobs/api/operation_views.py apps/jobs/api/operation_serializers.py apps/jobs/tests/test_operation_times.py`；`P -B -m ruff format --check apps/jobs/operation_times.py apps/jobs/api/operation_views.py apps/jobs/api/operation_serializers.py apps/jobs/tests/test_operation_times.py`；`$env:MYPYPATH='F:/Program/Fall_Campus_Recruitment/scripts'; P -B -m mypy apps/jobs/operation_times.py apps/jobs/api/operation_views.py apps/jobs/api/operation_serializers.py apps/jobs/tests/test_operation_times.py --platform linux --no-incremental` | 均通过 |
| backend `P -B manage.py spectacular --settings=config.settings.test --file ../contracts/openapi.yaml --validate --fail-on-warn`；frontend `N tooling/generate-api-types.mjs`；根目录 `P -B -X utf8 scripts/check_contracts.py --node N` | 75/3/7契约与清单、59项契约测试、两套生成DTO/类型均通过 |
| backend `P -B manage.py makemigrations --check --dry-run --settings=config.settings.test`；frontend `N node_modules/vite/bin/vite.js build` | 无迁移漂移，构建退出0；保留现有大于500kB的bundle提示，不扩大到全局拆包 |

中间检查如实保留：前端首次测试缺jsdom ResizeObserver，新测试按已有测试环境边界补替身并由真实浏览器补布局检查；测试误用exact查询选项和新增全角空格分别由类型/lint发现并修正。首次后端Ruff要求UTC写法，修正新测试；默认Docker、契约临时文件及Vite子进程遇Windows沙箱权限限制，同命令提升权限后通过。首次导出命令相对工具路径错误，更正工作目录相对路径后通过。未弱化断言或安全检查。

沿用用户“重启项目，我来核对和试用”的授权，根目录实际执行 `P -B -X utf8 .runtime/operation-log-table-20261003/update_runtime.py restore --docker D`、`prepare --docker D`、`build --docker D`，均退出0。检查时原实例服务已停止，restore只启动原PG/Redis/Worker/reconciler容器，保留其身份及镜像，旧教学服务继续停止。prepare逐一核对原Linux镜像49项依赖与锁一致，backend只复制本轮源码，frontend使用原Dockerfile；不执行迁移、内容加载或模型调用。

第一轮 `update_runtime.py update --docker D --checks-passed` 在服务就绪与原数据保护核对通过后，由真实HTTP组合筛选发现6个查询字段触发全局5字段限制，退出1，没有报告完成；真实窄屏检查还发现原bottomLeft弹层会翻到bottomRight并越出左侧。分别限定日志GET查询预算并补8项测试、改为可横向避让的bottom定位后，复验56/27项、静态检查、契约与构建全部通过。新修复脚本 `P -B -X utf8 .runtime/operation-log-table-20261003/repair_api.py prepare --docker D`、`build --docker D --checks-passed`、`update --docker D --checks-passed` 均退出0；仅重新替换api/frontend，第一轮计划、镜像及失败证据保留。新增mypy检查中QueryDict与Django stub类型不匹配，保持不可变查询并通过setattr更新请求缓存后检查通过。

最终运行证据 `repair-updated.json` 确认：所有原业务表记录及内部源码60对象摘要、6卷3网、原依赖及教学容器、其他实例保持，模型配置关闭；18条原日志均可读取开始/结束时间，列表与详情时间一致，四列组合、独立结束范围、全部9参数和5组非法查询检查通过。实时HTML/JS/CSS/theme-init与最终dist字节一致，CSP保持。API/frontend使用新的 `log-table-repair-20261003142716-c70106` 唯一标签，旧标签未改写。

真实浏览器在5181的操作日志页验证：四列条件同时生效，源码导入/成功及当天两个时间范围返回2条记录；结束范围反序显示“时间上界不能早于下界。”；单列清除保留其他三个条件，日志详情仍可读，全部清除恢复18条并关闭旧详情。实际桌面宽1243px、窄屏宽379px均无页面横向溢出；窄屏顶部滑杆可移到右侧结束时间列，弹层左右边界约77/367px，首日期控件聚焦、内容页保持第1页，Escape返回触发按钮。日期控件的自动fill只更新DOM，核验使用原生键盘事件提交，未修改产品事件逻辑。页面控制台error为0，窗口已恢复，试用页保留；截图与结构化记录为 `browser-desktop.png`、`browser-mobile.png`、`browser-proof.json`，均在本轮忽略目录。

项目记忆同步只更新API规范、前端规范和本节。核对发现前端规范页头仍写旧四分类/12模块，按M26当前三入口实现修正；未创建独立记忆文件或修改中央记忆。已有用户修改保持，本轮无Git写操作。上述运行与浏览器检查只包含读取/筛选，不新增导入、删除或真实模型任务；用户试用结论仍由用户反馈，不用工程检查替代。

### 12.7 追加：日志固定编号与名称搜索

用户明确选择日志页顶部独立搜索框，匹配操作类型、操作对象和项目名称，并授权实施固定数字编号、增量迁移与5181更新。本轮实施、聚焦验证、原数据保护与最终桌面/窄屏浏览器验收已完成，5181已加载最终版本。本轮在 `.runtime/operation-log-search-20261003` 保存17份相关文件字节基线及当前237项已有Git状态；保护上轮表格与其他既有修改，无Git写操作。

实施范围：jobs日志模型、新增迁移及读取API；日志页面/外壳调用与直接测试；生成契约/类型；API清单、API/前后端规范及本节。原UUID主键、审计响应头和详情路径保持；display_id为全项目固定唯一安全整数，原列不变，数据库默认值兼容旧写入口，失败事务允许跳号不复用。q按类型中文名称/代码、对象及保存的项目名称OR匹配，与原列筛选AND，计数分页前处理；默认全项目、不保留隐式项目筛选。

本轮实际执行（工具别名P/N/D同12.3）：

| 工作目录与命令 | 观察结果 |
| --- | --- |
| 根目录 `P -B -X utf8 scripts/check_v03_backend.py --docker D -- python -B -m pytest apps/jobs/tests/test_operation_audit.py apps/jobs/tests/test_operation_times.py apps/jobs/tests/test_operation_display_ids.py apps/jobs/tests/test_operation_search.py --ds=config.settings.local -q -p no:cacheprovider --tb=short` | 最终隔离PG17.9 **95 passed，6.94s**，临时资源清理完成。覆盖空/旧数据确定性迁移、原列保持、旧模型/SQL/ORM赋号、20次并发、事务跳号、最大安全整数、唯一约束、迁移中途失败原子回滚与重试，以及名称/类型/代码/已删除项目搜索、分页、完整10参数、Unicode/重复/NUL和GET零写 |
| frontend `N node_modules/vitest/vitest.mjs run src/features/jobs/OperationLogs.test.tsx src/app/WorkspacePage.test.tsx --configLoader native --pool threads` | 最终 **26 passed，11.99s**，覆盖固定编号、默认全项目、四列组合/分页/清除、200ms防抖、IME、Unicode200、取消与迟到响应、非法编号及原详情/键盘功能 |
| backend `P -B -m mypy apps/jobs/models.py apps/jobs/api/operation_views.py apps/jobs/api/operation_serializers.py apps/jobs/migrations/0007_operationlog_display_id.py apps/jobs/tests/test_operation_display_ids.py apps/jobs/tests/test_operation_search.py apps/jobs/tests/test_operation_times.py --platform linux --no-incremental`（MYPYPATH指向根目录scripts）；相同7文件 `P -B -m ruff check` 与 `P -B -m ruff format --check` | 类型、lint、格式均通过；`P -B manage.py check --settings=config.settings.test` 无问题，`P -B manage.py makemigrations --check --dry-run --settings=config.settings.test` 无漂移 |
| backend `P -B manage.py spectacular --settings=config.settings.test --file ../contracts/openapi.yaml --validate --fail-on-warn`；frontend `N tooling/generate-api-types.mjs`；根目录 `P -B -X utf8 scripts/check_contracts.py --node N` | 导出与生成退出0；最终源码的75/3/7契约、清单、59项契约测试及两套生成类型均通过 |
| frontend `N node_modules/typescript/bin/tsc --noEmit`；`N node_modules/eslint/bin/eslint.js src/features/jobs/OperationLogs.tsx src/features/jobs/OperationLogs.test.tsx src/app/MainlineWorkspace.tsx src/app/WorkspacePage.test.tsx --max-warnings 0`；`N node_modules/prettier/bin/prettier.cjs --check src/features/jobs/OperationLogs.tsx src/features/jobs/OperationLogs.css src/features/jobs/OperationLogs.test.tsx src/app/MainlineWorkspace.tsx src/app/WorkspacePage.test.tsx`；`N node_modules/vite/bin/vite.js build` | 均退出0；最终dist为 `index-C1mwuZXp.css`、`index-BPaGU6Gh.js`。保留已有大于500kB的bundle提示，不追加拆包范围 |

中间失败如实保留：首轮92项后端用例均在数据库初始化阶段因RawSQL空tuple合并参数失败，改为空list后92项通过；两处新测试类型注解补齐，新增原子回滚测试后93项通过。交叉审阅发现NUL查询会误报数据库错误，限定q在查询前返回400并补2项零SQL测试后最终95项通过。前端首次新测试提前点击尚未渲染的分页按钮，保持断言并等待响应后26项通过。Windows临时目录/子进程权限使首次契约与构建失败，同命令提升权限后通过。没有弱化校验或测试。

根目录实际执行 `P -B -X utf8 .runtime/operation-log-search-20261003/update_search_runtime.py prepare --docker D`、`build --docker D --checks-passed`、`update --docker D --checks-passed`。首次prepare因误要求未配置健康检查的frontend具有healthy状态而只读拒绝，没有停写或迁移；按实际配置保留PG/Redis/API的healthy要求，前端改为运行状态加HTTP/CSP/资产核对，13项离线维护边界测试通过后，三阶段均退出0。

真实维护再次核对接收和queued/running任务均为0，先停API并复查，再短暂停原Worker/reconciler。完整数据库自定义格式备份 `database-before.dump` 为179867字节，SHA-256及pg_restore目录核对通过；仅执行 `jobs.0007_operationlog_display_id`，覆盖entrypoint避免内容加载。18条原日志获得固定编号，34张原表的全部旧列摘要保持，迁移表仅新增此迁移；内部源码60对象、6卷3网、教学数据、其他实例以及原Worker/reconciler容器及镜像保持，模型配置关闭。运行核对确认跨页/详情编号稳定、名称/类型搜索、完整10参数及非法查询；HTML/JS/CSS/theme-init字节与当时dist一致，CSP保持。主更新API标签为 `log-search-20261003152129-2065a8`，原标签和证据未覆盖。

桌面真实浏览器已核对类型“导入”返回6条，操作对象“任务簿源码基线”与项目“模块独立性”各返回固定ID5/4，详情显示“日志4”；关键词与四列条件同时应用仍为ID4，全部清除恢复18条。首次390×844浏览器验收发现新增搜索框使说明文字被挤成竖列；将767px以下的日志筛选区域改为单列，26项前端回归与最终构建再次通过。另行准备前端专属维护脚本，根目录实际执行 `P -B -X utf8 .runtime/operation-log-search-20261003/test_frontend_layout_repair.py -v`（6项离线边界测试通过，0.026s），随后 `frontend_layout_repair.py prepare --docker D`、`build --docker D --checks-passed`、`update --docker D --checks-passed` 均退出0。只加载唯一前端标签 `log-search-layout-6195e10b7be1`，未重复迁移/内容加载或启停后端；现有所有字段含display_id的数据库摘要、API/Worker/reconciler身份及状态、源码和保护资源均保持，最终资产字节与最终dist一致。维护辅助脚本的默认沙箱离线临时目录权限失败已区分，同命令提升权限检查通过，原失败和主更新证据未覆盖。

最终真实浏览器：桌面1243px与窄屏379px均无页面横向溢出；窄屏筛选区约162px高，搜索、说明、清除按钮及表格ID/横向控件均可在首内容页阅读。滑杆移到右侧后结束时间弹层左右边界约77/367px，首日期控件自动聚焦；Escape关闭并返回列筛选按钮。窄屏类型代码import返回6条，清空立即恢复18条并聚焦搜索框；桌面内容分页和最终刷新仍保持ID18至1，页面不显示项目ID输入或日志UUID，顶栏全局搜索保持。最终页面控制台error为0，窗口恢复原尺寸、筛选清空且试用页保留。截图和结构化记录为 `browser-desktop.png`、`browser-mobile-final.png`、`browser-mobile-filter.png` 与 `browser-proof.json`；首次窄屏问题截图也保留在忽略目录。

最终审阅相对本轮基线的16份修改文件和3份新增文件，未改原审计写入口，原test_operation_audit.py字节保持；Git状态237项既有记录保留，只增加指定3个新文件。同步API清单、API/前后端规范和本节，记录数字编号、名称搜索、10字段限制、旧写入口兼容和迁移/回退边界；原12.6的9字段与UUID呈现保留为阶段历史，当前规则已明确更新，无其他记忆与实现矛盾。未创建独立记忆系统或修改中央记忆，不执行Git写操作。编号允许跳号且不可按页重算；常规回退保留新增列。IME/防抖/迟到请求由直接测试覆盖，未以真实操作系统输入法演示替代；浏览器和运行核查均为读取/筛选，没有新增导入、删除或模型任务。12.6保留为前轮历史，不用其结果替代本轮验证。

### 12.8 追加：日志搜索框去除双层蓝框

2026-10-04 用户通过5181操作日志页浏览器评论，要求移除搜索输入内部及外部蓝框。本轮读取AGENTS、前端规范、M26当前记录和实际CSS/浏览器计算样式，在 `.runtime/operation-search-focus-20261004` 保存三份文件字节基线和完整已有Git状态。改动限定日志搜索CSS、前端规范和本节；无搜索逻辑、接口、迁移、依赖或Git写操作。

外层focus-within移除accent描边，仅已有边线变为header-text中性色；输入选择器增加label元素，优先级高于后加载的通用input:not规则，保证内层border/outline/box-shadow归零，避免嵌套框。搜索清除按钮的键盘outline也局部使用中性色，其余输入和列筛选保持。前端规范将旧“整体焦点样式”更新为此明确规则，历史12.7证据保留。

实际执行（工具别名P/N/D同12.3）：frontend `N node_modules/prettier/bin/prettier.cjs --check src/features/jobs/OperationLogs.css`、`N node_modules/typescript/bin/tsc --noEmit` 退出0；`N node_modules/vite/bin/vite.js build` 默认沙箱首次因spawn EPERM失败，同命令提升执行权限后通过，最终dist为 `index-DQgxtRQe.css`、`index-BTcx_S5m.js`。保留既有超过500kB的构建提示；CSS局部修改不新增镜像式单元测试，真实焦点和主题由浏览器验证。

根目录实际 `P -B -X utf8 .runtime/operation-search-focus-20261004/load_frontend.py prepare --docker D`、`build --docker D --checks-passed`、`update --docker D --checks-passed` 均退出0。该忽略目录中的短入口复用12.7已验证的前端独立流程，使用本轮独立证据和唯一镜像标签；只替换frontend。验证确认完整数据库字段含display_id摘要、迁移记录、原源码60对象、6卷3网、API/Worker/reconciler与其他容器身份及状态保持，模型配置关闭；实时HTML/JS/CSS/theme-init与最终dist字节一致，CSP保持。不重新迁移、加载内容或重启后端。

5181真实浏览器检查已完成：鼠标聚焦以及深/浅主题Tab进入输入时，计算样式均为输入border=0px、outline=none、box-shadow=none（浅色鼠标），外层outline=none；浅色边线rgb(38,38,38)，深色rgb(255,255,255)。搜索import命中6条，Tab到清除按钮保留白色键盘描边，清除后恢复当前全量记录并聚焦输入。首次按历史18条等待清空结果超时，当时实时全量已为20条；只读核对关键词为空、没有页面错误后使用实际全量计数完成核验，未改产品或测试断言。桌面宽1069px且scrollWidth同值，没有页面横向溢出。主题恢复浅色，关键词清空，页面保留供用户核对；本轮不重跑窄屏验收，也不外发模型或新增导入/删除。

最终相对三份基线审阅，仅日志CSS和两份长期文档变化，原240项Git状态保持。无接口或架构知识变化，前端规范更新中性色焦点规则，本节记录实际验证；历史12.7样式作为前一阶段保留，无当前规则矛盾。截图 `browser-desktop.png`、计算样式与搜索核查 `browser-proof.json` 和维护保护结果均在本轮忽略目录；不建立新的项目记忆系统或修改中央记忆。

<a id="m27"></a>

## 13. M27 参考图全页面重构与固定浅色（2026-10-04）

### 13.1 授权、计划与增量边界

用户明确要求实施已审阅计划：按三张参考图重构项目管理、项目工作区、操作日志及配套面板，移除深色模式和按屏内容分页，补齐必要只读接口。执行前读取项目指令、README、需求、结构、前后端规范、API清单/协议及本阶段M26记录，核对源码、测试和240项已有Git状态；保存 `.runtime/m27-redesign-20261004-104035/manifest.json`、`baseline/` 和原HEAD。617份非敏感源文件基线按原字节保留，最终增量清单和diff均相对本轮基线，不从HEAD重建已有页面。

本轮不新增依赖、数据库表、迁移、账号、源码编辑执行或通用引用索引，不改变导入、删除和模型提交契约，不更新5181现有试用实例，不执行Git写操作或模型外发。ZIP20MiB、目录100MiB/2000文件、单根自动分析/多根选择/无根可读、删除隔离和单次模型确认继续有效。M21–M26主题/内容分页说明保留为历史，当前规则由M27替换。

### 13.2 已实现内容

| 范围 | 最终行为与主要取舍 |
| --- | --- |
| 公共外壳 | 64px品牌、直接搜索、三入口、本地模式；保留Ctrl/Meta+K且无徽标。HTML、CSS变量、Ant Design、源码、图和Portal固定浅色；删除主题状态、切换入口及启动脚本，不读取旧主题偏好。 |
| 滚动与草稿 | `ScrollPanel`替代`ContentPager`及位移测量，删除旧分页实现和对应测试；保留实际记录分页和单实例草稿。对话框、搜索和命名使用有界滚动，Portal不驱动外层滚动。矮窗口允许源码主体滚动至底栏。 |
| 项目管理 | 横向导入区、可展开项目/快照卡片、真实文件数/版本数/根路由、技术语言/声明/使用标签及未知空态；服务端先筛选排序再分页，技术选项覆盖完整关键词范围。≥1280px常驻340px状态栏，窄屏同一内容树作为模态侧栏，关闭/离开后停止轮询。 |
| 活动阶段 | 来自真实任务和日志事件，不编造百分比。重放同一请求时优先原执行日志，只有重放记录时如实回退，避免后来的幂等响应遮住原阶段；GET不补写。 |
| 工作区 | 五项左侧导航；源码约280px文件树、去重可关闭标签、面包屑、单窗/分屏、底部状态和相关依据。接口列表/详情、关系图/依据、知识目录/正文、讲解步骤/内容统一浅色；普通导航保留URL上下文。 |
| 源码读取 | 每次200行，每窗最多1000行DOM和一个相邻预取；切文件取消旧请求并防止迟到结果污染，块失败原位重试。跳行、末行、同名不同路径、关闭相邻标签、跨快照隔离、独立分屏滚动和URL恢复有直接测试；缩略图只反映已加载部分。 |
| 相关依据 | 分页聚合已保存接口、图关系、知识命中，校验文件、扫描和分析同快照；明确静态事实范围，不生成完整反向引用索引。 |
| 操作日志 | 四张真实统计卡、互斥结果/快捷筛选、稳定排序、表格和400px详情；低于1280px使用详情覆盖层。统计完整继承关键词/类型/项目/日期，忽略结果/快捷视图/分页；零分母显示“暂无数据”，空结束时间最后。 |
| 恢复与导出 | 服务端返回恢复资格，写入口再次校验；关联按直接父子/重试/同对象身份读取。CSV与列表共用筛选，UTF-8 BOM、公式保护、仅显示字段和稳定错误码，10000条/10MiB超限明确拒绝。 |
| 契约 | 新增八项GET，工作台83项操作；OpenAPI、生成TypeScript、运行时校验和API清单一致，不手工重复维护DTO。 |

最终改动文件逐项见本轮忽略目录 `changed-files.md` / `changed-files.json`，逐文件增量见同目录diff；生成产物和一次性验收数据未加入源码。复核确认依赖、锁、模型、迁移、部署文件相对基线不变，原HEAD不变。

### 13.3 自动化验证

工具别名：`P=F:/Program/Fall_Campus_Recruitment/.runtime/m1-t02-venv/Scripts/python.exe`，`N=F:/Program/Fall_Campus_Recruitment/.runtime/tools/node-v24.21.0-win-x64/node.exe`，`D=C:/Program Files/Docker/Docker/resources/bin/docker.exe`。下表记录实际执行结果，后端数据库验证使用脚本创建的独立PostgreSQL/Redis并清理，不使用现有实例数据库。

| 工作目录与实际命令 | 观察结果 |
| --- | --- |
| 根目录 `P -B -X utf8 scripts/check_v03_backend.py --docker D -- python -B -m pytest apps common tests --ds=config.settings.local -q -p no:cacheprovider --tb=short` | 完整后端 **749 passed，199.51s**；13项既有fork弃用警告。随后两项小范围补充按下行分别验证，不冒称重新跑过增加用例后的全套。 |
| 根目录，同一隔离脚本的pytest目标 `apps/jobs/tests/test_operation_dashboard.py` | **19 passed，9.31s**；含实际10000条完整导出/10001条拒绝、合法中文名称构成精确10485760字节成功/再加1字节拒绝、空结果BOM与标题、8种公式或控制前缀。未替换生产限额。 |
| 根目录，同一隔离脚本的pytest目标 `apps/projects/tests/test_management.py` | 最终 **17 passed，4.20s**；包括分页前筛选、真实技术身份、摘要回退、活动查询及原执行/重放日志选择。 |
| frontend `N node_modules/vitest/vitest.mjs run --reporter=dot` | 最终完整 **47文件280项通过，166.59s**。输出保留jsdom伪元素计算样式和旧学习样例重复key警告；不修改退役业务以消除警告。 |
| frontend `N node_modules/vitest/vitest.mjs run src/features/jobs/OperationLogs.test.tsx src/app/WorkspaceShell.test.tsx --reporter=dot` | 最后日志空态文案和dialog快捷键联动后 **24项通过，11.66s**。项目侧栏9项、源码13项、课程时序9项定向检查也通过。 |
| frontend `N node_modules/typescript/bin/tsc --noEmit`；`N node_modules/eslint/bin/eslint.js . --max-warnings 0` | 类型检查和完整ESLint通过；最终日志文案再次运行文件级ESLint和完整类型检查通过。 |
| frontend `N node_modules/prettier/bin/prettier.cjs --check @targets`，targets从本轮清单取现存非生成前端文件，并包括CourseReader测试 | 全部本轮匹配文件格式通过；没有仓库级格式改写。 |
| backend `P -B -m ruff check config common apps tests`；`P -B -m mypy config common apps tests --platform linux --no-incremental`，MYPYPATH指向根目录scripts | lint通过，**257源文件类型检查通过**；最终项目投影/日志边界测试改动另完成相关文件lint、format、mypy。 |
| backend `P -B manage.py check --settings=config.settings.test`；`P -B manage.py makemigrations --check --dry-run --settings=config.settings.test` | 无系统检查问题，无迁移漂移。 |
| 根目录 `P -B -X utf8 scripts/check_contracts.py --node N` | 最终83/3/7操作与清单一致；**59契约测试通过**，两套生成类型及TypeScript检查通过。 |
| 根目录 `P -B -m unittest discover -s scripts -p test_check_contracts.py` | **6项通过**。 |
| frontend `N node_modules/vite/bin/vite.js build` | 最终退出0；产物`index-BknQg0NZ.css`和`index-3OMHd5k7.js`。保留既有大于500kB包体警告，不扩大到未授权拆包。 |

中间失败均已区分：首次完整后端两项仍断言旧75操作，更新真实83项及新增路由白名单后完整通过；前端旧内容分页断言、无效测试技术枚举及关闭标签位置问题分别修正。最后一次完整前端曾出现CourseReader异步时序失败：课程标题先出现、进度缓存已更新但UI通知未完成；补上新课程零进度呈现等待再释放旧响应，保留原全部缓存/界面断言，最终280项通过。沙箱的spawn EPERM/临时目录权限和Docker访问限制使用同一命令授权执行后通过，没有削弱校验。

### 13.4 真实隔离运行与浏览器证据

实际根目录 `P -B -X utf8 scripts/check_m26_workspace.py start --docker D` 启动本轮标签 `learning-lab-m26-verify-fa89a049a4d4` 的隔离栈，入口5185；沿用现有生命周期机制，未替换5181。模型配置保持关闭。根目录 `P -B -X utf8 .runtime/m27-redesign-20261004-104035/verify_http.py` 退出0，结构化证据见`http-proof.json`与过滤导出CSV。

- 浏览器真实上传`test/task-board.zip`：9文件、唯一根自动分析7接口，完成后URL携带正确项目/快照/分析/源码；不使用图片示例数据。
- HTTP真实目录导入1205行无根源码可读，ZIP两根进入待选择，损坏CRC ZIP失败返回`INVALID_ARCHIVE`和重新上传动作。仅对隔离栈本轮创建的清理用样例执行删除：删除最新快照后摘要回退，删除测试项目后6条日志保留且对象不可进入；没有删除用户已有数据。
- 10组日志筛选与CSV编号一致；同对象历史及父子任务按身份核对。导出内容包含正确BOM和显示字段。浏览器点击导出未观察到IAB的download事件，不能据此声称本地文件下载已落盘；HTTP响应、导出内容、限制和前端触发测试已验证。
- 按实际CSS视口1680×945、1440×900、1280×720、768×1024、390×844核验三入口，15组`scrollWidth`均等于`innerWidth`，根`color-scheme=light`、画布`rgb(244,248,254)`；每组截图在真实列表/源码加载后保存。证据见`browser-final-matrix.json`及对应尺寸JPG。
- 390×480矮窗口源码可滚至最后状态/依据，1205行文件跳末行显示1188–1205、加载801–1205共405行DOM；跨200行块滚动观察加载1–600共600行。长路径/代码横向滚动由自身容器承担。
- 窄屏状态侧栏及日志详情Escape关闭后回到原按钮；帮助底项可达。桌面常驻活动栏不拦Ctrl+K。快照命名保存后，全局快照搜索返回服务端名称并跳到准确快照。
- 接口、知识正文、关系节点300px依据栏及图弹窗实测浅色；日志搜索内部border/outline/shadow清零，筛选Portal在390px内可见并回焦点。零匹配统计成功率显示“暂无数据”。最终浏览器控制台error为0。
- 讲解步骤进入既有流程，在未配置模型时明确阻止预览并显示配置错误，没有实际模型调用。旧主题偏好、存储不可用和系统深色由组件测试及固定首屏代码验证；浏览器计算样式实测为浅色，未实际切换宿主操作系统深色模式。

### 13.5 项目记忆、最终审阅与限制

读过AGENTS、README、需求、结构、前后端规范、API规范/清单及第四阶段M26；未发现独立项目记忆文件。更新AGENTS、README、需求、结构、前端规范、API规范/清单和本节，明确固定浅色、面板滚动、五面板职责、83项只读契约及真实统计/导出边界。旧双主题/内容分页与本轮实现的差异已通过源码搜索、契约检查和浏览器计算样式确认，并将旧说明标记为历史；没有建立额外记忆系统或写中央记忆。

主要取舍是复用既有React/Ant Design/History API和静态事实，保持单实例表单及写入安全边界；界面布局重构不引入编辑器库或账号。手工复核观察点：打开一个接口依据，源码应定位原快照对应文件行；日志失败动作应由服务端资格决定，零分母不显示0%。

本轮属于本地工程与隔离样例验收，不代表真实用户试用、其他浏览器/宿主兼容、真实模型兼容或压力测试。CSV浏览器下载事件、真实操作系统深色切换未取得浏览器级证据，上述HTTP/自动化证据不能替代这些结论。现有构建体积和测试环境警告保留。运行栈清理及最终diff复核结果在本节末记录。

最终根目录执行 `P -B -X utf8 scripts/check_m26_workspace.py stop --docker D` 退出0，仅本轮5185标签下容器、网络和测试卷清理完成；浏览器验收标签关闭、视口恢复。`P -B .runtime/m27-redesign-20261004-104035/capture_incremental_changes.py` 刷新清单：本轮新增22、修改56、删除6，共84份源文件，617份原始基线哈希一致，HEAD未变，无受保护范围改动；当前274项Git状态包含原工作区修改及本轮增量，不把它们全部归为本轮。`git diff --check`通过。最终源码检索没有运行时ContentPager、内容分页或深色主题逻辑；检索中发现的孤立旧CSS选择器已删除并重新通过该文件Prettier及Vite构建。没有遗留临时调试代码或未解决的本轮测试失败。

### 13.6 用户授权启动M27供审阅与试用

2026-10-04 用户追加“请启动项目，我来进行审阅和试用”。只读核对当前Git状态、AGENTS、README、M27及历史5181维护记录，确认已有 `learning-lab-v1-verify-8e9c1a0a0101` 正运行改造前镜像。用户本次指令授权加载刚完成的M27；13.1–13.5“未更新5181”属于此前工程验收范围，保留历史，不代表本次追加动作。

给出保留数据、保存基线和备份、最小加载及就绪核对计划后，在忽略目录 `.runtime/m27-review-20261004` 创建本轮独立维护入口和证据。复核确认M27新增模块只进入API读取链，没有Worker任务、模型、迁移、依赖和配置变化，因此仅替换API/前端，原Worker/reconciler、PG、Redis及已停用教学服务保持身份和状态。采用运行容器标签确认的九层Compose文件，再追加本轮唯一镜像层；不读取根.env或复制凭据卷。旧辅助验证器依赖三个资产的历史假设不适用，按实际HTML的JS/CSS清单逐项校验。

根目录实际依次执行 `P -B -X utf8 .runtime/m27-review-20261004/start_review.py prepare --docker D`、`build --docker D`、`update --docker D`，均退出0。prepare记录34张表全部字段逐行摘要、迁移清单、60个内部源码对象、6卷3网、服务/其他实例身份及无活动/接收任务状态；49项Linux依赖与当前锁完全一致。build复用原API同版本依赖层构建新后端，前端使用现有Dockerfile，原镜像标签保留。更新前以无网络一次性容器的`sha256sum`验证新镜像HTML/JS/CSS与已测dist完全相同。

update短暂停止原API接收请求后再次检查空闲任务和数据摘要，原Worker保持运行；保存192461字节自定义格式数据库备份并用`pg_restore --list`校验，不输出数据库内容。随后仅 `compose up -d --no-deps --no-build --pull never --wait --wait-timeout 90 api frontend` 加载新版本。未执行迁移、内容重载、导入、删除或模型调用。维护辅助脚本为替换前失败增加一次原API恢复及双异常证据保留；语法检查通过，本次未触发故障恢复分支。

内置verify通过：34表全字段/行摘要、迁移清单、60源码对象、6卷3网、未更新服务及其他实例身份/状态全部保持；项目、项目摘要、活动、快照搜索、任务、日志、日志统计均HTTP200，项目5、任务20、操作日志20。实时HTML及`index-3OMHd5k7.js`、`index-BknQg0NZ.css`与本地已测产物完全一致，CSP保持；`manage.py check`无问题，`manage.py migrate --check`确认无待执行迁移，Celery inspect ping返回pong，模型配置仍关闭。结果见本轮`verified-*.json`，备份、资源与数据摘要仅保留在忽略目录。

真实浏览器打开并保留 `http://127.0.0.1:5181/`：读取原有5个项目，三个入口和新版导入区正常，`data-theme=light`、`color-scheme=light`且无主题切换；实际宽1243px与页面scrollWidth一致，控制台error为0，截图为`browser-ready.jpg`。向Codex提交打开页面请求并通过浏览器可见性将页面展示供用户试用；服务继续运行，不清理本次试用环境。

本次只更新本节长期运行记录，业务源码、依赖、迁移和原274项Git状态保持；`git diff --check`通过。读取项目记忆后核实旧“启动九服务/三个资产”已不适用，执行以当前退役边界及M27固定浅色产物为准；未建立新记忆系统或写中央记忆。本次未重复完整业务回归，沿用13.3已执行结果并完成实际加载检查。真实用户审阅结论待反馈，模型外发仍未启用。

### 13.7 浏览器批注：导航居中与表头日历筛选

2026-10-04 用户在5181批注要求三入口居中放大、日志筛选移入对应字段并使用日历、删除常驻筛选/导出说明。核对AGENTS、前端规范、M27记录和当前274项Git状态后，先保存八个涉及文件的现状副本及状态清单到忽略目录`.runtime/m27-browser-comments-20261004`；只在现有代码上增量修改，不从HEAD重建。

- 顶栏通过等宽左右区域使三入口按页面中线居中，桌面17px；768–1279px以16px在第二行居中，手机保留菜单/搜索。品牌、直接搜索、Ctrl/Meta+K、URL导航、焦点和单实例草稿逻辑保持。
- 操作类型、结果、开始时间、结束时间筛选复用原组件进入对应表头，取消工具栏四个独立筛选块和指定提示段落。中文DatePicker保留两类时间各自上下界、单端范围、时分秒、反序校验、显式应用/清除、Escape焦点返回；日期类型从已有Ant Design推断，不新增依赖或更改锁文件。
- 日历有效草稿在选择时同步，手动清空输入失焦时同步null，避免外层立即应用读到旧值；沿用相同ISO查询参数、结果/快捷视图互斥、统计范围、分页和CSV导出契约。没有后端或数据库改动。

本节沿用13.3的P/N/D工具别名。frontend实际执行`N node_modules/vitest/vitest.mjs run src/features/jobs/OperationLogs.test.tsx src/app/WorkspaceShell.test.tsx --reporter=dot`，最终2文件25项通过，23.40s；涵盖实际日期格点击、秒级精度、应用前无查询、空单端、四界组合、分页、导出日期条件、导航/焦点/草稿。`N node_modules/typescript/bin/tsc --noEmit`、对四个改动TS/TSX执行`N node_modules/eslint/bin/eslint.js … --max-warnings 0`、对六个改动前端文件执行`N node_modules/prettier/bin/prettier.cjs --check …`均退出0。`N node_modules/vite/bin/vite.js build`通过，产物为`index-CrakctK9.js`与`index-CA1Sc0_t.css`。

首次时间筛选测试发现日历内部提交和外层应用存在时序差，补上有效草稿及空输入同步后保持原组合/反序/清除断言并通过。新增失焦处理的HTMLElement类型及测试库不支持的exact选项在静态检查中发现，分别补输入元素类型保护、使用默认精确名称匹配后复验通过。默认沙箱spawn EPERM使用相同命令正常权限重跑；一轮子代理工具等待未返回，取消后由根代理执行上述最终检查。保留jsdom伪元素计算样式与Vite既有大包警告；本次范围为前端批注修复，未重复后端或完整业务回归。

读取并更新前端规范当前规则与本节；旧M27布局记录作为历史保留，未发现独立项目记忆文件，未创建新记忆系统。运行加载与浏览器核对结果在本节后续段落记录。

根目录使用本轮忽略目录的`update_frontend.py prepare/build/update --docker D --checks-passed`依次保存新鲜基线、构建唯一镜像和仅替换frontend；继承现有M27 Compose/API镜像覆盖，不停止或替换API/Worker/reconciler，不迁移或重载内容。首次载入后只读验证通过：完整数据库与迁移、60源码对象、6卷3网、非前端及其他实例容器身份/状态和CSP保持，实时HTML/JS/CSS哈希与已测dist一致，项目摘要/活动/日志统计HTTP200。

真实浏览器首次测得桌面1609×928导航中心804.65px、视口中心804.5px、字号17px；1280×720中心639.99px、字号17px，768×1024第二行中心384.08px、字号16px，页面scrollWidth分别等于视口宽。四个筛选均位于对应th中且指定提示不存在。点击中文日历10月4日并应用后真实记录从20条变为当天2条（编号20/19），清除恢复20条；应用后焦点回到表头按钮。

390×844实测发现日历默认只翻转上下方向时顶部到-62px，月份标题越界。按已安装组件的popupAlign接口增加横纵shift（仍保留翻转和高度限制），不改组件库；针对`时间反序|中文日历|日志详情保留|导出保留`重新执行Vitest，4项通过、其余14项按名称未选中；完整TypeScript、该文件ESLint/Prettier及Vite构建再次通过，最终JS为`index-CoI89B3a.js`，CSS仍为`index-CA1Sc0_t.css`。在新的忽略目录`.runtime/m27-browser-comments-calendar-20261004`保存第二次前端维护的独立基线与证据，不覆盖首次运行记录。

最后复核将日历默认4px偏移归零，并保留内部“确定”按钮，使矮窗口可先收起日历再应用整个范围；内部确认仍不发起列表查询。日历测试增加实际确认操作，按组件真实可访问名称“确 定”定位，最终同一两文件Vitest命令再次**25项通过，24.23s**；TypeScript、改动TS/TSX ESLint、六个前端文件Prettier及Vite构建均通过。最终交付产物为`index-BWU6I1Go.js`和`index-CA1Sc0_t.css`；此前两个JS哈希仅属于本节中间验证记录。

使用`.runtime/m27-browser-comments-final-20261004/update_frontend.py prepare/build/update --docker D --checks-passed`完成最后一次仅前端加载，各步骤及内置verify退出0；再次核对34表全字段/行摘要、迁移、60源码对象、6卷3网、全部非前端及其他实例容器身份/状态、CSP一致，三个只读接口HTTP200，最终HTML/JS/CSS与本地已测产物哈希完全一致。未新增依赖、修改配置或启用模型调用。

最终浏览器390×844日历范围为y=0–616.97、x=86.99–376.98，390×480日历范围为y=23.81–479.81且内容高度617/可视高度456，均无页面横向溢出。矮窗口实际点击10月4日、滚动到日历“确定”、收起后“应用开始时间筛选”，得到编号20/19的2条真实记录；清除恢复20条。Escape回到表头触发按钮。恢复原1609×928窗口与未筛选列表后，Ctrl+K仍聚焦直接搜索、导航17px且居中、提示段落不存在，控制台error为0。页面保留供继续审阅；最终截图和尺寸证据在首个本轮目录的`desktop-final.png`、`calendar-mobile-final.png`、`short-filter-applied.png`与`browser-evidence.json`。

最终对照本轮文件副本审阅八个源码/文档文件增量；`git diff --check`通过，原274项状态条目集合保持。忽略目录的维护脚本和证据未加入源码，不执行Git写操作。前端规范已同步导航布局与表头日历规则，本节是唯一追加验证记录；本轮限于该三个浏览器批注，未重复完整后端或其他业务流程验收。

### 13.8 操作日志参考改造

2026-10-04 用户授权执行已确认计划：以`attack_verify`操作日志为只读参考，沿用当前固定浅色，仅改日志页面及其直接依赖、测试和两份约定文档。读取AGENTS、前端规范、API规范/清单及M26–M27，核对现有274项工作区状态；在忽略目录`.runtime/operation-log-redesign-20261004-af4dbf71`保存八个涉及文件的原字节副本和632份非敏感源码哈希。没有从HEAD重建未跟踪日志文件。参考端口20001未监听，参考依据为指定六个源码文件和已安装组件样式，不能据此称参考页面实机验证通过。

- 页面改为面包屑、主题色圆点标题、既有统计、左搜索右操作工具栏、紧凑有边框表格、底部居中分页。正文14px，长名称和错误代码省略，完整内容可从详情查看；宽表格继续局部横向浏览和滑杆，窄屏/矮窗口通过局部滚动保持末项可达。新增样式仅作用于日志及其专属Portal，保留既有中性色搜索焦点，无全局最小宽度、依赖或其他页面改动。
- 复用Ant Design分页和原`page/page_size`参数：默认20，可选10/20/50/100；四种时间排序保持。搜索、筛选、排序、数量变化回第一页并关闭详情，翻页关闭详情，同查询三秒后台刷新保留详情和滚动。200ms防抖、IME和完整查询键/AbortSignal保持；查询变化保留旧行时明确正在更新并禁用旧行操作。非首页`PAGE_NOT_FOUND`返回第一页，其他失败保留重试入口。
- 详情统一为约600px自适应右侧抽屉，完整字段、阶段、错误、关联记录、历史和原任务操作资格保持。明确关闭按钮、Escape、遮罩、焦点隔离和返回入口；开合中快速关闭以及切换关联日志均保持焦点连续性。原入口被刷新移除时回到日志搜索，隐藏模块停止查询且不向隐藏页面恢复焦点。
- CSV继续导出完整筛选及排序并剥离分页参数，同步请求护栏防止重复启动；取消、成功和失败有独立反馈，结束/失败恢复按钮并回收URL。零记录仍允许表头CSV。没有日志删除/清空/批量接口，不新增复选框、批量菜单或危险操作；原任务重试/继续清理资格和模型外发边界不变。
- 按钮及行颜色约150ms、抽屉约240ms、筛选浮层沿用组件约200ms开合；支持`prefers-reduced-motion`局部取消位移动效，不加逐行入场、循环装饰或动效依赖。

本节`N`为根目录`.runtime/tools/node-v24.21.0-win-x64/node.exe`，`P`为`.runtime/m1-t02-venv/Scripts/python.exe`。frontend最终TypeScript、三个改动TS/TSX的ESLint、四个改动前端文件的Prettier及Vite构建均退出0；最终产物`index-eGDA_kGu.js`、`index-Bl-oKy9f.css`。构建保留既有大于500kB警告，未扩大范围到拆包。

日志组件测试保留18项原行为断言、增加19项，最终37/37通过，总耗时38.60s；涵盖四种排序/页容量、页码复位、迟到响应、旧行禁操作、失效页回首页、三秒轮询、隐藏停读与Portal清理/恢复条件、详情加载/失败/关联切换/快速Escape焦点，以及导出重复保护、取消/失败/成功恢复和空表头契约。中间失败如实区分：初轮主要是详情ID呈现及rc组件测试id冲突，补唯一可访问标题ID；后续失败暴露初始焦点与快速关闭恢复时序，修复正文外关闭按钮焦点及可取消下一帧兜底。保留原语义断言，未删除或弱化测试。默认沙箱`spawn EPERM`在相同命令正常权限重跑后通过；jsdom伪元素计算样式警告保留。

frontend实际最终命令如下（`N`为上述确切Node路径，JSON证据位于本轮忽略目录）：

```text
N node_modules/vitest/vitest.mjs run src/features/jobs/OperationLogs.test.tsx --reporter=dot --reporter=json --outputFile ../.runtime/operation-log-redesign-20261004-af4dbf71/vitest-final.json
N node_modules/typescript/bin/tsc --noEmit
N node_modules/eslint/bin/eslint.js src/features/jobs/OperationLogs.tsx src/features/jobs/OperationLogsDetail.tsx src/features/jobs/OperationLogs.test.tsx --max-warnings 0
N node_modules/prettier/bin/prettier.cjs --check src/features/jobs/OperationLogs.tsx src/features/jobs/OperationLogsDetail.tsx src/features/jobs/OperationLogs.test.tsx src/features/jobs/OperationLogs.css
N node_modules/vite/bin/vite.js build
```

临时本地候选入口5186只转发GET至现有5181，5187使用75条独立合成日志；所有非GET拒绝。根目录实际`P -B -X utf8 .runtime/operation-log-redesign-20261004-af4dbf71/check_preview_server.py`退出0，覆盖辅助入口的分页、四排序、组合筛选、空结束时间、统计、CSV、慢请求/500、非GET拒绝与路径边界。该辅助代码和所有证据均留在忽略目录，不新增产品测试框架或部署配置。

浏览器实际读取候选页面的20条现有日志，搜索、10条分页及下一页、排序复位、详情完整字段/历史、Shift+Tab焦点隔离和Escape返回均已操作观察。合成页面实测分页位置保持y=739.67px，输入待更新禁用旧行、零记录、读取失败与重试、导出失败恢复/取消/成功反馈、长名称省略（可视218px/内容753px）、详情失败可关闭。切换关联记录初次观察焦点落BODY，补稳定关闭按钮焦点并重新通过组件和最终浏览器验证。

响应式以实际CSS视口为准：1398×874、1243×699、746×994、379×819、379×466，页面`scrollWidth`均等于视口宽度。桌面抽屉599.99px、手机379.03px；手机表格可视312px/内容1103px，滑杆可到最右列。矮窗口中文日历范围x=11–301、y=23.83–465.85，实际点击10月4日/内部确定/应用，读取真实编号20/19两条，再清除恢复20条；局部滚到分页底部417.51px，低于466px视口。后台轮询前后表格scrollTop均848.16px，真实候选控制台error为0。宽度请求受IAB缩放影响，因此不将请求的1440/390尺寸冒称实际尺寸。

最终审阅另发现并修复两项兼容遗漏：Ant Design默认在小屏隐藏页容量选择，使用日志局部规则保留选择器，手机实测切换10条成功且分页底部770.91px低于819px；隐藏页面原表头Popover/日历与页容量Select仍挂body，随active重挂组件后实测切项目管理无可见dialog/listbox，焦点留导航按钮，新增两项测试覆盖全部四筛选/日历、数量下拉及恢复已应用状态。

携带job入口采用局部滚动与固定300px表格，防止既有任务历史/恢复表单增高挤掉分页。只读隔离任务`00000000-0000-0000-0000-000000009001`复用真实历史system-checks读取契约和60段明确标注合成正文；自检再次通过，未访问真实上游。浏览器展开历史任务后任务区高7189.22px，主区可滚至7140.19px，表格仍299.99px、分页底部817.03px低于874px视口，页面无横向溢出；截图`after-job-history.jpg`。未修改任务组件、资格判断或提交行为。

截图和结构化证据为该目录`before-desktop.jpg`、`after-desktop.jpg`、`before-mobile.jpg`、`after-mobile.jpg`、`after-detail.jpg`、`after-mobile-detail.jpg`、`after-short.jpg`和`browser-proof.json`。浏览器显示CSV已生成并开始下载，但IAB未返回下载事件，不能声称文件已落盘；CSV响应/内容契约由隔离自检和组件测试验证。当前宿主`prefers-reduced-motion=false`且工具未提供偏好切换，因此只核验局部CSS覆盖，未实际切换宿主减少动态效果。未操作真实任务重试、继续清理、删除或模型调用，未重复后端/完整业务回归。

项目记忆同步：只更新前端规范当前日志规则及本节唯一实现/验证记录；修正“低于1280px切换日志列表/详情”“详情右栏”的当前描述，M27早期记录保留历史。已以源码和实际渲染确认固定浅色，未恢复历史双主题；未发现独立项目记忆文件，没有创建新记忆系统或写中央记忆。最终增量审阅和临时入口清理结果在下文记录；5181实例保持原版本，不把本地候选验收称为运行加载。

最终根目录`P -B -X utf8 .runtime/operation-log-redesign-20261004-af4dbf71/review_increment.py`退出0：632份基线中仅上述六个源码/文档文件变化，其余626份哈希一致，无删除或新增未忽略源码；274项状态条目集合和HEAD保持。增量辅助核验最初把基线主动排除的两个既有环境/秘密初始化文件误报新增，核对它们本已跟踪、时间早于本轮且Git无变化后延续原排除规则；未读取敏感内容或扩大排除范围。六个文件的完整增量保存为`incremental.diff`，各文件已审阅，`git diff --check`通过，未引入业务调试代码、依赖、配置或Git写操作。

只精确停止本轮5186/5187四个已核对的预览父子进程，剩余进程和监听端口均0，5181只读GET仍HTTP200；验证标签关闭并恢复浏览器视口。进程盘点首次普通权限拒绝访问、重启时首次身份核验因venv父子进程为两项而主动停止操作，随后按实际命令行确认父子关系后仅清理本轮进程，没有触碰5181或其他服务。两次隔离自检的临时目录权限限制均以原命令授权重跑，最终保留原临时隔离设计和完整静态校验，失败遗留目录已按精确路径清理。证据/截图继续保留在忽略目录，交付后不自动加载或部署候选产物。

### 13.9 用户授权加载操作日志前端供审阅与试用

2026-10-04 用户追加“请重新启动项目，我来进行审阅和试用”，授权将13.8已验证的新版操作日志加载到原5181。只读核对AGENTS、README、前端规范和M27运行记录、274项Git状态及当前容器标签：沿用`learning-lab-v1-verify-8e9c1a0a0101`，六个服务运行、三个退役教学服务停止。此前“不自动加载”的记录保留其历史范围。本次只替换frontend，不重新启动API、Worker/reconciler、数据库、Redis或其他实例，不执行迁移、业务写入、模型调用或Git写操作。

本轮在忽略目录`.runtime/operation-log-review-20261004-af4dbf71`建立独立维护入口和新鲜基线，保留原镜像。复用实际容器标签确认的十一层Compose配置并追加本轮唯一前端镜像；保存源码及相关配置哈希，不读取根.env或输出凭据。更新前以无网络、只读、无挂载的一次性容器校验新镜像HTML/JS/CSS的SHA-256与13.8最终已测dist完全相同。辅助入口增加一次原前端镜像恢复和异常证据保留，本次更新成功，没有触发或人为演练故障恢复分支。

根目录实际执行Python AST语法检查、配置基线/源码一致性检查，以及以下命令，均退出0。`P`沿用13.8的Python路径，`D`为`C:/Program Files/Docker/Docker/resources/bin/docker.exe`：

```text
P -B -X utf8 .runtime/operation-log-review-20261004-af4dbf71/update_frontend.py prepare --docker D --checks-passed
P -B -X utf8 .runtime/operation-log-review-20261004-af4dbf71/update_frontend.py build --docker D --checks-passed
P -B -X utf8 .runtime/operation-log-review-20261004-af4dbf71/update_frontend.py update --docker D --checks-passed
```

仅执行frontend的`compose up -d --no-deps --no-build --pull never --wait --wait-timeout 90`。内置verify通过：34表全字段/逐行摘要、迁移清单、60个内部源码对象、6卷3网、所有非前端及其他实例的容器身份/状态均保持，模型配置仍关闭。项目摘要、活动、日志统计三个只读接口HTTP200，实时HTML及`index-eGDA_kGu.js`、`index-Bl-oKy9f.css`哈希与已测产物一致，CSP保持；根地址单独GET也为HTTP200。结果为本轮目录的`verified-5abe6afd8ab24c0ba539337dfca44a9f.json`。本次没有业务源码改动，不重复13.8的37项组件测试和完整业务回归。

实际浏览器读取20条现有日志，默认每页20；1243×699视口页面scrollWidth为1243，固定浅色，控制台error为0。点击详情确认10个完整字段、一个“操作详情”标题和599.99px宽抽屉；Escape关闭后焦点回到原详情按钮。已显示并保留`http://127.0.0.1:5181/?section=jobs`供用户审阅，运行栈继续保留。截图为本轮目录`browser-ready.jpg`，结构化证据为`browser-proof.json`。

项目记忆仅在本节同步追加授权、实际前端加载和保护验证；历史启动记录按当前退役状态与本次前端范围核对，没有恢复旧服务。未发现独立项目记忆文件，未创建新记忆系统或写中央记忆。最终源码/配置一致性、Git状态与增量审阅及`git diff --check`通过；除本节文档和忽略目录维护材料外，无新增改动。真实用户试用结论待反馈，模型外发仍未启用。

### 13.10 浏览器批注：移除顶部搜索与筛选蓝框

2026-10-04 用户在当前5181批注要求移除顶部搜索栏，结果选择及开始日期筛选去掉蓝框。读取AGENTS、前端规范、当前M27记录和真实调用/样式来源，核对274项工作区状态后给出限定实施计划；在忽略目录`.runtime/review-comments-20261004-1450`保存八个涉及文件的原字节副本及Git状态/HEAD。未从HEAD重建或覆盖已有修改。批注标记自身的蓝框属于浏览器工具，本轮修改真实页面聚焦状态；不改全局焦点规则、后端、接口、权限或依赖。

- `MainlineWorkspace`取消顶部`WorkspaceSearch`挂载，`WorkspaceShell`移除搜索插槽、备用输入和对应Ctrl/Meta+K拦截。源码原`search/setSearch`及页内搜索、项目搜索和日志搜索保持；旧独立搜索组件和历史测试未删除。桌面继续等宽两翼居中三入口，768–1279px保留第二行导航，手机顶栏104px改为64px且不留搜索空行。
- 只在`.operation-filter-dialog`覆盖原生select聚焦轮廓和DatePicker聚焦/悬停的主色边框、阴影，改用`--muted`中性色边框。自动聚焦、Tab、中文日历、应用/清除、Escape及焦点恢复保持；筛选已应用状态、按钮和日历选中日的主题色保持。
- 外壳测试调整为新授权行为：顶部无搜索，Ctrl/Meta+K不阻止默认行为、不抢局部焦点或修改草稿，菜单和导航保持；工作区集成断言确认顶部不再挂载输入。未删除或弱化不相关行为测试。

frontend实际执行以下最终命令，全部退出0。`N`为根目录`.runtime/tools/node-v24.21.0-win-x64/node.exe`；完整测试3文件56/56通过，53.79s，包含日志原37项回归。子代理预先启动的Shell单文件检查也7/7通过；根代理默认沙箱首次Vite启动遇到`spawn EPERM`，以相同完整测试命令正常权限重跑通过。保留jsdom伪元素计算样式和既有大包警告，未改测试环境或拆包。

```text
N node_modules/vitest/vitest.mjs run src/app/WorkspaceShell.test.tsx src/app/WorkspacePage.test.tsx src/features/jobs/OperationLogs.test.tsx --reporter=dot --reporter=json --outputFile ../.runtime/review-comments-20261004-1450/vitest-final.json
N node_modules/typescript/bin/tsc --noEmit
N node_modules/eslint/bin/eslint.js src/app/MainlineWorkspace.tsx src/app/WorkspaceShell.tsx src/app/WorkspaceShell.test.tsx src/app/WorkspacePage.test.tsx --max-warnings 0
N node_modules/prettier/bin/prettier.cjs --check src/app/MainlineWorkspace.tsx src/app/WorkspaceShell.tsx src/app/WorkspaceShell.test.tsx src/app/WorkspacePage.test.tsx src/app/shell-redesign.css src/features/jobs/OperationLogs.css
N node_modules/vite/bin/vite.js build
```

沿用用户本次试用和浏览器批注授权，在本轮独立忽略目录创建前端维护入口。AST检查及不执行Docker的Compose顺序检查退出0；实际prepare从当前frontend标签保存完整有序十一层Compose来源，更新/恢复只在其末尾追加对应覆盖，避免固定旧链遗漏已载入的覆盖。没有修改旧辅助脚本或现有配置。根目录实际依次执行以下三个命令，均退出0，`P/D`沿用13.9。原镜像保留，更新前无网络只读容器核验镜像资源哈希，然后仅frontend执行`up -d --no-deps --no-build --pull never --wait --wait-timeout 90`；没有停止API或后台任务服务。

```text
P -B -X utf8 .runtime/review-comments-20261004-1450/update_frontend.py prepare --docker D --checks-passed
P -B -X utf8 .runtime/review-comments-20261004-1450/update_frontend.py build --docker D --checks-passed
P -B -X utf8 .runtime/review-comments-20261004-1450/update_frontend.py update --docker D --checks-passed
```

内置verify通过：34表全字段/逐行摘要、迁移清单、60内部源码对象、6卷3网、全部非前端和其他实例容器身份/状态、CSP均保持，模型配置仍关闭；三个只读接口HTTP200，根地址GET为200。实时HTML、`index-CObE4T6g.js`和`index-DM5Zxpj8.css`与最终已测dist哈希一致。仅前端容器改变；故障恢复分支未触发，未人为故障演练。

实际浏览器验证当前真实实例：1297×928视口无顶部输入，主导航中心648.54px、视口中线648.5px，页面scrollWidth为1297，仍读取20条日志。结果select改造前聚焦outline为主色实线；日期框稳定聚焦为`rgb(23,103,216)`并带2px阴影。改造后两个控件聚焦均为`rgb(93,112,149)`边框、无outline和shadow，焦点保留。选择失败并应用得到4条，选中文日历10月4日并内部确定/外层应用得到2条；清除分别恢复20条，应用/日期Escape均返回对应表头按钮。项目管理页顶部无搜索，页内“搜索项目”继续可见。

手机请求390×844、实际CSS视口379×819：页面scrollWidth为379，顶栏63.99px，无顶部输入；菜单三入口可用，Escape回到“功能导航”。操作日志20条、页容量选择仍可见；局部滚动至219.81px后分页底部743.84px，末项可达。恢复原桌面窗口后局部scrollTop为0、列表保持未筛选20条，控制台error为0，页面保留供继续试用。前后及详情控件截图为本轮目录`before-page.jpg`、`before-result.jpg`、`before-date.jpg`、`after-page.jpg`、`after-projects.jpg`、`after-result.jpg`、`after-date.jpg`和`after-mobile.jpg`，结构化证据为`browser-before.json`、`browser-proof.json`。

项目记忆同步：前端规范v0.37修正当前顶栏和筛选焦点规则，本节是唯一追加实现/验证记录；此前搜索快捷键和蓝框证据保留其历史范围。未发现独立项目记忆文件，未创建新记忆系统或写中央记忆。本轮仅八个约定源码/测试/文档文件有增量，274项状态条目集合及HEAD保持，完整增量已审阅，`git diff --check`通过。没有真实任务写入、删除、清空或模型调用；未重复后端、压力和完整业务回归，真实用户试用结论仍待反馈。

### 13.11 工作区填满可用空间与移除外壳底栏（2026-10-04）

用户继续在5181源码页批注，要求工作区扩展至剩余空白并删除底部说明。先读取AGENTS、当前前端规范与本阶段记录，核对现有274项工作区状态和flex/grid高度链；无更深指令或独立项目记忆文件。本轮在`.runtime/workspace-fill-20261004-1640/baseline`保存五个约定文件的原始字节，Git状态与HEAD另存，保护已有修改。按PLAN→EXECUTE→TEST→DELIVER实施。

实现仅移除`WorkspaceShell`的外壳说明footer及其桌面/手机样式，为`data-category=project`的`shell-main`取消外层padding。五个工作区面板沿原高度链获得空间，项目管理和日志保留原外边距。面板内部间距、源码状态/跳行footer、窄屏文件树和矮屏局部滚动不变，无新增依赖或业务动作。测试增加三入口移除说明栏且保留正文footer的断言，既有断言保持。

前端目录使用`N=../.runtime/tools/node-v24.21.0-win-x64/node.exe`，实际执行以下检查。最终五文件36/36通过（Shell 10、Page 12、SourceWorkspace 4、SourceViewer 7、ScrollPanel 3），类型/lint/格式/构建均退出0。首轮新增测试错误地要求所有contentinfo消失，误计入夹具源码footer；修正为只保留正文footer后重跑通过，没有修改既有测试期望。首次格式检查发现新增测试换行，仅该测试执行`prettier --write`后复查通过。Vitest与Vite最初在沙箱被`spawn EPERM`阻止，原命令以正常本地进程权限重跑；构建仍提示既有大于500kB资源块，未扩大范围拆包。

```text
N node_modules/vitest/vitest.mjs run src/app/WorkspaceShell.test.tsx src/app/WorkspacePage.test.tsx src/features/projects/SourceWorkspace.test.tsx src/features/projects/SourceViewer.test.tsx src/shared/components/ScrollPanel.test.tsx --reporter=dot --reporter=json --outputFile ../.runtime/workspace-fill-20261004-1640/vitest-final.json
N node_modules/typescript/bin/tsc --noEmit
N node_modules/eslint/bin/eslint.js src/app/WorkspaceShell.tsx src/app/WorkspaceShell.test.tsx --max-warnings 0
N node_modules/prettier/bin/prettier.cjs --check src/app/WorkspaceShell.tsx src/app/WorkspaceShell.test.tsx src/app/shell-redesign.css
N node_modules/vite/bin/vite.js build
```

依照既有试用及连续批注授权，仅载入前端。本轮维护入口由上轮已测工具复制，仅调整中文说明、镜像前缀和本轮覆盖名字；Python AST、三处标识增量及不执行Docker的内存Compose顺序检查均退出0。实际prepare保存当前完整有序十二层Compose来源，更新/恢复只在末尾追加本轮覆盖；旧辅助文件和部署源码未改。根目录依次执行以下命令，均退出0；`P=.runtime/m1-t02-venv/Scripts/python.exe`、`D=C:/Program Files/Docker/Docker/resources/bin/docker.exe`。镜像资产无网络只读核验后，仅frontend执行`up -d --no-deps --no-build --pull never --wait --wait-timeout 90`，原镜像保留。没有停止API、Worker或reconciler。

```text
P -B -X utf8 .runtime/workspace-fill-20261004-1640/update_frontend.py prepare --docker D --checks-passed
P -B -X utf8 .runtime/workspace-fill-20261004-1640/update_frontend.py build --docker D --checks-passed
P -B -X utf8 .runtime/workspace-fill-20261004-1640/update_frontend.py update --docker D --checks-passed
```

内置verify通过：34表完整字段/逐行摘要、22项迁移、60内部源码对象、6卷3网、所有非前端及其他实例容器身份/状态保持，模型配置仍关闭，CSP不变。三个原只读接口和根资源GET为200；实时HTML、`index-By209Kvj.js`与`index-CltnOvj9.css`哈希匹配已测dist。仅前端容器改变；恢复分支没有触发，未人为故障演练。

实际浏览器验证当前真实实例：同尺寸1297×928改造前工作区约1249×798、x24/y84，底栏约26px；改造后工作区约1297×864、x0/y64，top与header.bottom一致，右/底边与视口在0.5px舍入范围内一致，padding为0，外壳footer为0。源码、接口、关系、知识、讲解五面板切换后均保持该几何与项目/快照/分析/源码引用。项目管理及操作日志仍为20px×24px外边距。手机请求390×844、实际379×819，平板请求1000×800、实际971×777：工作区均贴合顶栏和视口边界，无页面横向溢出；手机键盘Enter关闭文件树后焦点回“项目结构”。矮屏请求1297×480、实际1260×466，局部滚动198.06px后源码状态栏底部406.27px，跳转34成功显示末行。宽桌面请求1700×928、实际1650×901，双窗口可见，主窗滚动368.93px时副窗保持0，末行可达。

浏览器另发现既有分屏断点冲突：未改动的`workspace.css`在≤1599px隐藏其中一窗，而`SourceWorkspace.css`仅在≤1200px显示切换导航；1297px实测副窗display:none且切换导航display:none。用户本轮仅要求外框填满与删除底栏，未扩大范围修复该既有问题；因此不宣称1201–1599px分屏正常。结构化证据包含此限制。控制台error为0；恢复原1297×928窗口、源URL及1–34行引用，外层/源码scrollTop均为0，页面保留供审阅。本轮同尺寸前后截图`before.jpg`/`after.jpg`及`after-split.jpg`、`after-mobile.jpg`、`after-short.jpg`均位于本轮忽略目录，几何与交互证据见`browser-before.json`和`browser-proof.json`。

项目记忆同步：前端规范v0.38明确移除说明栏、五工作区满宽高及内部滚动边界，本节是唯一新增实现/验证记录；此前底栏和布局描述保留历史范围。没有新增记忆系统或写中央记忆。本轮五个约定文件增量完成审阅，274项状态集合与HEAD保持，`git diff --check`通过；独立只读审阅也未发现本轮增量问题。未操作真实任务、删除、清空、模型外发或Git写入；未重复后端、压力、完整业务回归或故障恢复演练，真实用户试用待反馈。

### 13.12 源码标题收缩与目录宽度拖拽（2026-10-04）

用户继续在5181源码页批注，要求标题区仅保留项目名称并允许拖拽目录/代码边界。先读取AGENTS、前端规范和本阶段记录，核对274项已有工作区状态、源码入口与快照隔离、隐藏面板和高度链。没有更深指令或独立项目记忆文件。本轮在`.runtime/source-space-20261004-1730/baseline`保存八个既有文件原始字节，登记新增hook原本不存在，并另存Git状态与HEAD，按PLAN→EXECUTE→TEST→DELIVER实施。

源码专属标题仅呈现项目名称一行，长名省略且title保留全文；约38px高度替代原约111px。其他四面板的快照、统计及命名入口和项目管理命名保持，异常识别/多根/恢复状态仍由原独立状态区承担。目录默认260px，在180–480px内调整，12px分隔条给代码保留至少320px，上限随实际容器宽度变化。复用CSS网格与Pointer Events，不增加依赖；相比已安装Splitter，自有局部hook可以明确处理可访问键盘、取消和隐藏会话。尺寸仅保留在当前快照会话，不写URL或持久存储，普通切页/文件保持，父快照key重建恢复默认。

分隔条支持左键主指针、捕获与异指针隔离，释放消费最后坐标；Escape、pointercancel、lostpointercapture、窗口失焦、后台隐藏、不可用容器和卸载取消，恢复起始偏好并清理监听/观察器。键盘方向键10px、Shift加速40px及Home/End边界；ARIA上下界/当前值、关联区域、中文名称和提示与实际限制一致。140ms颜色反馈及局部减少动态规则，不对宽度加动画。手机或容器不足512px使用原单实例覆盖树，不重建源码DOM。

前端目录使用`N=../.runtime/tools/node-v24.21.0-win-x64/node.exe`，实际执行如下。最终五文件57/57通过（Shell 10、Page 18、SourceWorkspace 19、SourceViewer 7、ScrollPanel 3），新增6项标题及15项分隔条行为验证；原断言保留。类型、lint、格式和构建均退出0。首次新增测试helper使用EventTarget过宽导致TS2345，收紧为Node或Window后类型通过；首轮回归56通过、1失败，新增源码文字查询无法跨着色span命中，改为PRE节点完整textContent匹配后同命令57项通过，没有改实现或弱化内容断言。Vitest/Vite最初在沙箱遇到spawn EPERM，原命令以正常本地进程权限重跑；代理一个无结果的重复等待被取消，不作为通过证据。构建保持既有大于500kB资源块提示，未扩大范围拆包。

```text
N node_modules/vitest/vitest.mjs run src/app/WorkspacePage.test.tsx --reporter=dot --reporter=json --outputFile ../.runtime/source-space-20261004-1730/vitest-page.json
N node_modules/vitest/vitest.mjs run src/app/WorkspaceShell.test.tsx src/app/WorkspacePage.test.tsx src/features/projects/SourceWorkspace.test.tsx src/features/projects/SourceViewer.test.tsx src/shared/components/ScrollPanel.test.tsx --reporter=dot --reporter=json --outputFile ../.runtime/source-space-20261004-1730/vitest-final.json
N node_modules/typescript/bin/tsc --noEmit
N node_modules/eslint/bin/eslint.js src/app/MainlineWorkspace.tsx src/app/WorkspacePage.test.tsx src/features/projects/SourceWorkspace.tsx src/features/projects/SourceWorkspace.test.tsx src/features/projects/useSourceTreeResize.ts --max-warnings 0
N node_modules/prettier/bin/prettier.cjs --check src/app/MainlineWorkspace.tsx src/app/mainline.css src/app/WorkspacePage.test.tsx src/features/projects/SourceWorkspace.tsx src/features/projects/SourceWorkspace.css src/features/projects/SourceWorkspace.test.tsx src/features/projects/useSourceTreeResize.ts
N node_modules/vite/bin/vite.js build
```

新增测试查询修正后，重复执行tsc及该测试文件的eslint/prettier检查均退出0。源码页标题三文件和目录四文件分别执行prettier --write，最后局部CSS修正仅执行对应prettier --check及Vite构建，均退出0；未格式化其他前端文件。

沿既有试用与连续批注授权，仅载入前端。维护工具复制上轮入口，只替换中文说明、唯一镜像前缀和本轮覆盖名，规范化Python AST和旧辅助字节核对通过。首次prepare使用完整有序13层Compose来源。首次浏览器在826×777发现旧workspace.css的≤1199px目录隐藏/绝对定位及30px网格行干扰新三列；在SourceWorkspace.css局部补充单行网格和非覆盖目录的静态定位/尺寸，不改全局文件或旧分屏规则。格式及生产构建通过后，新建`.runtime/source-space-20261004-1730-r2`维护目录，新鲜prepare保留当前14层来源；未覆盖首次证据。第二维护入口同样仅三处标识替换，AST核对通过。根目录两个维护目录分别依次执行以下三个action，六次命令均退出0；`P=.runtime/m1-t02-venv/Scripts/python.exe`、`D=C:/Program Files/Docker/Docker/resources/bin/docker.exe`。

```text
P -B -X utf8 .runtime/source-space-20261004-1730/update_frontend.py prepare --docker D --checks-passed
P -B -X utf8 .runtime/source-space-20261004-1730/update_frontend.py build --docker D --checks-passed
P -B -X utf8 .runtime/source-space-20261004-1730/update_frontend.py update --docker D --checks-passed
P -B -X utf8 .runtime/source-space-20261004-1730-r2/update_frontend.py prepare --docker D --checks-passed
P -B -X utf8 .runtime/source-space-20261004-1730-r2/update_frontend.py build --docker D --checks-passed
P -B -X utf8 .runtime/source-space-20261004-1730-r2/update_frontend.py update --docker D --checks-passed
```

两次内置verify均通过：34表完整字段/逐行摘要、22项迁移、60内部源码对象、6卷3网、全部非前端与其他实例容器身份/状态和CSP保持，模型配置仍关闭；三个只读接口HTTP200。每次无网络只读核对镜像资产后，仅frontend执行up --no-deps --no-build --pull never --wait；原镜像保留，没有停止API/Worker/reconciler。最终实时HTML、index-CLSvGd7d.js和index-wcH0_UgB.css与已测最终dist一致。未触发或人为演练故障恢复分支。

真实5181浏览器：1297×928视口，源码标题110.63px→38.00px，仅一个项目名称子节点；源码行容器493.86px→566.49px，增加72.63px。最终实际拖拽260→400px时URL保持，前后scrollTop同为97.0874px；源码高度稳定、没有重读闪烁。初版实际键盘ArrowLeft/Shift+ArrowRight由400到430，Home/End到180/480；切接口后仍有原快照/统计/命名，返回源码恢复480px偏好和原滚动。最终版桌面键盘同样可恢复260px默认。

最终版窄窗口请求850×800、实际826×777，两栏都正常显示，上限384px时目录383.99px、代码320.11px、源码行容器280.08px；缩小约束并在放大时恢复480px偏好。手机请求390×844、实际379×819，标题38px、源码可视283.06px，页面scrollWidth379、无横向溢出；原目录覆盖层打开可见，实际发送到当前焦点的Escape关闭后焦点返回项目结构。自动化指定目标的Return/Enter/部分click尝试仅聚焦或未产生状态变化，改用新鲜AX的原生点击与当前焦点Escape后观察到结果，不把先前尝试记为键盘激活通过。矮窗口请求1297×480、实际1260×466，源码仍有181.87px可视区域，通过可用跳转入口到34行，实际显示27–34行。恢复原1297×928视口、1–34行源码URL、默认260px目录及约97.09px源码滚动，控制台error为0，页面保留供试用。

截图before.jpg/after.jpg为同尺寸前后，after-drag.jpg、after-narrow.jpg、after-mobile.jpg、after-mobile-tree.jpg和after-short.jpg及结构化browser-before.json/browser-proof.json均在本轮忽略目录。浏览器验证使用真实只读接口；模拟PointerEvent/ResizeObserver的取消、后台隐藏、极窄容器、捕获失败、卸载清理及节点/scrollLeft保留属于组件测试，未冒称真实指针中断。减少动态规则已检查，未切换系统偏好实测。13.11所述1201–1599px既有分屏断点限制保持，未扩大范围修复；未宣称该区间分屏通过。

项目记忆同步：前端规范v0.39更新单行源码标题、260px默认值、分隔条尺寸/键盘/取消/减少动态及局部样式边界，核对并纠正此前约280px与实际260px不一致；本节为唯一追加实现与验证记录，没有建立新记忆系统或写中央记忆。最终九个约定源码/测试/文档文件有增量；原274项Git状态条目和HEAD保持，仅新增hook带来275项状态，完整本轮增量已审阅，git diff --check通过，独立只读审阅未发现新阻塞。未操作真实任务、删除、清空、模型外发或Git写入，未重复后端、压力、完整业务回归及真实用户试用结论。

### 13.13 源码紧凑布局与中文路径提示（2026-10-04）

用户追加IDE布局参考和四项浏览器批注：移除目录标题、筛选输入及接收计数，折叠/定位提供中文悬浮提示，文件名显示以项目为根的相对路径。先读取AGENTS、前端规范及本阶段当前记录，核对275项已有工作区状态、源码调用方、文件身份、焦点和局部样式；无更深指令或独立项目记忆文件。六个约定文件包含已有未跟踪源码，其原始字节与Git状态/HEAD保存在`.runtime/source-ide-20261004-173309/baseline`及同目录记录中，按PLAN→EXECUTE→TEST→DELIVER实施。参考图用于结构，沿用已确认的固定浅色。

左侧移除旧“项目文件”标题、筛选和接收计数，保留紧凑折叠/定位工具；生产调用方移除独立search状态。右侧将分屏、解读和快照信息并入文件标签栏，取消另占一行的路径面包屑；源码状态、跳行及相关依据保持。目录和标签的悬浮/键盘聚焦提示直接使用服务端已有file_path，不拼接本机绝对目录；关闭和固定入口同样有中文说明。复用Ant Design Tooltip，局部160/120ms淡化和150ms颜色反馈，不新增依赖。源码页将来源行视觉收起，保留屏幕阅读器文本并提供信息提示，不改共享SourceViewer或其他消费者。

“＋”通过本实例引用打开目录并聚焦当前文件、首个目录或空树容器；窄屏Escape、关闭和选文件后返回实际打开按钮。焦点请求在可取消定时任务内完成，隐藏及卸载不向其他实例/旧输入恢复焦点。空树折叠和无有效文件定位不可执行；既有文件身份去重、关闭邻近标签、双窗口引用、快照隔离、200行块/每窗1000行上限及目录拖拽规则保持。减少动态时停用颜色过渡，提示淡化缩至1ms且保留结束事件，避免全局animation:none触发组件1000ms兜底期限。

前端目录使用`N=../.runtime/tools/node-v24.21.0-win-x64/node.exe`，实际执行如下。最终五文件65/65通过（SourceWorkspace 27、SourceViewer 7、Page 18、Shell 10、ScrollPanel 3），保留原19项源码工作区测试并补充8项提示/精简结构/焦点/空树验证；类型、lint、格式及生产构建均退出0。

```text
N node_modules/vitest/vitest.mjs run src/features/projects/SourceWorkspace.test.tsx src/features/projects/SourceViewer.test.tsx src/app/WorkspacePage.test.tsx src/app/WorkspaceShell.test.tsx src/shared/components/ScrollPanel.test.tsx --reporter=dot --reporter=json --outputFile ../.runtime/source-ide-20261004-173309/vitest-final.json
N node_modules/typescript/bin/tsc --noEmit
N node_modules/eslint/bin/eslint.js src/features/projects/SourceWorkspace.tsx src/features/projects/SourceWorkspace.test.tsx src/app/MainlineWorkspace.tsx --max-warnings 0
N node_modules/prettier/bin/prettier.cjs --check src/features/projects/SourceWorkspace.tsx src/features/projects/SourceWorkspace.css src/features/projects/SourceWorkspace.test.tsx src/app/MainlineWorkspace.tsx
N node_modules/vite/bin/vite.js build
```

首轮完整测试62通过/3失败：jsdom不执行CSS动画，新增提示关闭断言的默认1000ms等待短于组件兜底期限和移出延迟；改为2000ms等待，保留“提示已消失”的完整断言。焦点移到可取消定时任务，修复Tooltip在effect内聚焦产生的flushSync警告；同命令重跑65项通过，无该警告。新增源码文字断言按PRE完整textContent匹配着色内容，同名文件路径分别验证。窄套件最初spawn EPERM，代理一个无结果的重复等待已取消，不作为通过证据；完整Vitest及Vite以正常本地进程权限执行。仅四个约定前端文件执行过prettier --write。最终局部CSS修正后重新执行对应格式检查与Vite构建，退出0；构建仍有既有大于500kB资源块提示，未扩大范围拆包。

沿连续审阅授权将候选前端载入5181。维护工具复制既有入口，仅替换中文说明、唯一镜像前缀和本轮覆盖名，规范化Python AST及旧工具字节核对通过。首次prepare保留完整有序15层Compose来源。第一次真实渲染发现通用icon-button规则重新显示桌面关闭目录按钮，以及“＋”继承默认按钮padding扩大标签栏；只在本页CSS补充非覆盖模式隐藏规则和padding/line-height重置。构建通过后使用独立r2维护目录，新鲜prepare保留当前16层来源，不覆盖首次证据。根目录实际依次执行六次命令，均退出0；`P=.runtime/m1-t02-venv/Scripts/python.exe`、`D=C:/Program Files/Docker/Docker/resources/bin/docker.exe`。

```text
P -B -X utf8 .runtime/source-ide-20261004-173309/update_frontend.py prepare --docker D --checks-passed
P -B -X utf8 .runtime/source-ide-20261004-173309/update_frontend.py build --docker D --checks-passed
P -B -X utf8 .runtime/source-ide-20261004-173309/update_frontend.py update --docker D --checks-passed
P -B -X utf8 .runtime/source-ide-20261004-173309-r2/update_frontend.py prepare --docker D --checks-passed
P -B -X utf8 .runtime/source-ide-20261004-173309-r2/update_frontend.py build --docker D --checks-passed
P -B -X utf8 .runtime/source-ide-20261004-173309-r2/update_frontend.py update --docker D --checks-passed
```

两次内置verify通过：34表完整字段/逐行摘要、22项迁移、60内部源码对象、6卷3网、所有非前端及其他实例容器身份/状态、关闭的模型配置和CSP保持。三个原只读接口HTTP200。无网络只读核对镜像资产后仅frontend执行up --no-deps --no-build --pull never --wait，API/Worker/reconciler未停止，旧镜像保留；最终实时HTML、index-C8kvSJ3a.js和index-D19YjJtN.css与已测dist一致。未触发或演练故障恢复分支。

真实5181浏览器同尺寸1297×928：标签栏约51.50→36.00px，代码可视高度566.49→663.26px，增加96.77px；目录从y240.35上移至y141.52。桌面关闭目录入口不显示，悬浮折叠/定位显示中文提示，目录及文件标签悬浮显示backend/config/urls.py相对路径，离开后提示消失。最终实际拖拽260→360px，源码非零scrollTop均为118.835px，scrollLeft和URL保持；键盘恢复默认260px。

窄窗口请求850×800、实际826×777，两栏可见、页面宽826、代码可视463.81px。手机请求390×844、实际379×819，无页面横向溢出；“＋”实际打开覆盖树并聚焦当前文件，Escape和可见关闭按钮分别关闭后回到“从文件树打开文件”，源码滚动保持。宽桌面请求1700×928、实际1650×901，将另一同名urls.py固定后两窗均可见、各约627.71px，引用分别为backend/config/urls.py与backend/apps/tasks/api/urls.py。矮屏请求1297×480、实际1260×466，代码可视278.64px；通过原工作区局部滚动125.05px，状态/跳行栏底部到406.65px可达，未用裁切让内容消失。

验证结束恢复1297×928、原项目/快照/分析/1–34行URL、单个原文件标签、默认260px目录及118.835px源码滚动，外层scrollTop为0，控制台error为0，页面保留供试用。同尺寸before-desktop.png/after-desktop.png及after-path-tooltip.png、after-drag.png、after-narrow.png、after-mobile.png、after-mobile-tree.png、after-split.png、after-short.png与browser-proof.json位于本轮忽略目录。组件测试覆盖原分隔条隐藏/卸载清理、空树和两个实例的焦点隔离，不能替代真实指针中断验证；新增焦点定时任务的隐藏防护和取消逻辑经过源码审阅。减少动态CSS已审阅，未切换系统偏好实测；13.11所述1201–1599px既有分屏断点限制保持，未宣称该区间通过。没有触发真实任务恢复、删除、清空或模型外发，未重复后端、压力、完整业务回归或真实用户试用验收。

项目记忆同步：前端规范v0.40明确精简源码布局、中文路径提示、焦点恢复及局部减少动态规则，并纠正当前“源码目录筛选继续保留”的旧说明；历史章节保留其原阶段范围。本节为唯一新增进度/验证记录，没有建立新记忆系统或写中央记忆。

最终六个约定文件的字节基线增量完成审阅，275项Git状态条目集合与HEAD保持，git diff --check通过；独立只读增量审阅未发现本轮新阻塞。运行证据均在忽略目录，无后端、接口、依赖、部署源码或Git写入改动。

### 13.14 源码缩略图悬浮显示与实际定位（2026-10-04）

用户在5181源码页批注，要求右侧缩略图仅在悬浮代码时出现，点击对应区域可以跳转。先读取AGENTS、前端规范及本阶段当前记录，核对275项已有工作区状态、共享SourceViewer调用方、分块读取与滚动、原焦点和局部样式。未找到更深指令或独立项目记忆文件。在`.runtime/source-minimap-20261004/baseline`保存五个约定源码/测试/文档的原始字节（包含已有未跟踪源码），另存Git状态和HEAD，按PLAN→EXECUTE→TEST→DELIVER实施。

缩略图默认隐藏，仅对应源码阅读区悬浮或键盘focus-visible时显示，鼠标移入缩略图仍可操作；150ms淡化可直接打断，离开立即停用指针事件。保留68px占位、源码DOM及原手机隐藏规则，不改变代码尺寸或两轴滚动；双窗独立。键盘可从原工具栏进入代码区、Tab到缩略图并激活定位，移出阅读区后隐藏。减少动态时取消该过渡。仅增加本页CSS，不增加依赖或全局样式。

保留已加载范围坐标映射，未加载空隙定位最近已加载块，不预读全文。检查及真实短文件观察发现旧状态栏可能显示7–14行，但实际scrollTop为0；定位末尾也可能因浏览器滚动上限而反馈错误首行。因此共享SourceViewer首次有效尺寸才恢复引用，隐藏窗口不以0高度初始化；后续resize和定位按浏览器实际scrollTop更新视口。显式跳行仍传递用户请求行的引用，来源信息展示、200行请求/每窗1000行渲染上限、缓存、取消和迟到结果保护保持。

前端目录使用`N=../.runtime/tools/node-v24.21.0-win-x64/node.exe`，实际执行如下。最终三文件58/58通过（SourceViewer 13、SourceWorkspace 27、Page 18），原7项SourceViewer测试及其断言保留，新增6项覆盖坐标顶部/中部/底部、越界/零高度、加载空隙、双实例、短文件/末尾模拟滚动上限和隐藏后首次测量/resize。类型、lint、格式及生产构建均退出0。

```text
N node_modules/vitest/vitest.mjs run src/features/projects/SourceViewer.test.tsx src/features/projects/SourceWorkspace.test.tsx src/app/WorkspacePage.test.tsx --reporter=dot --reporter=json --outputFile ../.runtime/source-minimap-20261004/vitest-final.json
N node_modules/typescript/bin/tsc --noEmit
N node_modules/eslint/bin/eslint.js src/features/projects/SourceViewer.tsx src/features/projects/SourceViewer.test.tsx --max-warnings 0
N node_modules/prettier/bin/prettier.cjs --check src/features/projects/SourceViewer.tsx src/features/projects/SourceViewer.test.tsx src/features/projects/SourceWorkspace.css
N node_modules/vite/bin/vite.js build
```

首轮同套件57通过/1失败，新增测试对继承滚动访问器的spy清理留下自身描述符，干扰原5000行测试；保存并还原/移除对应自身描述符后，同套件58项通过，没有弱化原断言。初始和最终JSON分别保留为vitest-initial.json/vitest-final.json。测试修正后重新执行上述类型、lint和格式检查，均通过。仅三个约定前端文件执行局部prettier --write。Vitest及Vite沿Windows已核实的子进程权限要求，以正常本地进程权限执行；本轮未重新遭遇spawn EPERM。构建仍有既有大于500kB资源块提示，未扩大范围拆包。

沿连续审阅授权仅载入前端。维护工具复制既有r2入口，只替换中文说明、唯一镜像前缀和本轮覆盖名，规范化Python AST、三处标识增量及旧工具字节核对通过。新鲜prepare保留完整有序17层Compose来源，在其末尾追加本轮忽略目录覆盖，不改部署源码。根目录以下四次命令均退出0；`P=.runtime/m1-t02-venv/Scripts/python.exe`、`D=C:/Program Files/Docker/Docker/resources/bin/docker.exe`。

```text
P -B -X utf8 .runtime/source-minimap-20261004/update_frontend.py prepare --docker D --checks-passed
P -B -X utf8 .runtime/source-minimap-20261004/update_frontend.py build --docker D --checks-passed
P -B -X utf8 .runtime/source-minimap-20261004/update_frontend.py update --docker D --checks-passed
P -B -X utf8 .runtime/source-minimap-20261004/update_frontend.py verify --docker D
```

prepare/build/update退出0，内置verify通过：34表完整字段/逐行摘要、22项迁移、60内部源码对象、6卷3网、所有非前端及其他实例容器身份/状态、关闭的模型配置与CSP保持。三个原只读接口HTTP200。无网络只读核对镜像资产后，仅frontend执行up --no-deps --no-build --pull never --wait，API/Worker/reconciler未停止，旧镜像保留；实时HTML、index-5pdZZacB.js和index-BFIVaVHD.css匹配本轮已测dist。未触发或人为演练恢复分支。浏览器验证后再次执行独立verify，退出0，数据、资产与所有保护项保持。

真实5181浏览器同尺寸1297×928：默认缩略图opacity为0、visibility为hidden、pointer-events为none，悬浮对应代码区后为1/visible/auto；移入图上继续显示，点击后移出也隐藏。前后代码宽844.45px、高663.26px，短文件scrollTop/scrollLeft均为0；旧错误反馈7–14行改为实际1–14行。短文件已全部可见时点击不会伪造实际滚动。

同实例34行urls.py可滚动文件，点击缩略图约10%位置实际scrollTop为69.13px、显示4–32行；点击底部为119.61px、显示6–34行，符合浏览器上限。键盘从工具栏Tab进入代码区使图出现，再Tab到图按钮，Enter将119.61px回到0、显示1–29行；Tab离开后图隐藏。宽桌面请求1700×928、实际1650×901，主窗悬浮时仅主图显示，点击主图实际滚动199.61px、副窗仍0；移入副窗仅副图显示，主窗滚动保持。

窄窗口请求850×800、实际826×777：代码宽385px，横向浏览稳定后scrollTop146.80px、scrollLeft293.59px，悬浮/离开两态保持相同位置和尺寸。首个滚动采样仍在动画过程中，最终以稳定后的两态证据为准。手机请求390×844、实际379×819，缩略图仍display:none，不新增触摸定位入口。验证结束清除窗口覆盖，恢复原1297×928、项目/快照/分析和services.py的1–14行URL、原三个文件标签顺序及248px目录，源码两轴滚动和外层scrollTop为0，控制台error为0，另一用户浏览器标签未操作。页面保留供试用。

同尺寸before.png/after-hidden.png/after-hover.png、after-split.png、after-mobile.png、after-narrow.png及结构化browser-before.json/browser-proof.json均保存在本轮忽略目录。浏览器只使用真实只读接口；加载空隙、零高度、隐藏恢复、长文件及模拟滚动边界属于组件测试，不冒称真实浏览器边界场景。减少动态CSS经过审阅，未切换系统偏好实测；13.11所述1201–1599px既有分屏断点限制保持，未宣称该区间通过。没有触发真实任务恢复、删除、清空或模型外发，未重复后端、压力、完整业务回归或真实用户试用验收。

项目记忆同步：前端规范v0.41明确本页缩略图显隐、键盘可达、占位/分屏隔离、已加载范围与实际视口反馈，纠正本页常驻缩略图的当前规则；旧阶段描述保留历史范围。本节为唯一新增进度/验证记录，没有建立新记忆系统或写中央记忆。独立只读增量审阅未发现本轮新阻塞。最终五个约定文件的完整字节基线增量已审阅，原275项Git状态条目集合与HEAD保持，git diff --check通过；证据目录被忽略，没有后端、接口、依赖、部署源码或Git写入改动。

### 13.15 用户授权配置远程仓库与 dev 分支（2026-10-06）

用户明确要求配置远程仓库、切换到`dev`并创建远端`dev`。地址末尾中文逗号按标点处理，实际`origin`为`https://github.com/lkuliuying/Programlr.git`。执行前本地只有`main`，HEAD为`d50e751986dcaace3d5d33d87bc4e4600b92ff4d`，暂存区为空、275项已有未提交状态；远端引用查询为空。本轮从该提交创建并切换到本地`dev`，保留`main`，普通推送创建远端`dev`并建立`origin/dev`跟踪关系，没有创建新提交或改写历史。

根目录实际执行并成功的配置与核验命令：

```text
git remote add origin https://github.com/lkuliuying/Programlr.git
git switch -c dev
git push --set-upstream origin dev
git remote -v
git branch -vv
git ls-remote --symref origin HEAD refs/heads/dev
git rev-list --left-right --count dev...origin/dev
git diff --check
```

远端`dev`与本地HEAD均为上述完整提交，ahead/behind为`0 0`，远端HEAD指向`dev`。分支操作后与本轮忽略目录`.runtime/remote-dev-20261006`中的基线核对，641项文件存在性/字节摘要及275项状态均保持，暂存区仍为空。工作区既有改动和本节记录继续保留在本地，未提交内容不在本次推送范围；本次只验证Git配置、分支、同步与原文件保护，不代表业务测试或部署验收。

项目记忆已读取AGENTS及本计划相关历史记录，仅在本节同步当前仓库和分支事实；早期无远程、使用`main`及当时未授权推送的记录保留其历史范围，以本次实际Git配置及远端查询为当前依据。未发现独立项目记忆文件，没有建立新记忆系统或写中央记忆。

### 13.16 用户授权分批提交并推送 dev（2026-10-06）

用户明确要求将已有工作分批提交并推送到`dev`。执行前本地与`origin/dev`同为`d50e751986dcaace3d5d33d87bc4e4600b92ff4d`，暂存区为空，共275项未提交状态（139修改、6删除、130新增）。沿用`https://github.com/lkuliuying/Programlr.git`，保存641项文件存在性/SHA-256基线和精确NUL路径清单；除本节追加的交付记录外，本轮不改写已有源码、测试、配置或文档内容，不新建业务提交内容。

按相互依赖分成三批，后端相关契约及其生成类型随同服务端提交，前端规范随界面提交，跨阶段材料集中在最后一批：

| 批次 | 范围 | 文件数 | 提交 |
| --- | --- | --- | --- |
| 1 | 后端扫描、目录导入、知识、操作日志、内部清理、退役兼容、迁移和测试，知识内容、83项契约/生成类型、代理、校验脚本及API/后端规范 | 143 | `5bae710`，`feat(backend): 完善源码扫描、项目清理与操作日志主线` |
| 2 | 三入口界面、固定浅色、面板滚动、项目/源码/日志交互及测试，前端规范；原6项删除随该批纳入 | 124 | `684413e`，`feat(frontend): 重构三入口工作台与源码日志交互` |
| 3 | AGENTS、README、需求、结构、路线图、演示、试用和本阶段计划 | 8 | `docs: 同步产品边界、验收记录与 dev 交付说明`，准确哈希以本次Git记录为准 |

每批使用`git add --pathspec-from-file=.runtime/batch-dev-20261006/batch-N.paths --pathspec-file-nul`精确暂存，逐批比对实际暂存路径、运行`git diff --cached --check`，再以对应UTF-8消息文件提交；每次提交后核对原文件摘要，使用`git push origin dev`普通推送。前两批已收到远端成功回执，最后一批包含本节。保留本地`main`及原历史，不合并、不强推、不部署、不提交`.env`、依赖、运行数据、证据或构建产物。前两批的行为验证基于本轮最终工作区，不将它们各自中间版本描述成单独部署验收。

本轮实际验证：`P=.runtime/m1-t02-venv/Scripts/python.exe`（3.13.15），`N=.runtime/tools/node-v24.21.0-win-x64/node.exe`（24.21.0）；根目录入口为`P -B -X utf8 .runtime/batch-dev-20261006/run_checks.py backend|contracts|frontend|vitest`，四个分组分别执行。完整参数、工作目录、日志和真实退出码保存在同目录`*-results.json`与对应日志。

| 已执行检查 | 观察结果 |
| --- | --- |
| backend：`P -B -X utf8 -m ruff check config common apps tests`及`ruff format --check config common apps tests` | 均退出0，257文件格式通过 |
| 根目录：四份本轮既有校验脚本`ruff check` | 退出0 |
| backend：设置`MYPYPATH`为项目`scripts`，执行`P -B -X utf8 -m mypy config common apps tests --platform linux --no-incremental` | 257源文件无错误 |
| backend：`P -B -X utf8 manage.py check --settings=config.settings.test`；`makemigrations --check --dry-run --settings=config.settings.test` | 系统检查无问题；无迁移漂移，不连接业务数据库 |
| 根目录：`P -B -X utf8 -m pytest scripts/test_check_m26_workspace.py scripts/test_check_contracts.py -q -p no:cacheprovider --basetemp .runtime/batch-dev-20261006/pytest` | 17 passed，4 subtests passed |
| 根目录：`P -B -X utf8 scripts/check_contracts.py --node N` | 三服务83/3/7项操作清单一致，59项无数据库契约测试通过；两套生成类型与TypeScript检查通过 |
| frontend：`N node_modules/eslint/bin/eslint.js . --max-warnings 0`；对本轮118个现存前端文件逐项展开`N node_modules/prettier/bin/prettier.cjs --check` | 均退出0，没有执行格式写入 |
| frontend：`N node_modules/vite/bin/vite.js build` | 退出0，保留已有大于500kB资源块提示；仅构建，不加载到运行实例 |
| frontend：`N node_modules/vitest/vitest.mjs run --configLoader native --pool threads --reporter=dot --reporter=json --outputFile=.runtime/batch-dev-20261006/vitest.json`（报告参数实际为根目录下该文件的绝对路径） | 47文件、338项全部通过，失败/跳过均0，约410秒；保留已有jsdom伪元素支持提示 |
| Git与文件检查 | 暂存清单逐批匹配；`git diff --check`通过；275项路径的指定凭据格式扫描无命中；161个本地文档链接均存在；每批原文件摘要保持 |

本轮没有重新执行完整PostgreSQL/Worker集成、浏览器交互、真实模型或真人试用；这些范围的旧证据仍属于原阶段，不能算成本次复验。指定格式凭据检查不是对任意秘密的检测保证。

项目记忆读取AGENTS、README、结构、API规范、前后端规范及本阶段相关记录，仅在本节追加本次Git交付与实际验证。既有文档有两处待单独修订的描述：README仍描述顶栏全局搜索及Ctrl/Meta+K，但当前MainlineWorkspace/WorkspaceShell已移除该入口；后端规范顶部仍写日志10查询字段，当前OperationLogsView.initial实际使用max_num_fields=12，API规范已记录12。已以源码核对并在此标记，不在本次分批提交中扩大范围改写已有说明。未发现独立项目记忆文件，不创建新记忆系统或更新中央记忆。临时交付材料均保留在忽略目录，最终远端HEAD与ahead/behind以推送后的只读核验为准。
