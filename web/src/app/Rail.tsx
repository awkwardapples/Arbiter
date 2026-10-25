import { Activity, BookMarked, ClipboardCheck, FolderOpen, Gauge, ScrollText, Server } from "lucide-react";
import { NavLink } from "react-router";
import { cn } from "../ui/lib/cn";
import { ClassicConsoleLink } from "./ClassicConsole";

// The shadcn sidebar pattern reduced to a fixed rail: labels always visible (design §10).
const NAV = [
  { to: "/", label: "Assess", icon: ClipboardCheck, end: true },
  { to: "/cases", label: "Cases", icon: FolderOpen },
  { to: "/memory", label: "Memory", icon: BookMarked },
  { to: "/sources", label: "Sources", icon: Server },
  { to: "/provider", label: "Provider", icon: Activity },
  { to: "/audit", label: "Audit", icon: ScrollText },
  { to: "/evaluation", label: "Evaluation", icon: Gauge },
];

export function Rail() {
  return (
    <nav aria-label="Main" className="sticky top-0 flex h-screen w-[200px] shrink-0 flex-col border-r border-hairline bg-sheet max-lg:w-[64px]">
      <NavLink to="/" className="m-3 flex items-center justify-center rounded-panel bg-ink px-3 py-2" aria-label="Arbiter home">
        {/* The wordmark is white on transparent, so it sits on an ink tile. */}
        <img src={`${import.meta.env.BASE_URL}arbiter_logo.png`} alt="Arbiter" className="h-9 w-auto max-lg:h-6" />
      </NavLink>
      <ul className="flex flex-1 flex-col gap-0.5 px-2">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <li key={to}>
            <NavLink
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-[6px] px-3 py-2 text-sm font-medium text-graphite hover:bg-well hover:text-ink",
                  isActive && "bg-well text-ink",
                )
              }
            >
              <Icon className="size-4 shrink-0" aria-hidden />
              <span className="max-lg:sr-only">{label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
      <div className="border-t border-hairline px-2 py-3">
        <ClassicConsoleLink />
      </div>
    </nav>
  );
}
