import { Component, type ReactNode } from 'react';

type Props = { children: ReactNode; onReload?: () => void };
type State = { failed: boolean };

export class AppErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <main className="app-recovery">
        <div role="alert">
          <h1>工作区暂时无法显示</h1>
          <p>页面发生了显示异常。请重新加载当前工作区，再核对任务状态。</p>
          <p>
            已提交的任务可能仍在执行。恢复后请先查询或恢复原操作，避免重复提交。
          </p>
        </div>
        <button
          onClick={this.props.onReload ?? (() => window.location.reload())}
        >
          重新加载当前工作区
        </button>
        <a href="?view=jobs">查看任务历史</a>
      </main>
    );
  }
}
