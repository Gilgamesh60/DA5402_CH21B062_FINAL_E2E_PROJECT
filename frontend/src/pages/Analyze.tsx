import { FormEvent, useState } from "react";
import { api, ApiError, PredictResponse, Sentiment } from "../lib/api";
import { Badge, EmptyState, ErrorBanner, Spinner, Stat } from "../components/ui";

const TICKER_RE = /^[A-Z][A-Z0-9.-]{0,9}$/;

function sentimentTone(s: Sentiment): "green" | "red" | "slate" {
  if (s === "positive") return "green";
  if (s === "negative") return "red";
  return "slate";
}

export default function Analyze() {
  const [ticker, setTicker] = useState("AAPL");
  const [lookback, setLookback] = useState(24);
  const [explain, setExplain] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [error, setError] = useState<{ title: string; message?: string } | null>(null);
  const [feedbackSent, setFeedbackSent] = useState<Sentiment | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setFeedbackSent(null);
    const t = ticker.trim().toUpperCase();
    if (!TICKER_RE.test(t)) {
      setError({ title: "Invalid ticker", message: "Use uppercase letters like AAPL or BRK.A." });
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const res = await api.predict({
        ticker: t,
        lookback_hours: lookback,
        include_explanations: explain,
      });
      setResult(res);
    } catch (err) {
      const e = err as ApiError;
      if (e.status === 404) {
        setError({ title: "No recent data", message: `No records found for ${t} in the last ${lookback}h.` });
      } else if (e.status === 503) {
        setError({ title: "Model unavailable", message: "The model server is starting up — try again shortly." });
      } else {
        setError({ title: "Prediction failed", message: e.message });
      }
    } finally {
      setLoading(false);
    }
  }

  async function sendFeedback(label: Sentiment) {
    if (!result) return;
    try {
      await api.feedback({
        ticker: result.ticker,
        prediction_request_id: result.request_id,
        true_label: label,
      });
      setFeedbackSent(label);
    } catch (err) {
      setError({ title: "Couldn't record feedback", message: (err as Error).message });
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-1">
        <div className="card">
          <h2 className="text-base font-semibold text-slate-900 mb-4">Analyze a ticker</h2>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label htmlFor="ticker" className="label">Ticker</label>
              <input
                id="ticker"
                type="text"
                className="input mt-1 uppercase"
                value={ticker}
                maxLength={10}
                autoComplete="off"
                spellCheck={false}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="AAPL"
              />
            </div>
            <div>
              <label htmlFor="lookback" className="label">
                Lookback window: <span className="font-normal text-slate-500">{lookback}h</span>
              </label>
              <input
                id="lookback"
                type="range"
                min={1}
                max={168}
                step={1}
                value={lookback}
                onChange={(e) => setLookback(Number(e.target.value))}
                className="mt-2 w-full"
              />
              <p className="mt-1 text-xs text-slate-500">
                How many hours back to look for news + social mentions.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <input
                id="explain"
                type="checkbox"
                checked={explain}
                onChange={(e) => setExplain(e.target.checked)}
                className="rounded border-slate-300 text-brand-600 focus:ring-brand-600"
              />
              <label htmlFor="explain" className="text-sm text-slate-700">
                Show contributing snippets
              </label>
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading && <Spinner className="h-4 w-4 mr-2" />}
              {loading ? "Analyzing…" : "Analyze"}
            </button>
          </form>
        </div>
      </div>

      <div className="lg:col-span-2">
        {error && (
          <ErrorBanner
            title={error.title}
            message={error.message}
            onDismiss={() => setError(null)}
          />
        )}

        {!result && !loading && (
          <div className="card">
            <EmptyState
              title="No prediction yet"
              hint="Enter a ticker on the left to see its current sentiment."
            />
          </div>
        )}

        {loading && (
          <div className="card flex items-center justify-center py-12 text-slate-500">
            <Spinner className="h-5 w-5 mr-2" /> Fetching prediction…
          </div>
        )}

        {result && (
          <div className="space-y-6">
            <div className="card">
              <div className="flex items-start justify-between mb-6">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500 font-medium">
                    Ticker
                  </p>
                  <h3 className="text-2xl font-bold text-slate-900 mt-1">{result.ticker}</h3>
                </div>
                <Badge tone={sentimentTone(result.sentiment)}>{result.sentiment}</Badge>
              </div>
              <div className="grid grid-cols-3 gap-4 pb-6 border-b border-slate-100">
                <Stat
                  label="Confidence"
                  value={`${(result.confidence * 100).toFixed(1)}%`}
                  tone={sentimentTone(result.sentiment)}
                />
                <Stat label="Sample size" value={result.sample_size} />
                <Stat label="Latency" value={`${result.latency_ms} ms`} />
              </div>
              <div className="mt-6">
                <p className="text-xs uppercase tracking-wide text-slate-500 font-medium mb-3">
                  Probability breakdown
                </p>
                <div className="space-y-2">
                  {(["positive", "neutral", "negative"] as const).map((lbl) => {
                    const v = result.scores[lbl];
                    return (
                      <div key={lbl} className="flex items-center gap-3">
                        <span className="text-sm w-20 text-slate-700 capitalize">{lbl}</span>
                        <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                          <div
                            className={`h-full ${
                              lbl === "positive"
                                ? "bg-green-500"
                                : lbl === "negative"
                                ? "bg-red-500"
                                : "bg-slate-400"
                            }`}
                            style={{ width: `${v * 100}%` }}
                          />
                        </div>
                        <span className="text-sm w-12 text-right text-slate-600 tabular-nums">
                          {(v * 100).toFixed(1)}%
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="mt-6 pt-6 border-t border-slate-100 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                <span>
                  Model:{" "}
                  <span className="font-medium text-slate-700">
                    {result.model.name} v{result.model.version}
                  </span>
                </span>
                <span>·</span>
                <span>Stage: {result.model.stage}</span>
                <span>·</span>
                <span>Request: <span className="font-mono">{result.request_id.slice(0, 8)}</span></span>
              </div>
            </div>

            {result.explanations.length > 0 && (
              <div className="card">
                <p className="text-xs uppercase tracking-wide text-slate-500 font-medium mb-3">
                  Contributing snippets
                </p>
                <ul className="space-y-3">
                  {result.explanations.map((ex, i) => (
                    <li
                      key={i}
                      className="border-l-2 border-brand-200 pl-3 text-sm text-slate-700"
                    >
                      <p>{ex.snippet}</p>
                      <p className="text-xs text-slate-400 mt-1">
                        {ex.source} · contribution {(ex.contribution * 100).toFixed(1)}%
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="card">
              <p className="text-xs uppercase tracking-wide text-slate-500 font-medium mb-3">
                Is this right?
              </p>
              {feedbackSent ? (
                <p className="text-sm text-green-700">
                  Thanks — recorded as <span className="font-semibold">{feedbackSent}</span>.
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {(["positive", "neutral", "negative"] as const).map((lbl) => (
                    <button
                      key={lbl}
                      type="button"
                      onClick={() => sendFeedback(lbl)}
                      className="btn-secondary capitalize"
                    >
                      {lbl}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
