/**
 * Benches (/benches): find benches on the network and manage them in one place.
 * PLACEHOLDER — stacks the pre-redesign Hosts and Discover pages until the
 * Benches page agent replaces it (see components/ui-cdi/README.md and the
 * Benches mockup). /hosts and /discover redirect here.
 */
import { DiscoverPage } from "@/pages/legacy/discover-page"
import { HostsPage } from "@/pages/legacy/hosts-page"

export function BenchesPage() {
  return (
    <>
      <section
        id="find-benches"
        aria-label="Find benches on the network"
        className="flex flex-col gap-6"
      >
        <DiscoverPage />
      </section>
      <section aria-label="Benches" className="flex flex-col gap-6">
        <HostsPage />
      </section>
    </>
  )
}
