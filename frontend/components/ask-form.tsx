"use client"

import { useEffect, useState, type FormEvent } from "react"
import { ArrowRightIcon, FileSearchIcon, SearchIcon } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
const ALL_COMPANIES = "all"

const GLASS_PANEL =
  "rounded-3xl bg-white/5 ring-1 ring-white/10 backdrop-blur-xl"
const SECTION_LABEL =
  "text-[0.7rem] font-medium tracking-[0.18em] text-white/40 uppercase"

const QUICK_ACTIONS = [
  {
    label: "Apple's risk factors",
    question: "What are Apple's main risk factors?",
  },
  {
    label: "Apple vs Microsoft",
    question: "Compare Apple's and Microsoft's antitrust risk factors",
  },
  {
    label: "Tesla's tax rate",
    question: "What is Tesla's effective tax rate?",
  },
  {
    label: "NVIDIA supply chain",
    question: "What does NVIDIA say about supply chain risk?",
  },
]

type Source = {
  ticker?: string
  filing_date?: string
  item_number?: string
  item_title?: string
  text?: string
  similarity?: number
}

type AskResponse = {
  answer: string
  sources: Source[]
}

function snippet(text: string, max = 220) {
  const compact = text.replace(/\s+/g, " ").trim()
  if (compact.length <= max) return compact
  return `${compact.slice(0, max).trimEnd()}…`
}

function similarityLabel(score: number | undefined) {
  if (typeof score !== "number" || Number.isNaN(score)) return "n/a"
  if (score <= 1) return `${Math.round(score * 100)}%`
  return score.toFixed(2)
}

