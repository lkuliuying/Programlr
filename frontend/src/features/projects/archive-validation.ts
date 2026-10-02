export const MAX_ARCHIVE_BYTES = 20 * 1024 * 1024;

export function archiveValidationMessage(file: File): string | null {
  if (!file.name.toLowerCase().endsWith('.zip'))
    return '请选择 ZIP 格式的源码压缩包。';
  if (!file.size) return '这个文件是空的，请重新选择源码 ZIP。';
  if (file.size > MAX_ARCHIVE_BYTES)
    return '文件超过 20 MiB，请移除依赖、构建产物或无关文件后重新压缩。';
  return null;
}
