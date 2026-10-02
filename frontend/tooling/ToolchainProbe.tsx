import { useState } from 'react';
import { Button, ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';

// 仅验证组件库与 React 事件，不承担工作台页面或教学业务。
export function ToolchainProbe() {
  const [checked, setChecked] = useState(false);
  return (
    <ConfigProvider locale={zhCN}>
      <Button onClick={() => setChecked(true)}>
        {checked ? '工具检查完成' : '检查组件'}
      </Button>
    </ConfigProvider>
  );
}
