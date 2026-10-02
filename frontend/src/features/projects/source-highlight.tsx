const keywords = new Set(
  'import from as class def return if else elif for while try except finally with async await pass raise lambda yield in is not and or True False None export default const let function new null true false interface type extends implements public private readonly useState useEffect'.split(
    ' ',
  ),
);
export function highlightSource(line: string, path: string) {
  if (!/\.(py|tsx?|jsx?)$/i.test(path)) return line;
  // 仅做行内词法着色；跨行字符串和语义判断仍以原始源码为准。
  const pattern =
    /(#.*$|\/\/.*$|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|\b[A-Za-z_]\w*\b)/g;
  const parts = [];
  let start = 0;
  for (const match of line.matchAll(pattern)) {
    const index = match.index;
    if (index > start) parts.push(line.slice(start, index));
    const value = match[0];
    const kind = /^(#|\/\/)/.test(value)
      ? 'comment'
      : /^["'`]/.test(value)
        ? 'string'
        : keywords.has(value)
          ? 'keyword'
          : '';
    parts.push(
      kind ? (
        <span key={index} className={`syntax-${kind}`}>
          {value}
        </span>
      ) : (
        value
      ),
    );
    start = index + value.length;
  }
  if (start < line.length) parts.push(line.slice(start));
  return parts.length ? parts : line;
}
