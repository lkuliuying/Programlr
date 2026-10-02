# 项目解读实验室：第四阶段计划

| 项目 | 内容 |
| --- | --- |
| 文档版本 | v0.7 |
| 产品版本 | v1.0 稳定个人作品 |
| 更新日期 | 2026-10-02 |
| 本文职责 | M16–M22 及试用补充交付的唯一进度、验证证据和恢复入口 |

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
| M22-T02 | 导入限制一致、立即反馈、显式提交和恢复 | 已实现，聚焦测试通过；待综合复核 |
| M22-T03 | 从真实页面审阅引导、视觉层级和导航，按证据改进 | 进行中 |
| M22-T04 | 综合回归、浏览器检查、文档一致性与本地提交 | 待完成 |

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
