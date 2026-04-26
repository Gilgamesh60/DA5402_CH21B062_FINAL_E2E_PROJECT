import { useEffect, useState } from "react";
import { config } from "../lib/config";
import { Badge, Spinner } from "../components/ui";

interface PipelineStage {
  name: string;
  description: string;
  tool: string;
}

const stages: PipelineStage[] = [
  { name: "ingest", description: "Pull financial news + social text", tool: "Airflow → DVC" },
  { name: "validate", description: "Schema + length + dedup", tool: "DVC" },
  { name: "eda_baselines", description: "Compute drift baselines", tool: "DVC" },
  { name: "features", description: "Clean + TF-IDF vectorize", tool: "DVC" },
  { name: "train", description: "Train classifier, log to MLflow", tool: "DVC + MLflow" },
  { name: "evaluate", description: "Test metrics, promote to Production", tool: "DVC + MLflow" },
  { name: "drift", description: "KS + JSD vs baselines, emit metrics", tool: "Airflow + Prometheus" },
];

interface Target {
  health: string;
  labels: { job: string };
}

export default function Pipelines() {
  const [targets, setTargets] = useState<Target[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Scrape Prometheus targets to show live health. Fail open — this is a
    // demo aid, not critical path.
    fetch(`${config.prometheusUrl}/api/v1/targets?state=active`)
      .then((r) => r.json())
      .then((d) => setTargets(d.data.activeTargets))
      .catch(() => setTargets([]))
      .finally(() => setLoading(false));
  }, []);

  const toolByName: Record<string, { url: string; label: string }> = {
    Airflow: { url: config.airflowUrl, label: "Open Airflow" },
    MLflow: { url: config.mlflowUrl, label: "Open MLflow" },
    Prometheus: { url: config.prometheusUrl, label: "Open Prometheus" },
    Grafana: { url: config.grafanaUrl, label: "Open Grafana" },
  };

  return (
    <div className="space-y-6">
      <div className="card">
        <h2 className="text-base font-semibold text-slate-900 mb-1">ML pipeline</h2>
        <p className="text-sm text-slate-600">
          End-to-end lineage from raw text to a production-deployed model. Click any
          MLOps tool to open its native UI for deeper inspection.
        </p>
      </div>

      <div className="card">
        <h3 className="text-sm font-semibold text-slate-900 mb-4">Stages</h3>
        <ol className="relative space-y-4">
          {stages.map((s, i) => (
            <li key={s.name} className="flex gap-4 items-start">
              <div className="flex flex-col items-center">
                <div className="flex-shrink-0 h-8 w-8 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-sm font-semibold">
                  {i + 1}
                </div>
                {i < stages.length - 1 && <div className="w-0.5 h-8 bg-slate-200 mt-1" />}
              </div>
              <div className="flex-1 pb-2">
                <div className="flex items-center gap-2">
                  <code className="text-sm font-mono text-slate-900">{s.name}</code>
                  <Badge tone="brand">{s.tool}</Badge>
                </div>
                <p className="text-sm text-slate-600 mt-0.5">{s.description}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>

      <div className="card">
        <h3 className="text-sm font-semibold text-slate-900 mb-4">
          Live tool consoles
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {Object.entries(toolByName).map(([name, t]) => (
            <a
              key={name}
              href={t.url}
              target="_blank"
              rel="noreferrer noopener"
              className="rounded-md border border-slate-200 p-4 hover:border-brand-400 hover:bg-brand-50 transition-colors"
            >
              <p className="font-semibold text-slate-900">{name}</p>
              <p className="text-xs text-slate-500 mt-1">{t.label} →</p>
            </a>
          ))}
        </div>
      </div>

      <div className="card">
        <h3 className="text-sm font-semibold text-slate-900 mb-3">Scrape targets</h3>
        {loading && (
          <p className="text-sm text-slate-500 flex items-center gap-2">
            <Spinner /> Loading targets…
          </p>
        )}
        {!loading && targets && targets.length === 0 && (
          <p className="text-sm text-slate-500">
            Couldn't reach Prometheus from the browser — check{" "}
            <a href={config.prometheusUrl} className="text-brand-600 hover:underline">
              {config.prometheusUrl}
            </a>{" "}
            directly.
          </p>
        )}
        {!loading && targets && targets.length > 0 && (
          <ul className="divide-y divide-slate-100">
            {targets.map((t, i) => (
              <li key={i} className="py-2 flex items-center justify-between">
                <span className="text-sm text-slate-700 font-mono">{t.labels.job}</span>
                <Badge tone={t.health === "up" ? "green" : "red"}>
                  {t.health.toUpperCase()}
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
