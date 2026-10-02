(function () {
  let mode = 'dark';
  try {
    const saved = localStorage.getItem('learning-lab.ui-theme');
    if (saved === 'light' || saved === 'dark') mode = saved;
  } catch {
    // 存储不可用时仍允许本次会话使用默认主题。
  }
  document.documentElement.dataset.theme = mode;
  document.documentElement.style.colorScheme = mode;
})();
