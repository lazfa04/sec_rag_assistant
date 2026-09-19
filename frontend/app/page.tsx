import { AskForm } from "@/components/ask-form"

export default function Home() {
  return (
    <div className="flex flex-1 flex-col bg-background">
      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-10 px-6 py-12 sm:py-16">
        <header className="flex flex-col gap-3">
          <p className="text-sm text-muted-foreground">SEC filings</p>
          <h1 className="font-heading text-3xl font-medium tracking-tight">
            Ask a question about a filing
          </h1>
          <p className="max-w-lg text-sm leading-relaxed text-muted-foreground">
            Answers come only from retrieved 10-K and 10-Q chunks, with citations
            you can check against the source sections.
          </p>
        </header>
        <AskForm />
      </main>
    </div>
  )
}
