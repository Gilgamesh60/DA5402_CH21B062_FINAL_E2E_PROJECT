import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  { to: "/", label: "Analyze", end: true },
  { to: "/pipelines", label: "Pipelines" },
  { to: "/models", label: "Models" },
  { to: "/health", label: "Health" },
  { to: "/manual", label: "User Manual" },
];

export default function Layout() {
  return (
    <div className="min-h-full flex flex-col">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-md bg-brand-600 flex items-center justify-center">
                <span className="text-white font-bold text-sm">SS</span>
              </div>
              <div>
                <h1 className="text-lg font-semibold text-slate-900 leading-tight">
                  Stock Sentiment
                </h1>
                <p className="text-xs text-slate-500 leading-tight">MLOps demo</p>
              </div>
            </div>
            <nav className="flex items-center gap-1">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-brand-50 text-brand-700"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
        </div>
      </header>

      <main className="flex-1">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
          <Outlet />
        </div>
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-xs text-slate-500">
            Not financial advice. Sentiment predictions are derived from recent public text
            and can be wrong.
          </p>
        </div>
      </footer>
    </div>
  );
}
