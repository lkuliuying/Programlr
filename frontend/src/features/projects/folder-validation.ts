import { ApiError } from '../../shared/api/client';

export type FolderEntry = { file: File; path: string };
export type FolderSelection = {
  name: string;
  entries: FolderEntry[];
  excluded: number;
  bytes: number;
};
const excludedDirectories = new Set([
  '.git',
  '.hg',
  '.svn',
  'node_modules',
  'vendor',
  '.venv',
  'venv',
  'env',
  '__pycache__',
  'dist',
  'build',
  '.pytest_cache',
  '.mypy_cache',
  '.ruff_cache',
  '.cache',
  'coverage',
  '.next',
  '.nuxt',
  '.idea',
  '.vscode',
  '.ssh',
]);
const source = /\.(py|js|jsx|ts|tsx)$/i;
const manifest =
  /^(requirements(?:[-_.][A-Za-z0-9_-]+)?\.txt|pyproject\.toml)$/i;

export function selectFolder(files: File[]): FolderSelection {
  const entries: FolderEntry[] = [];
  const seen = new Set<string>();
  let excluded = 0;
  let bytes = 0;
  let name = '';
  for (const file of files) {
    const relative = file.webkitRelativePath;
    const parts = relative.normalize('NFC').split('/');
    if (!name) name = parts[0] ?? '';
    if (!relative || parts.length < 2 || parts[0] !== name)
      throw new ApiError('目录路径无效，请重新选择一个完整目录。', 400);
    const segments = parts.slice(1);
    if (
      segments.length > 32 ||
      segments.some(
        (part) =>
          !part ||
          part === '.' ||
          part === '..' ||
          /[\\:<>"|?*]/.test(part) ||
          [...part].some(
            (char) =>
              char.charCodeAt(0) < 32 ||
              (char.charCodeAt(0) >= 127 && char.charCodeAt(0) <= 159),
          ) ||
          /[. ]$/.test(part) ||
          /^(con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])(?:\.|$)/i.test(part) ||
          new TextEncoder().encode(part).length > 255,
      )
    )
      throw new ApiError('目录包含不安全的相对路径，未提交上传。', 400);
    const path = segments.join('/');
    if (new TextEncoder().encode(path).length > 1024)
      throw new ApiError('目录路径过长，未提交上传。', 400);
    const basename = segments.at(-1)!;
    if (
      segments
        .slice(0, -1)
        .some(
          (part) =>
            excludedDirectories.has(part.toLowerCase()) ||
            part.toLowerCase() === '.env' ||
            part.toLowerCase().startsWith('.env.'),
        ) ||
      basename.toLowerCase().startsWith('.env') ||
      /^(credentials|secrets|id_rsa|id_ed25519)\./i.test(basename) ||
      (!source.test(basename) && !manifest.test(basename))
    ) {
      excluded++;
      continue;
    }
    const identity = path.toLowerCase();
    if (
      seen.has(identity) ||
      [...seen].some(
        (prior) =>
          prior.startsWith(identity + '/') || identity.startsWith(prior + '/'),
      )
    )
      throw new ApiError('目录存在重名或大小写冲突的路径，未提交上传。', 400);
    seen.add(identity);
    if (file.size > 1024 * 1024)
      throw new ApiError('目录中的有效文件不能超过 1 MiB。', 400);
    bytes += file.size;
    entries.push({ file, path });
    if (entries.length > 2000 || bytes > 100 * 1024 * 1024)
      throw new ApiError('目录最多 2000 个有效文件，合计不超过 100 MiB。', 400);
  }
  if (!entries.length)
    throw new ApiError('目录没有可识别的源码或依赖声明。', 400);
  entries.sort((a, b) => a.path.localeCompare(b.path, 'en'));
  return { name, entries, excluded, bytes };
}

export function folderBody(folder: FolderSelection): FormData {
  const manifest = JSON.stringify({
    files: folder.entries.map((entry, index) => ({ path: entry.path, index })),
  });
  if (new TextEncoder().encode(manifest).length > 4 * 1024 * 1024)
    throw new ApiError('目录路径清单不能超过 4 MiB。', 400);
  const body = new FormData();
  body.append(
    'manifest',
    new Blob([manifest], { type: 'application/json' }),
    'manifest.json',
  );
  folder.entries.forEach(({ file }) => body.append('files', file, file.name));
  return body;
}
