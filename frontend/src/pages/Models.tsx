import { useEffect, useState } from "react";
import { api, ApiError, ModelInfo, VersionSummary } from "../lib/api";
import { Badge, ErrorBanner, Spinner } from "../components/ui";

function stageTone(stage: string): "green" | "amber" | "slate" {
  if (stage === "Production") return "green";
  if (stage === "Staging") return "amber";
  return "slate";
}

export default function Models() {
  const [versions, setVersions] = useState<VersionSummary[] | null>(null);
  const [info, setInfo] = useState<ModelInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [rolling, setRolling] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info_msg, setInfoMsg] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [v, i] = await Promise.all([api.modelVersions(), api.modelInfo().catch(() => null)]);
      setVersions(v.versions);
      setInfo(i);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function rollback(version: string) {
    if (!confirm(`Roll Production back to version ${version}?`)) return;
    setRolling(version);
    setError(null);
    setInfoMsg(null);
    try {
      const res = await api.rollback(version);
      setInfoMsg(
        `Rollback staged: previous v${res.previous.version} → archived; v${res.current.version} now Production. Restart model-server to load the new version.`
      );
      await load();
    } catch (e) {
      const err = e as ApiError;
      setError(
        err.status === 403
          ? "Rollback only allowed from the local docker network."
          : err.message
      );
    } finally {
      setRolling(null);
    }
  }

  return (
    <div className="space-y-6">
      {error && <ErrorBanner title="Something went wrong" message={error} onDismiss={() => setError(null)} />}
      {info_msg && (
        <div className="rounded-md bg-green-50 border border-green-200 p-4 text-sm text-green-800">
          {info_msg}
        </div>
      )}

      <div className="card">
        <h2 className="text-base font-semibold text-slate-900 mb-4">Current production model</h2>
        {loading && <p className="text-sm text-slate-500 flex items-center gap-2"><Spinner /> loading…</p>}
        {info && (
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Name</dt>
              <dd className="mt-1 font-medium">{info.name}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Version</dt>
              <dd className="mt-1 font-medium">v{info.version}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Git SHA</dt>
              <dd className="mt-1 font-mono text-xs">
                {info.git_commit_sha?.slice(0, 10) ?? "—"}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">MLflow run</dt>
              <dd className="mt-1 font-mono text-xs">
                {info.mlflow_run_id?.slice(0, 10) ?? "—"}
              </dd>
            </div>
          </dl>
        )}
      </div>

      <div className="card">
        <h2 className="text-base font-semibold text-slate-900 mb-4">Registry versions</h2>
        {!versions && loading && (
          <p className="text-sm text-slate-500 flex items-center gap-2"><Spinner /> loading…</p>
        )}
        {versions && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="py-2 font-medium">Version</th>
                  <th className="py-2 font-medium">Stage</th>
                  <th className="py-2 font-medium">macro-F1</th>
                  <th className="py-2 font-medium">Trained</th>
                  <th className="py-2 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {versions.map((v) => (
                  <tr key={v.version} className="border-b border-slate-100 last:border-0">
                    <td className="py-3 font-medium">v{v.version}</td>
                    <td className="py-3">
                      <Badge tone={stageTone(v.stage)}>{v.stage}</Badge>
                    </td>
                    <td className="py-3 tabular-nums">
                      {v.macro_f1 != null ? v.macro_f1.toFixed(4) : "—"}
                    </td>
                    <td className="py-3 text-slate-500">
                      {v.trained_at
                        ? new Date(v.trained_at).toLocaleString()
                        : "—"}
                    </td>
                    <td className="py-3 text-right">
                      {v.stage !== "Production" && (
                        <button
                          type="button"
                          disabled={rolling === v.version}
                          onClick={() => rollback(v.version)}
                          className="btn-secondary text-xs"
                        >
                          {rolling === v.version ? <Spinner className="h-3 w-3" /> : "Roll to Prod"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
