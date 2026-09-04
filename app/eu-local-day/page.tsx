export const metadata = {
  title: "EU Local Day | Smart AliExpress Finds for Europe",
  description: "A focused EU Local Day shopping gateway with one clear path to the current AliExpress promotion.",
};

const affiliateUrl = "https://s.click.aliexpress.com/e/_c2JowsLL";

export default function EuLocalDayPage() {
  return (
    <main className="min-h-screen bg-[#080b12] text-white overflow-hidden">
      <section className="relative mx-auto flex min-h-[92vh] max-w-7xl items-center px-6 py-20 lg:px-10">
        <div className="absolute -left-28 top-12 h-72 w-72 rounded-full bg-orange-500/20 blur-3xl" />
        <div className="absolute -right-20 bottom-12 h-96 w-96 rounded-full bg-amber-300/10 blur-3xl" />
        <div className="relative grid w-full gap-14 lg:grid-cols-[1.15fr_.85fr] lg:items-center">
          <div>
            <div className="mb-7 inline-flex rounded-full border border-white/15 bg-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[.24em] text-orange-200">
              AFFINITY × EU Local Day
            </div>
            <h1 className="max-w-4xl text-5xl font-black leading-[.96] tracking-[-.055em] sm:text-7xl lg:text-8xl">
              Europe’s deal window,
              <span className="block text-orange-400">without the clutter.</span>
            </h1>
            <p className="mt-8 max-w-2xl text-lg leading-8 text-white/65 sm:text-xl">
              Enter the current AliExpress EU Local Day promotion through one clean gateway. Browse the live campaign directly on AliExpress and verify the final price, availability and delivery for your location before ordering.
            </p>
            <div className="mt-10 flex flex-col gap-4 sm:flex-row">
              <a href={affiliateUrl} target="_blank" rel="sponsored noopener noreferrer" className="inline-flex min-h-14 items-center justify-center rounded-2xl bg-orange-500 px-8 text-base font-black text-black transition hover:scale-[1.02] hover:bg-orange-400">
                Explore EU Local Day →
              </a>
              <a href="#how" className="inline-flex min-h-14 items-center justify-center rounded-2xl border border-white/15 bg-white/5 px-8 font-semibold text-white/80 hover:bg-white/10">
                How to shop smarter
              </a>
            </div>
            <p className="mt-5 text-xs leading-5 text-white/35">Affiliate disclosure: this page may earn a commission from qualifying purchases. The final merchant, price, stock, shipping, taxes, returns and product terms are shown by AliExpress.</p>
          </div>

          <div className="relative">
            <div className="rounded-[2rem] border border-white/10 bg-white/[.055] p-5 shadow-2xl backdrop-blur-xl">
              <div className="rounded-[1.55rem] border border-white/10 bg-gradient-to-br from-orange-500/25 via-white/[.04] to-transparent p-8 sm:p-10">
                <div className="text-xs font-bold uppercase tracking-[.25em] text-orange-300">AFFINITY CHECK</div>
                <div className="mt-5 text-3xl font-black tracking-tight">Promotion gateway</div>
                <div className="mt-8 space-y-4">
                  {[
                    ["Destination", "AliExpress EU campaign"],
                    ["Affiliate tracking", "Present"],
                    ["Individual SKU", "Selected after click"],
                    ["Price & stock", "Verify live on merchant"],
                    ["Delivery", "Check for Greece / EU address"],
                  ].map(([a,b]) => (
                    <div key={a} className="flex items-start justify-between gap-5 border-b border-white/10 pb-4">
                      <span className="text-sm text-white/45">{a}</span><span className="text-right text-sm font-bold text-white/90">{b}</span>
                    </div>
                  ))}
                </div>
                <a href={affiliateUrl} target="_blank" rel="sponsored noopener noreferrer" className="mt-9 flex min-h-14 w-full items-center justify-center rounded-xl bg-white text-sm font-black text-black hover:bg-orange-100">Open the live promotion</a>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="how" className="border-y border-white/10 bg-white/[.025]">
        <div className="mx-auto max-w-7xl px-6 py-20 lg:px-10">
          <div className="max-w-2xl">
            <div className="text-xs font-bold uppercase tracking-[.25em] text-orange-300">BUYER FILTER</div>
            <h2 className="mt-4 text-4xl font-black tracking-tight sm:text-5xl">Three checks before you buy.</h2>
          </div>
          <div className="mt-12 grid gap-5 md:grid-cols-3">
            {[
              ["01", "Compare the real price", "Check the final checkout price rather than relying on promotional framing. Compare it with Greek and EU alternatives."],
              ["02", "Confirm delivery", "Verify that the exact SKU ships to your address and inspect delivery time, shipping cost and the ship-from location."],
              ["03", "Check protection", "Read the exact seller, return and warranty terms for the product you choose before payment."],
            ].map(([n,t,d]) => (
              <article key={n} className="rounded-3xl border border-white/10 bg-white/[.045] p-7">
                <div className="text-sm font-black text-orange-400">{n}</div>
                <h3 className="mt-6 text-xl font-black">{t}</h3>
                <p className="mt-3 leading-7 text-white/55">{d}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-6 py-24 text-center">
        <p className="text-sm font-bold uppercase tracking-[.25em] text-orange-300">Ready to browse?</p>
        <h2 className="mt-5 text-4xl font-black tracking-tight sm:text-6xl">Go directly to the live EU campaign.</h2>
        <p className="mx-auto mt-5 max-w-2xl text-white/55">Because this is a campaign-level link rather than one fixed product, all product-specific AFFINITY checks should be performed on the SKU you ultimately select.</p>
        <a href={affiliateUrl} target="_blank" rel="sponsored noopener noreferrer" className="mt-9 inline-flex min-h-14 items-center justify-center rounded-2xl bg-orange-500 px-9 font-black text-black hover:bg-orange-400">Shop EU Local Day →</a>
      </section>
    </main>
  );
}
