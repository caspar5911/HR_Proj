import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { CalendarDays, LayoutDashboard, Loader2, ShieldCheck, Users, Wallet } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/**
 * Demo accounts (seeded by backend/seed_demo.py). One click fills the form so
 * the role-aware UI can be explored without typing credentials.
 */
const DEMO_ACCOUNTS = [
  { label: "Admin", email: "admin@example.com", password: "admin123", hint: "Full operations access" },
  { label: "Manager", email: "manager@example.com", password: "manager123", hint: "Approvals + dashboard" },
  { label: "Employee", email: "employee@example.com", password: "employee123", hint: "Self-service My Home" },
];

const FEATURES = [
  { icon: Users, text: "People directory with departments, roles and org chart" },
  { icon: CalendarDays, text: "Leave requests, balances and a team absence calendar" },
  { icon: Wallet, text: "Payroll runs with one-click calculation and printable payslips" },
  { icon: LayoutDashboard, text: "Live analytics — hiring trend, headcount and utilization" },
];

export default function LoginPage() {
  const { login, isLoading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
      </div>
    );
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email, password);
      // Successful login flips isAuthenticated — PublicOnlyRoute redirects to /
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Invalid email or password.");
      setSubmitting(false);
    }
  }

  function fill(account: (typeof DEMO_ACCOUNTS)[number]) {
    setEmail(account.email);
    setPassword(account.password);
    setError(null);
  }

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* Brand panel */}
      <div className="hidden lg:flex w-[46%] flex-col justify-between bg-slate-900 p-12 text-white">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 text-xl font-bold">
            A
          </div>
          <div>
            <p className="text-lg font-bold leading-tight">Arella HR</p>
            <p className="text-xs text-slate-400">People &amp; payroll platform</p>
          </div>
        </div>

        <div className="space-y-8">
          <h2 className="text-3xl font-bold leading-tight">
            Everything your people team needs,
            <br />
            <span className="text-blue-400">in one place.</span>
          </h2>
          <ul className="space-y-4">
            {FEATURES.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-start gap-3 text-sm text-slate-300">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-800">
                  <Icon className="h-4 w-4 text-blue-400" />
                </div>
                <span className="pt-1.5">{text}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="text-xs text-slate-500">
          © 2026 Arella HR · Secure access with role-based permissions
        </p>
      </div>

      {/* Form panel */}
      <div className="flex flex-1 items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 text-white text-lg font-bold">
              A
            </div>
            <div>
              <p className="text-base font-bold leading-tight">Arella HR</p>
              <p className="text-[11px] text-slate-500">People &amp; payroll platform</p>
            </div>
          </div>

          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Sign in</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Use your work account to continue.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                required
                autoComplete="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                required
                autoComplete="current-password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            {error && (
              <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </div>
            )}

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <ShieldCheck className="h-4 w-4 mr-2" />
              )}
              {submitting ? "Signing in…" : "Sign In"}
            </Button>
          </form>

          {/* Demo accounts */}
          <div className="mt-8 rounded-lg border border-dashed border-slate-300 bg-white p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Demo accounts
            </p>
            <div className="mt-3 grid grid-cols-3 gap-2">
              {DEMO_ACCOUNTS.map((a) => (
                <button
                  key={a.label}
                  type="button"
                  onClick={() => fill(a)}
                  title={a.hint}
                  className="rounded-md border border-slate-200 bg-slate-50 px-2 py-2 text-xs font-medium text-slate-700 transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
                >
                  {a.label}
                </button>
              ))}
            </div>
            <p className="mt-2 text-[11px] text-slate-400">
              Click a role to fill the form, then sign in.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
