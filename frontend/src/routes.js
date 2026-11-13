// Every address in the app, in one place: the page it opens, the name shown in
// the browser tab, and the old addresses that now lead somewhere else.

const CODE = '([\\w.-]+)'

// pattern groups become params, named in order by `params`.
const ROUTES = [
  { name: 'home', pattern: /^\/home$/, title: 'Home' },
  { name: 'matches', pattern: /^\/matches$/, title: 'Matches' },
  { name: 'profile', pattern: /^\/profile$/, title: 'My profile' },
  { name: 'careers', pattern: /^\/careers$/, title: 'Careers' },
  { name: 'career', pattern: new RegExp(`^/careers/${CODE}(?:/(fit|plan))?$`), params: ['code', 'tab'], title: 'Career' },
  { name: 'plan', pattern: /^\/plan$/, title: 'My plan' },
  { name: 'history', pattern: /^\/history(?:\/(\d+))?$/, params: ['runId'], title: 'History' },
  { name: 'settings', pattern: /^\/settings$/, title: 'Settings' },
]

// Addresses from before the pages were renamed; bookmarks and old links keep working.
const MOVED = [
  [/^\/?$/, '/home'],
  [/^\/dashboard$/, '/home'],
  [/^\/recommendations$/, '/matches'],
  [/^\/assessment$/, '/profile'],
  [/^\/roadmap$/, '/plan'],
  [/^\/(?:roadmap|plan)\/([\w.-]+)$/, '/careers/$1/plan'],
  [/^\/saved$/, '/careers?show=saved'],
]

// The path of a hash address, without its query: '/careers?show=saved' gives '/careers'.
export function pathOf(address) {
  return address.split('?')[0].replace(/(.)\/$/, '$1')
}

// The query of a hash address as an object: '/careers?show=saved' gives { show: 'saved' }.
export function queryOf(address) {
  return Object.fromEntries(new URLSearchParams(address.split('?')[1] ?? ''))
}

// { name, params, title } for a page, { redirect } for a moved address, or
// { name: 'not-found' } when nothing lives there.
export function resolve(address) {
  const path = pathOf(address)
  const query = address.slice(address.split('?')[0].length)
  for (const [old, target] of MOVED) {
    if (old.test(path)) return { redirect: path.replace(old, target) + (target.includes('?') ? '' : query) }
  }
  for (const route of ROUTES) {
    const found = path.match(route.pattern)
    if (!found) continue
    const params = Object.fromEntries((route.params ?? []).map((key, i) => [key, found[i + 1]]))
    return { name: route.name, params, title: route.title }
  }
  return { name: 'not-found', params: {}, title: 'Page not found' }
}

// Where to go after signing in: the address that was asked for if it is a real page, or home.
export function landing(address) {
  const route = resolve(address)
  if (route.redirect) return route.redirect
  return route.name === 'not-found' ? '/home' : address
}

// The link in `links` ([{ path }]) that the address belongs under, or null.
export function activeLink(address, links) {
  const path = pathOf(address)
  return links.find((l) => path === l.path || path.startsWith(`${l.path}/`))?.path ?? null
}
