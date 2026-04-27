export default function Manual() {
  return (
    <article className="prose prose-slate max-w-none">
      <div className="card">
        <h1 className="text-xl font-bold text-slate-900 mb-4">User manual</h1>
        <p className="text-sm text-slate-600 mb-6">
          A short walkthrough for non-technical users. Everything here runs
          locally — no cloud, no account, no PII.
        </p>

        <section className="mb-8">
          <h2 className="text-base font-semibold text-slate-900 mb-2">
            1. What this app does
          </h2>
          <p className="text-sm text-slate-700">
            Given a stock ticker like <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">AAPL</code>,
            the app returns a sentiment score — <em>positive</em>, <em>neutral</em>,
            or <em>negative</em> — computed from recent financial news and social
            media posts referencing that ticker. Each prediction includes a
            confidence percentage and the supporting sample size.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-base font-semibold text-slate-900 mb-2">
            2. Analyze a ticker
          </h2>
          <ol className="list-decimal pl-6 text-sm text-slate-700 space-y-1.5">
            <li>Click <strong>Analyze</strong> in the top navigation.</li>
            <li>Type a ticker (uppercase, e.g. <code className="text-xs bg-slate-100 px-1 rounded">MSFT</code>).</li>
            <li>Adjust the lookback slider if you want more or less history.</li>
            <li>Check <strong>Show contributing snippets</strong> to see which texts influenced the result.</li>
            <li>Click <strong>Analyze</strong>.</li>
          </ol>
          <p className="mt-3 text-sm text-slate-700">
            After a prediction arrives, tell us whether it was right using the
            feedback buttons. This data is logged so the model can be retrained
            on real mistakes over time.
          </p>
          <figure className="mt-4 rounded-md border border-slate-200 overflow-hidden bg-slate-50">
            <img
              src="/manual-analyze.png"
              alt="Screenshot of the Analyze screen with a sample prediction for AAPL"
              className="w-full block"
              loading="lazy"
            />
            <figcaption className="text-xs text-slate-500 p-2 border-t border-slate-200">
              Example result with contributing snippets enabled.
            </figcaption>
          </figure>
        </section>

        <section className="mb-8">
          <h2 className="text-base font-semibold text-slate-900 mb-2">
            3. Understand the result
          </h2>
          <ul className="list-disc pl-6 text-sm text-slate-700 space-y-1.5">
            <li><strong>Sentiment</strong> — the single label the model is most sure about.</li>
            <li><strong>Confidence</strong> — how strongly it backs that label, 0–100%.</li>
            <li><strong>Sample size</strong> — how many news + social records were aggregated.</li>
            <li><strong>Latency</strong> — end-to-end response time in milliseconds.</li>
            <li><strong>Probability breakdown</strong> — the distribution across all three classes.</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-base font-semibold text-slate-900 mb-2">
            4. Inspect the pipeline
          </h2>
          <p className="text-sm text-slate-700">
            The <strong>Pipelines</strong> screen shows every stage from raw
            ingestion to a deployed model, plus quick links to each underlying
            MLOps tool (Airflow, MLflow, Prometheus, Grafana). Scrape targets
            at the bottom of the page show which services Prometheus is
            successfully monitoring right now.
          </p>
          <figure className="mt-4 rounded-md border border-slate-200 overflow-hidden bg-slate-50">
            <img
              src="/manual-pipelines.png"
              alt="Screenshot of the Pipelines screen"
              className="w-full block"
              loading="lazy"
            />
          </figure>
        </section>

        <section className="mb-8">
          <h2 className="text-base font-semibold text-slate-900 mb-2">
            5. Manage models
          </h2>
          <p className="text-sm text-slate-700">
            The <strong>Models</strong> screen lists every version in the MLflow
            Model Registry with its stage (Production / Staging / Archived) and
            test-set macro-F1 score. If a newly-deployed model misbehaves,
            click <em>Roll to Prod</em> next to an older Staging or Archived
            version to promote it back. A model-server restart is required for
            the change to take effect.
          </p>
          <figure className="mt-4 rounded-md border border-slate-200 overflow-hidden bg-slate-50">
            <img
              src="/manual-models.png"
              alt="Screenshot of the Models screen"
              className="w-full block"
              loading="lazy"
            />
          </figure>
        </section>

        <section className="mb-8">
          <h2 className="text-base font-semibold text-slate-900 mb-2">
            6. Service health
          </h2>
          <p className="text-sm text-slate-700">
            The <strong>Health</strong> screen pings every component every 15
            seconds. If any tile turns red, click the link to the respective
            tool's own admin page for a deeper look.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-base font-semibold text-slate-900 mb-2">
            7. Privacy and safety
          </h2>
          <ul className="list-disc pl-6 text-sm text-slate-700 space-y-1.5">
            <li>No personal data is collected or stored.</li>
            <li>Predictions run locally — nothing leaves your machine.</li>
            <li>This is a research demo, <strong>not financial advice.</strong></li>
          </ul>
        </section>

        <section className="mb-2">
          <h2 className="text-base font-semibold text-slate-900 mb-2">
            8. Glossary
          </h2>
          <dl className="text-sm text-slate-700 space-y-2">
            <div>
              <dt className="font-medium">Sentiment</dt>
              <dd className="text-slate-600">Whether text expresses positive, negative, or neutral feelings.</dd>
            </div>
            <div>
              <dt className="font-medium">F1 score</dt>
              <dd className="text-slate-600">A quality metric for classifiers — higher is better, max 1.0.</dd>
            </div>
            <div>
              <dt className="font-medium">Drift</dt>
              <dd className="text-slate-600">When live data starts looking different from what the model trained on. The app monitors for it and alerts automatically.</dd>
            </div>
            <div>
              <dt className="font-medium">Rollback</dt>
              <dd className="text-slate-600">Restoring an earlier model version when the current one breaks.</dd>
            </div>
          </dl>
        </section>
      </div>
    </article>
  );
}
