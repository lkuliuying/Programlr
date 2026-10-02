# 页面试用：任务簿导入测试项目

这是 DRF + React 任务簿的核心源码包，用于在项目解读实验室中试用项目导入、源码阅读、API 分析、静态关系图、知识卡片和固定练习。来源为 `examples/task-board` 的 `task-board/1.0.0`，9 个源码文件保持原路径和字节内容，与已发布教学内容的文件摘要一致。

## 使用方法

1. 在工作台进入「项目导入」，创建一个项目，例如「任务簿页面试用」。
2. 选择本目录的 [task-board.zip](task-board.zip)，提交导入并等待任务成功。直接上传现成 ZIP，无需重新压缩源码目录。
3. 选择新快照，发起静态分析；根路由文件填写 `backend/config/urls.py`。
4. 在 API 分析中选择 `POST /api/v1/tasks/`，查看源码引用和静态关系。
5. 在源码阅读中打开 `backend/apps/tasks/api/views.py`，将 `frontend/src/features/tasks/TaskBoard.tsx` 固定到第二窗口；尝试搜索 `serializers.py`、切换主题、分段阅读和刷新恢复。
6. 打开学习区域查看适用知识卡片和固定练习。实验区域连接工作台既有可信示例；可用性由当前运行环境决定，导入这份 ZIP 不会启动任何服务。

模型讲解继续使用工作台的预览及单次确认流程；导入和分析无需模型调用。源码窗口每次最多显示 200 行，较长文件可继续分段阅读。

## 文件与用途

| 文件 | 用途 |
| --- | --- |
| `backend/config/urls.py` | 根路由入口 |
| `backend/apps/tasks/api/urls.py` | 任务接口路由 |
| `backend/apps/tasks/api/views.py` | DRF 视图与请求处理 |
| `backend/apps/tasks/api/serializers.py` | 输入及输出序列化 |
| `backend/apps/tasks/services.py` | 创建任务的业务操作 |
| `backend/apps/tasks/models.py` | 任务数据模型 |
| `frontend/src/features/tasks/TaskBoard.tsx` | React 任务页面与交互 |
| `frontend/src/features/tasks/api/tasks-api.ts` | 任务请求封装 |
| `frontend/src/shared/api/client.ts` | HTTP 客户端 |

`task-board/` 是 ZIP 中这 9 个文件的目录副本。ZIP 根目录直接包含 `backend/` 和 `frontend/`，没有额外的 `task-board/` 外层，也不包含依赖、缓存、凭据、用户作答或标准答案。

## 边界与来源

这份包用于只读导入分析，不是可独立启动的完整应用。若要运行任务簿应用，使用已有的 [完整可信示例及运行说明](../examples/task-board/README.md)，其依赖、配置、测试和启动入口仍由原示例维护。

测试包只从已发布清单 `content/exercises/task-board-create.json` 的源码路径复制，不单独维护第二套业务逻辑。修改文件后重新打包，会产生新的快照；与发布摘要不一致时，已有固定教学内容可能不再适用。

交付及验证记录统一见 [第四阶段计划](../docs/phase-4-plan.md#trial-test-project)，测试包存在不代表真实用户试用已通过。
