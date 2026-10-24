import { Outlet } from "react-router";
import { Rail } from "./Rail";

export function Shell() {
  return (
    <div className="flex min-h-full bg-paper">
      <Rail />
      <main className="min-w-0 flex-1">
        <Outlet />
      </main>
    </div>
  );
}
