// Runtime configuration. Replaced by the nginx container entrypoint
// with the live env values. Used by src/lib/config.ts.
window.SSA_CONFIG = {
  apiBaseUrl: "/api",
  mlflowUrl: "http://localhost:5000",
  airflowUrl: "http://localhost:8080",
  grafanaUrl: "http://localhost:3001",
  prometheusUrl: "http://localhost:9090"
};
