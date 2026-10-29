// Thin outline icons on an 18px grid. Stroke width, caps and colour come from
// the .icon rule in styles.css, so an icon takes the colour of its text.

const PATHS = {
  home: (
    <>
      <rect x="2" y="2" width="6" height="6" rx="1.5" />
      <rect x="10" y="2" width="6" height="6" rx="1.5" />
      <rect x="2" y="10" width="6" height="6" rx="1.5" />
      <rect x="10" y="10" width="6" height="6" rx="1.5" />
    </>
  ),
  matches: <path d="M3 15V9M9 15V3M15 15V7" />,
  plus: <path d="M9 3.5v11M3.5 9h11" />,
  explore: (
    <>
      <circle cx="9" cy="9" r="6.5" />
      <path d="m11.6 6.4-1.5 3.7-3.7 1.5 1.5-3.7z" />
    </>
  ),
  roadmap: <path d="M4 16V2.5M4 3h9l-2 3 2 3H4" />,
  graph: (
    <>
      <circle cx="4" cy="9" r="2" />
      <circle cx="14" cy="4" r="2" />
      <circle cx="14" cy="14" r="2" />
      <path d="m5.8 8.1 6.4-3.2M5.8 9.9l6.4 3.2" />
    </>
  ),
  search: (
    <>
      <circle cx="8" cy="8" r="5.5" />
      <path d="m12.5 12.5 3.5 3.5" />
    </>
  ),
  logout: <path d="M7 3H4.5A1.5 1.5 0 0 0 3 4.5v9A1.5 1.5 0 0 0 4.5 15H7M11 12l3-3-3-3M14 9H7" />,
  back: <path d="M11 4 6 9l5 5" />,
  forward: <path d="m7 4 5 5-5 5" />,
  chevron: <path d="m5 7 4 4 4-4" />,
  close: <path d="m5 5 8 8M13 5l-8 8" />,
  edit: <path d="m11.5 3.5 3 3L6 15H3v-3z" />,
  check: <path d="m4 9.5 3 3 7-7" />,
  sun: (
    <>
      <circle cx="9" cy="9" r="3.2" />
      <path d="M9 1.5v1.8M9 14.7v1.8M1.5 9h1.8M14.7 9h1.8M3.7 3.7 5 5M13 13l1.3 1.3M3.7 14.3 5 13M13 5l1.3-1.3" />
    </>
  ),
  moon: <path d="M15 10.8A6.5 6.5 0 1 1 7.2 3a5 5 0 0 0 7.8 7.8z" />,
  bookmark: <path d="M5 2.5h8a.5.5 0 0 1 .5.5v12.5L9 12.5l-4.5 3V3a.5.5 0 0 1 .5-.5z" />,
  settings: (
    <>
      <circle cx="9" cy="9" r="2.4" />
      <path d="M9 1.8v2M9 14.2v2M1.8 9h2M14.2 9h2M3.9 3.9l1.4 1.4M12.7 12.7l1.4 1.4M3.9 14.1l1.4-1.4M12.7 5.3l1.4-1.4" />
    </>
  ),
  user: (
    <>
      <circle cx="9" cy="6" r="3.2" />
      <path d="M2.8 16a6.2 6.2 0 0 1 12.4 0" />
    </>
  ),
  bulb:<path d="M7 13.5h4M7.5 16h3M9 2a5 5 0 0 0-3 9c.6.5 1 1.2 1 2.5h4c0-1.3.4-2 1-2.5a5 5 0 0 0-3-9z" />,
  alert: (
    <>
      <path d="M8.1 2.8 1.9 13.6A1 1 0 0 0 2.8 15h12.4a1 1 0 0 0 .9-1.4L9.9 2.8a1 1 0 0 0-1.8 0z" />
      <path d="M9 6.5v3.5M9 12.5v.01" />
    </>
  ),
}

export function Icon({ name, size = 18 }) {
  return (
    <svg className="icon" width={size} height={size} viewBox="0 0 18 18" aria-hidden="true" focusable="false">
      {PATHS[name]}
    </svg>
  )
}
