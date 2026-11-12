import { EmptyState, PageHeader } from '../components.jsx'

// Shown for an address that no page lives at, such as a mistyped link.
export default function NotFoundScreen() {
  return (
    <>
      <PageHeader title="Page not found" subtitle="There is nothing at this address." />
      <EmptyState title="This page does not exist" action={{ href: '#/home', label: 'Go to Home' }}>
        The link may be mistyped, or the page may have moved. Your skills and matches are safe.
      </EmptyState>
    </>
  )
}