export function AskForm() {
  const [mounted, setMounted] = useState(false)
  const [companies, setCompanies] = useState<string[]>([])
  const [ticker, setTicker] = useState(ALL_COMPANIES)
  const [question, setQuestion] = useState("")
  const [loadingCompanies, setLoadingCompanies] = useState(true)
  const [asking, setAsking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AskResponse | null>(null)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (!mounted) return

    let cancelled = false

    async function loadCompanies() {
      try {
        const response = await fetch(`${API_BASE}/companies`)
        if (!response.ok) {
          throw new Error(`Could not load companies (${response.status})`)
        }
        const data: unknown = await response.json()
        const tickers = Array.isArray(data)
          ? data.filter((item): item is string => typeof item === "string")
          : []
        if (!cancelled) {
          setCompanies(tickers)
          setError(null)
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Could not reach the API. Is it running on port 8000?"
          )
        }
      } finally {
        if (!cancelled) setLoadingCompanies(false)
      }
    }

    loadCompanies()
    return () => {
      cancelled = true
    }
  }, [mounted])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const trimmed = question.trim()
    if (!trimmed || asking) return

    setAsking(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: trimmed,
          ticker: ticker === ALL_COMPANIES ? null : ticker,
        }),
      })
      if (!response.ok) {
        throw new Error(`Ask failed (${response.status})`)
      }
      const data = (await response.json()) as AskResponse
      setResult({
        answer: data.answer,
        sources: Array.isArray(data.sources) ? data.sources : [],
      })
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong while asking the question."
      )
    } finally {
      setAsking(false)
    }
  }

  const handleQuickAction = (value: string) => {
    setQuestion(value)
  }

  if (!mounted) {
    return <AskFormFallback />
  }

  return (
    <div className="flex flex-col gap-8">
      <div className={`${GLASS_PANEL} flex flex-col gap-5 p-4 shadow-2xl shadow-black/40 sm:p-5`}>
        <form onSubmit={handleSubmit}>
          <FieldLabel htmlFor="question" className="sr-only">
            Question
          </FieldLabel>
          <div className="flex items-center gap-2 rounded-full bg-white/5 p-1.5 ring-1 ring-white/10 transition-colors focus-within:ring-white/25">
            {loadingCompanies ? (
              <Skeleton className="h-9 w-32 shrink-0 rounded-full bg-white/10" />
            ) : (
              <Select
                value={ticker}
                onValueChange={(value) => {
                  if (value) setTicker(value)
                }}
                disabled={asking}
              >
                <SelectTrigger
                  id="company"
                  aria-label="Company"
                  className="h-9 w-auto min-w-34 shrink-0 rounded-full border-0 bg-white/5 px-3.5 text-sm text-white/80 ring-1 ring-white/10 hover:bg-white/10 dark:bg-white/5 dark:hover:bg-white/10"
                >
                  <SelectValue placeholder="Select a company">
                    {ticker === ALL_COMPANIES ? "All companies" : ticker}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent align="start">
                  <SelectGroup>
                    <SelectItem value={ALL_COMPANIES}>All companies</SelectItem>
                    {companies.map((code) => (
                      <SelectItem key={code} value={code}>
                        {code}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            )}

            <span aria-hidden="true" className="h-6 w-px shrink-0 bg-white/10" />

            <div className="flex min-w-0 flex-1 items-center gap-2">
              <SearchIcon
                aria-hidden="true"
                className="size-4 shrink-0 text-white/40"
              />
              <Input
                id="question"
                name="question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="What antitrust issues is Apple facing?"
                disabled={asking}
                autoComplete="off"
                className="h-9 border-0 bg-transparent px-0 text-sm text-white placeholder:text-white/35 focus-visible:border-transparent focus-visible:ring-0 disabled:bg-transparent dark:bg-transparent dark:disabled:bg-transparent"
              />
            </div>

            <Button
              type="submit"
              size="icon-lg"
              aria-label={asking ? "Searching filings" : "Ask question"}
              disabled={asking || !question.trim()}
              className="size-9 shrink-0 rounded-full bg-white text-neutral-950 hover:bg-white/85"
            >
              {asking ? <Spinner /> : <ArrowRightIcon />}
            </Button>
          </div>
        </form>

        <div className="flex flex-col gap-2.5">
          <p className={SECTION_LABEL}>Quick actions</p>
          <div className="flex flex-wrap gap-2">
            {QUICK_ACTIONS.map((action) => (
              <Button
                key={action.label}
                type="button"
                variant="ghost"
                size="sm"
                disabled={asking}
                onClick={() => handleQuickAction(action.question)}
                className="rounded-full bg-white/5 px-3.5 text-xs font-medium text-white/70 ring-1 ring-white/10 hover:bg-white/10 hover:text-white dark:hover:bg-white/10"
              >
                {action.label}
              </Button>
            ))}
          </div>
        </div>
      </div>

      {error ? (
        <Alert
          variant="destructive"
          className="border-0 bg-red-500/10 text-red-100 ring-1 ring-red-400/20 backdrop-blur-xl"
        >
          <AlertTitle>Request failed</AlertTitle>
          <AlertDescription className="text-red-100/70">
            {error}
          </AlertDescription>
        </Alert>
      ) : null}

      {asking ? (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <Skeleton className="h-4 w-24 bg-white/10" />
            <Skeleton className="h-4 w-full bg-white/10" />
            <Skeleton className="h-4 w-5/6 bg-white/10" />
            <Skeleton className="h-4 w-2/3 bg-white/10" />
          </div>
          <div className="flex flex-col gap-3">
            <Skeleton className="h-24 w-full rounded-3xl bg-white/10" />
            <Skeleton className="h-24 w-full rounded-3xl bg-white/10" />
          </div>
        </div>
      ) : null}

      {!asking && result ? (
        <div className="flex flex-col gap-8">
          <section className={`${GLASS_PANEL} flex flex-col gap-3 p-5`}>
            <h2 className={SECTION_LABEL}>Answer</h2>
            <p className="whitespace-pre-wrap text-base leading-7 text-white/90">
              {result.answer}
            </p>
          </section>

          <Separator className="bg-white/10" />

          <section className="flex flex-col gap-4">
            <h2 className={SECTION_LABEL}>Sources</h2>
            {result.sources.length === 0 ? (
              <p className="text-sm text-white/50">
                No source chunks were returned for this answer.
              </p>
            ) : (
              <div className="flex flex-col gap-3">
                {result.sources.map((source, index) => (
                  <Card
                    key={`${source.ticker}-${source.item_number}-${index}`}
                    size="sm"
                    className="rounded-2xl bg-white/5 text-white/80 ring-1 ring-white/10 backdrop-blur-xl"
                  >
                    <CardHeader>
                      <CardTitle className="text-white">
                        {source.item_title || `Item ${source.item_number}`}
                      </CardTitle>
                      <CardDescription className="text-white/45">
                        {[source.ticker, source.item_number && `Item ${source.item_number}`, source.filing_date]
                          .filter(Boolean)
                          .join(" · ")}
                      </CardDescription>
                      <CardAction>
                        <Badge
                          variant="secondary"
                          className="bg-white/10 text-white/70 ring-1 ring-white/10 dark:bg-white/10"
                        >
                          {similarityLabel(source.similarity)}
                        </Badge>
                      </CardAction>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm leading-relaxed text-white/55">
                        {snippet(source.text ?? "")}
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </section>
        </div>
      ) : null}

      {!asking && !result && !error ? (
        <Empty className="rounded-3xl border border-dashed border-white/15 bg-white/5 backdrop-blur-xl">
          <EmptyHeader>
            <EmptyMedia
              variant="icon"
              className="bg-white/10 text-white ring-1 ring-white/10"
            >
              <FileSearchIcon />
            </EmptyMedia>
            <EmptyTitle className="text-white">No answer yet</EmptyTitle>
            <EmptyDescription className="text-white/50">
              Pick a company, ask a question, and we&apos;ll retrieve the matching
              filing sections.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : null}
    </div>
  )
}

export function AskFormFallback() {
  return (
    <div className="flex flex-col gap-8">
      <div className={`${GLASS_PANEL} flex flex-col gap-5 p-4 shadow-2xl shadow-black/40 sm:p-5`}>
        <div className="flex items-center gap-2 rounded-full bg-white/5 p-1.5 ring-1 ring-white/10">
          <Skeleton className="h-9 w-32 shrink-0 rounded-full bg-white/10" />
          <span aria-hidden="true" className="h-6 w-px shrink-0 bg-white/10" />
          <Skeleton className="h-4 flex-1 bg-white/10" />
          <Skeleton className="size-9 shrink-0 rounded-full bg-white/10" />
        </div>
        <div className="flex flex-col gap-2.5">
          <Skeleton className="h-3 w-24 bg-white/10" />
          <div className="flex flex-wrap gap-2">
            <Skeleton className="h-7 w-32 rounded-full bg-white/10" />
            <Skeleton className="h-7 w-28 rounded-full bg-white/10" />
            <Skeleton className="h-7 w-24 rounded-full bg-white/10" />
            <Skeleton className="h-7 w-36 rounded-full bg-white/10" />
          </div>
        </div>
      </div>
      <Skeleton className="h-32 w-full rounded-3xl bg-white/10" />
    </div>
  )
}
