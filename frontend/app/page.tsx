"use client"

import { useEffect, useState, type FormEvent } from "react"
import { FileSearchIcon, SearchIcon } from "lucide-react"

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
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
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

export default function Home() {
  const [companies, setCompanies] = useState<string[]>([])
  const [ticker, setTicker] = useState(ALL_COMPANIES)
  const [question, setQuestion] = useState("")
  const [loadingCompanies, setLoadingCompanies] = useState(true)
  const [asking, setAsking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AskResponse | null>(null)

  useEffect(() => {
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
  }, [])

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
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

        <form onSubmit={onSubmit}>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="company">Company</FieldLabel>
              {loadingCompanies ? (
                <Skeleton className="h-8 w-full" />
              ) : (
                <Select
                  value={ticker}
                  onValueChange={(value) => {
                    if (value) setTicker(value)
                  }}
                  disabled={asking}
                >
                  <SelectTrigger id="company" className="w-full">
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
            </Field>

            <div className="flex items-end gap-2">
              <Field className="flex-1">
                <FieldLabel htmlFor="question">Question</FieldLabel>
                <Input
                  id="question"
                  name="question"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="What antitrust issues is Apple facing?"
                  disabled={asking}
                  autoComplete="off"
                />
              </Field>
              <Button type="submit" disabled={asking || !question.trim()} size="lg">
                {asking ? (
                  <Spinner data-icon="inline-start" />
                ) : (
                  <SearchIcon data-icon="inline-start" />
                )}
                {asking ? "Searching" : "Ask"}
              </Button>
            </div>
          </FieldGroup>
        </form>

        {error ? (
          <Alert variant="destructive">
            <AlertTitle>Request failed</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        {asking ? (
          <div className="flex flex-col gap-6">
            <div className="flex flex-col gap-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-2/3" />
            </div>
            <div className="flex flex-col gap-3">
              <Skeleton className="h-24 w-full rounded-xl" />
              <Skeleton className="h-24 w-full rounded-xl" />
            </div>
          </div>
        ) : null}

        {!asking && result ? (
          <div className="flex flex-col gap-8">
            <section className="flex flex-col gap-3">
              <h2 className="text-sm font-medium text-muted-foreground">Answer</h2>
              <p className="whitespace-pre-wrap text-base leading-7">{result.answer}</p>
            </section>

            <Separator />

            <section className="flex flex-col gap-4">
              <h2 className="text-sm font-medium text-muted-foreground">Sources</h2>
              {result.sources.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No source chunks were returned for this answer.
                </p>
              ) : (
                <div className="flex flex-col gap-3">
                  {result.sources.map((source, index) => (
                    <Card key={`${source.ticker}-${source.item_number}-${index}`} size="sm">
                      <CardHeader>
                        <CardTitle>
                          {source.item_title || `Item ${source.item_number}`}
                        </CardTitle>
                        <CardDescription>
                          {[source.ticker, source.item_number && `Item ${source.item_number}`, source.filing_date]
                            .filter(Boolean)
                            .join(" · ")}
                        </CardDescription>
                        <CardAction>
                          <Badge variant="secondary">
                            {similarityLabel(source.similarity)}
                          </Badge>
                        </CardAction>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm leading-relaxed text-muted-foreground">
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
          <Empty className="border border-dashed">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <FileSearchIcon />
              </EmptyMedia>
              <EmptyTitle>No answer yet</EmptyTitle>
              <EmptyDescription>
                Pick a company, ask a question, and we&apos;ll retrieve the matching
                filing sections.
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : null}
      </main>
    </div>
  )
}
