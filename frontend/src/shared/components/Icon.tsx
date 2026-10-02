const paths = {
  workbench: ['M3 4h18v16H3z', 'M3 9h18M8 9v11'],
  import: ['M4 6h6l2 2h8v12H4z', 'M12 11v6m-3-3 3 3 3-3'],
  source: ['m8 6-6 6 6 6m8-12 6 6-6 6M14 3l-4 18'],
  api: ['M3 12h18M12 3v18', 'm6 9-3 3 3 3m12-6 3 3-3 3'],
  graph: ['M9 2h6v6H9zM2 16h6v6H2zM16 16h6v6h-6z', 'M12 8v5M5 16v-3h14v3'],
  comparison: ['M3 4h7v16H3zM14 4h7v16h-7z', 'M7 8h1M7 12h1m9-4h1m-1 4h1'],
  impact: [
    'M9 9h6v6H9z',
    'M12 2v7M12 15v7M2 12h7M15 12h7M4 4l5 5m6 6 5 5M4 20l5-5m6-6 5-5',
  ],
  learning: [
    'M3 3h7l2 2 2-2h7v17h-7l-2 2-2-2H3z',
    'M12 5v17M6 8h3m-3 4h3m6-4h3m-3 4h3',
  ],
  labs: ['M8 2h8M10 2v7L4 19q-1 3 2 3h12q3 0 2-3L14 9V2', 'M7 16h10'],
  explanation: ['M5 3h14v16H9l-4 3z', 'M8 7h8M8 11h8M8 15h5'],
  jobs: ['M4 5h16v16H4zM9 2h6v6H9z', 'm8 13 2 2 5-5'],
  system: ['M3 4h18v12H3zM8 21h8M12 16v5', 'm6 10 3-3 4 6 4-5 2 2'],
  folder: ['M3 5h7l2 3h9v13H3z'],
  file: ['M5 2h9l5 5v15H5zM14 2v6h5', 'M8 12h8m-8 4h6'],
  search: ['M16 10a6 6 0 1 1-12 0 6 6 0 0 1 12 0', 'm15 15 6 6'],
  close: ['m6 6 12 12M6 18 18 6'],
  pin: ['m8 3 10 10M10 5l-5 7 7 7 7-5M3 21l5-5'],
  sun: [
    'M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
    'M12 1v2m0 18v2M1 12h2m18 0h2M4 4l2 2m12 12 2 2M4 20l2-2M18 6l2-2',
  ],
  moon: ['M20 16A9 9 0 0 1 8 4a9 9 0 1 0 12 12Z'],
  menu: ['M3 6h18M3 12h18M3 18h18'],
  arrow: ['M4 12h16m-5-5 5 5-5 5'],
  cube: ['m12 2 10 6v9l-10 5L2 17V8zM2 8l10 5 10-5M12 13v9'],
  clock: ['M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0', 'M12 6v6l4 2'],
} as const;
export type IconName = keyof typeof paths;
export function Icon({
  name,
  className = '',
}: {
  name: IconName;
  className?: string;
}) {
  return (
    <svg
      className={`icon ${className}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name].map((d, i) => (
        <path key={i} d={d} />
      ))}
    </svg>
  );
}
export function LabMark() {
  return (
    <svg className="lab-mark" viewBox="0 0 40 44" aria-hidden="true">
      <path
        d="M14 3h12v4h-3v12l12 19q1 3-3 3H8q-4 0-3-3l12-19V7h-3Z"
        fill="var(--accent-soft)"
        stroke="var(--cyan)"
        strokeWidth="2"
      />
      <path d="M11 30h18l5 9H6Z" fill="var(--accent)" />
      <circle cx="20" cy="27" r="2" fill="var(--cyan)" />
      <circle cx="23" cy="34" r="2" fill="var(--canvas)" />
    </svg>
  );
}
