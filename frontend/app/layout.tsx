import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentFlow — AI Task Execution Platform",
  description: "Production-grade AI task execution platform with human-in-the-loop approvals and real-time streaming.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
          <header className="border-b border-slate-200 bg-white/70 backdrop-blur sticky top-0 z-40">
            <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
              <a href="/" className="flex items-center gap-2 font-semibold text-slate-900">
                <span className="inline-block w-8 h-8 rounded-lg bg-gradient-to-br from-sky-500 to-indigo-600" />
                AgentFlow
              </a>
              <nav className="flex items-center gap-6 text-sm">
                <a href="/" className="text-slate-600 hover:text-slate-900">New Task</a>
                <a href="/dashboard" className="text-slate-600 hover:text-slate-900">Dashboard</a>
              </nav>
            </div>
          </header>
          <main className="max-w-6xl mx-auto px-6 py-10">{children}</main>
        </div>
      </body>
    </html>
  );
}
