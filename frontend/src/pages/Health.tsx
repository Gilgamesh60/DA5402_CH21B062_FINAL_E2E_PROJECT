import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { config } from "../lib/config";
import { Badge, Spinner } from "../components/ui";

interface ServiceCheck {
  name: string;
  description: string;
  url: string;
  mode: "cors" | "no-cors";  // no-cors for services without CORS headers
  status: "checking" | "ok" | "fail";
  detail?: string;
}

const defaultChecks: ServiceCheck[] = [
  { name: "API",         description: "FastAPI gateway", url: "/api/health", mode: "cors", status: "checking" },
  { name: "Model ready", description: "Production model loaded", url: "/api/ready", mode: "cors", status: "checking" },
  { name: "MLflow",      description: "Tracking + Registry", url: `${config.mlflowUrl}/health`, mode: "no-cors", status: "checking" },
  { name: "Prometheus",  description: "Metrics + alerts", url: `${config.prometheusUrl}/-/healthy`, mode: "no-cors", status: "checking" },
  { name: "Grafana",     description: "Dashboards", url: `${config.grafanaUrl}/api/health`, mode: "no-cors", status: "checking" },
  { name: "Airflow",     description: "Scheduled pipelines", url: `${config.airflowUrl}/health`, mode: "no-cors", status: "checking" },
];

export default function Health() {
  const [checks, setChecks] = useState<ServiceCheck[]>(defaultChecks);

  useEffect(() => {
    let cancelled = false;

    async function runChecks() {
      const next = await Promise.all(
        defaultChecks.map(async (c): Promise<ServiceCheck> => {
          try {
            if (c.mode === "cors") {
              if (c.url.endsWith("/ready")) {
                const r = await api.ready();
                return {
                  ...c,
                  status: r.status === "ready" ? "ok" : "fail",
                  detail:
                    r.status === "ready" && r.model
                      ? `v${r.model.version} (${r.model.stage})`
                      : r.reason ?? r.status,
                };
              }
              await api.health();
              return { ...c, status: "ok" };
            }
            // no-cors: can't read response but `ok` means reachable
            await fetch(c.url, { mode: "no-cors" });
            return { ...c, status: "ok", detail: "reachable" };
          } catch {
            return { ...c, status: "fail" };
          }
        })
      );
      if (!cancelled) setChecks(next);
    }

    runChecks();
    const t = setInterval(runChecks, 15_000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);

  return (
    <div className="space-y-6">
      <div className="card">
        <h2 className="text-base font-semibold text-slate-900 mb-1">Service status</h2>
        <p className="text-sm text-slate-600">
          Live health probes of every service in the stack. Refreshes every 15 seconds.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {checks.map((c) => (
          <div key={c.name} className="card flex items-start justify-between">
            <div>
              <p className="font-semibold text-slate-900">{c.name}</p>
              <p className="text-xs text-slate-500 mt-0.5">{c.description}</p>
              {c.detail && (
                <p className="mt-3 text-xs font-mono text-slate-600">{c.detail}</p>
              )}
            </div>
            <div>
              {c.status === "checking" && <Spinner className="h-4 w-4 text-slate-400" />}
              {c.status === "ok" && <Badge tone="green">Healthy</Badge>}
              {c.status === "fail" && <Badge tone="red">Down</Badge>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
