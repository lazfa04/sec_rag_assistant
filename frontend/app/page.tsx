import { AskForm } from "@/components/ask-form"

export default function Home() {
  return (
    <div className="relative isolate flex flex-1 flex-col overflow-hidden bg-[#06040f]">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(125%_125%_at_50%_0%,#241552_0%,#120c30_38%,#08051a_68%,#04030c_100%)]"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-48 left-1/2 size-[38rem] -translate-x-1/2 rounded-full bg-violet-600/25 blur-[150px]"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute top-1/4 -left-40 size-[30rem] rounded-full bg-blue-600/20 blur-[140px]"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-40 bottom-0 size-[32rem] rounded-full bg-fuchsia-600/15 blur-[150px]"
      />

      <main className="relative mx-auto flex w-full max-w-3xl flex-1 flex-col gap-10 px-6 py-16 sm:py-20">
        <header className="flex flex-col items-center gap-4 text-center">
          <span className="inline-flex h-7 items-center rounded-full bg-white/5 px-3.5 text-[0.7rem] font-medium tracking-[0.2em] text-white/60 uppercase ring-1 ring-white/10 backdrop-blur-xl">
            SEC Filings
          </span>
          <h1 className="font-heading text-2xl font-extrabold tracking-[0.18em] text-white uppercase sm:text-3xl">
            Filing Research Assistant
          </h1>
          <p className="max-w-md text-sm leading-relaxed text-white/50">
            Ask a question about a 10-K or 10-Q. Answers come only from retrieved
            filing text, with citations you can check against the source sections.
          </p>
        </header>
        <AskForm />
      </main>
    </div>
  )
}
