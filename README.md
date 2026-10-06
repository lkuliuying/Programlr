# 项目解读实验室

本地单用户源码学习工作台，保留 React／DRF／Celery／PostgreSQL 架构。当前主流程：**导入 ZIP／源码目录 → 自动识别 → 联动阅读源码、接口、关系与知识 → 按需生成模型讲解**。只读分析导入副本，不安装依赖、不执行项目。

## 当前使用流程

1. 在“项目管理”上传 ZIP 或选择目录，项目名称默认取来源名称并可修改；已有项目可导入新快照。
2. 导入成功进入统一工作区。系统扫描根路由、AST知识和包事实；唯一 Django 根路由自动分析，多根列出依据供选择，无根仍能阅读源码与知识。
3. 文件／接口导航联动双源码和接口、关系、知识、讲解面板。“接口关联”以共用处理器、序列化器、模型连接接口；“代码依赖”保持静态依赖方向，不宣称业务执行顺序。
4. 知识展示版本化可信卡片及命中位置，可筛选整个快照／当前文件／当前接口。未知导入展示“未映射”，不编造正文；旧快照显式重新识别，GET不自动补写。
5. 模型讲解保持预览、确认、显式提交。排除片段同步排除相关知识；模板1.1.0使旧未消费确认失效，旧讲解可读。配置仅地址、模型ID、API key，现行应用不设模型预算或请求总期限，无自动计费重试。
6. “操作日志”记录导入、扫描、分析、模型与删除的阶段、结果、稳定错误和重放。删除先预览范围并确认，后台只清理内部副本及关联结果；原ZIP／目录不受影响。文件失败保持删除隔离，在日志显式“继续清理”；完成后日志和必要任务摘要仍可读。

ZIP保持20MiB上限。目录最多2000有效文件、单文件1MiB、合计100MiB、路径清单4MiB；代理110MiB、内部归档105MiB。前后端排除环境、依赖、构建和敏感文件并检查路径。不支持目录选择时使用ZIP。过滤不保证识别所有硬编码秘密，模型发送前需检查实际范围。

界面固定浅色，正文改为面板滚动并保留服务端分页。源码提供只读多标签、可选分屏、连续200行分块和已保存的相关依据；URL定位与单实例草稿保持。全局搜索项目、跨项目快照及当前文件/接口，Ctrl/Meta+K聚焦，空词不展开。项目技术筛选/排序及日志统计、关联历史、CSV导出使用真实持久数据。

## 已退役功能与历史

课程目录／先修路径／学习进度、固定练习／作答／自评、受控实验、快照对比、候选影响、人工关系校准、独立课程首页、通知中心和基础检查页面已移除当前流程。对应旧写入口返回410 FEATURE_RETIRED，通用重试和遗留队列不能重启这些功能；历史模型、迁移和必要只读入口保留，旧链接解释退役原因，历史任务结果从日志查看。新实例只加载可信知识卡片。

当前83项工作台契约包含退役兼容入口；[API清单](docs/api-catalog.md)与生成类型由实现导出。M1–M26的旧界面、实验和验收属于阶段历史。M27重构范围、进度、实际证据和限制唯一见[第四阶段计划](docs/phase-4-plan.md#m27)。独立人工审阅、旧模型兼容和旧实例验收不能自动推广为本次结果；真实用户试用仍待进行。

## 启动与访问

工作目录 F:\Program\Fall_Campus_Recruitment，需要Docker Desktop Linux引擎/Compose；不需要全局安装Python/Node。已有实例本轮不自动更新。用户决定更新时先备份实例数据，保留命名卷，再执行：

```powershell
$env:PATH = 'C:/Program Files/Docker/Docker/resources/bin;' + $env:PATH
docker compose up -d --build --wait --wait-timeout 90
```

默认入口 http://127.0.0.1:5173/。增量迁移保留未删除目标旧数据，内容加载不重算历史。Compose私有凭据卷与既有模型配置方式保持；不要将秘密写入文档/日志。端口冲突明确失败，不自动换端口。不运行会删除命名卷的清理命令。

## 隔离验证

以下命令只操作脚本拥有的随机名称和标签资源，回环5185，独立tmpfs PostgreSQL、Redis、源码存储和Linux Worker；不读取根.env、不更新5181或默认实例，不调用真实模型。需要现有learning-lab-backend:m5-verify、learning-lab-frontend:m5-verify及固定PostgreSQL/Redis镜像，并先构建frontend/dist；缺少镜像时明确失败，不自动安装。

```powershell
& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 scripts/check_m26_workspace.py start --docker 'C:/Program Files/Docker/Docker/resources/bin/docker.exe'
& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 scripts/check_m26_workspace.py status --docker 'C:/Program Files/Docker/Docker/resources/bin/docker.exe'
# 完成验证后仅清理本次脚本的临时数据。
& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 scripts/check_m26_workspace.py stop --docker 'C:/Program Files/Docker/Docker/resources/bin/docker.exe'
```

隔离完整后端回归（脚本自行创建并清理另一组临时数据）：

```powershell
& '.runtime/m1-t02-venv/Scripts/python.exe' -B -X utf8 scripts/check_v03_backend.py --docker 'C:/Program Files/Docker/Docker/resources/bin/docker.exe' -- python -B -m pytest apps common tests --ds=config.settings.local -q -p no:cacheprovider --tb=short
```

固定工具前端命令在frontend执行：`npm run typecheck`、`npm run lint`、`npm run test -- --run`、`npm run build`。后端Ruff、设置MYPYPATH为根scripts后的`mypy config common apps tests --platform linux --no-incremental`及迁移检查使用项目隔离Python。生成契约先在backend执行`python manage.py spectacular --settings=config.settings.test --file ../contracts/openapi.yaml --validate --fail-on-warn`，再在frontend执行`npm run api:types`；不得手改生成DTO。

契约只读核对：`python -B -X utf8 scripts/check_contracts.py --node .runtime/tools/node-v24.21.0-win-x64/node.exe`。独立任务簿契约/示例保留为源码基准，原固定检查/实验HTTP验证脚本属于历史版本，不能作为M26入口执行。

## 文档与试用材料

[产品需求](docs/requirements.md)、[项目结构](docs/project-structure.md)、[API协议](docs/api-conventions.md)、[后端规范](docs/backend-guidelines.md)、[前端规范](docs/frontend-guidelines.md)维护长期规则。历史[第一阶段](docs/phase-1-plan.md)、[第二阶段](docs/phase-2-plan.md)、[第三阶段](docs/phase-3-plan.md)与第四阶段M21–M25保留原验证边界。

[test/task-board.zip](test/task-board.zip)及同名目录是只读导入材料，原始文件不因内部删除变化；完整示例由examples/task-board维护，导入不会启动示例服务。当前根发现通常可自动识别backend/config/urls.py，识别限制通过诊断展示。

[v1演示](docs/v1-demo.md)和[试用协议](docs/v1-trial.md)保存旧演示/空白观察模板，M26使用本页三入口流程。真实用户学习效果、其他框架/浏览器、任意项目动态路由和真实模型调用不以本轮工程回归替代。

项目已有本地main仓库，本轮不执行Git写操作或远程发布。所有现有未提交工作由实施前非敏感工程基线保护；临时证据位于忽略的.runtime，不建立新的长期记忆系统。
