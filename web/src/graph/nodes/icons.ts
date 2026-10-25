import {
  BookMarked,
  Boxes,
  Cpu,
  Database,
  FileSignature,
  FileText,
  Gavel,
  type LucideIcon,
  MessageSquareText,
  Network,
  PenLine,
  Route,
  Scale,
  ScanSearch,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Stamp,
  Swords,
  TriangleAlert,
} from "lucide-react";

const ICONS: Record<string, LucideIcon> = {
  planner: Route,
  evidence: ScanSearch,
  evaluator: Scale,
  challenger: Swords,
  guard: ShieldCheck,
  usl: Network,
  engine: Cpu,
  policy: Gavel,
  memory: BookMarked,
  reporter: PenLine,
  contract: FileSignature,
  outcome: Stamp,
  clash: TriangleAlert,
  "vendor.answers": MessageSquareText,
  "vendor.documents": FileText,
  "vendor.components": Boxes,
  "rec.kev": ShieldAlert,
};

export function iconFor(id: string): LucideIcon {
  if (id.startsWith("model:")) return Sparkles;
  return ICONS[id] ?? Database;
}
