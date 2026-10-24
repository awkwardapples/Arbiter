import { createBrowserRouter, type RouteObject } from "react-router";
import AssessPage from "../pages/assess";
import AuditPage from "../pages/audit";
import CasePage from "../pages/case";
import CasesPage from "../pages/cases";
import EvaluationPage from "../pages/evaluation";
import MemoryPage from "../pages/memory";
import NewAssessmentPage from "../pages/new";
import ProviderPage from "../pages/provider";
import ReviewPage from "../pages/review";
import { LiveRunPage, RecordingPage } from "../pages/run";
import SourcesPage from "../pages/sources";
import { NotFound } from "./NotFound";
import { Shell } from "./Shell";

// Every page has a route from day one; 18c and 18d replace their own page files only.
export const routes: RouteObject[] = [
  {
    path: "/",
    element: <Shell />,
    children: [
      { index: true, element: <AssessPage /> },
      { path: "runs/:runId", element: <LiveRunPage /> },
      { path: "recordings/:runId", element: <RecordingPage /> },
      { path: "cases", element: <CasesPage /> },
      { path: "cases/:caseId", element: <CasePage /> },
      { path: "memory", element: <MemoryPage /> },
      { path: "review/:caseId", element: <ReviewPage /> },
      { path: "sources", element: <SourcesPage /> },
      { path: "provider", element: <ProviderPage /> },
      { path: "audit", element: <AuditPage /> },
      { path: "evaluation", element: <EvaluationPage /> },
      { path: "new", element: <NewAssessmentPage /> },
      { path: "*", element: <NotFound /> },
    ],
  },
];

export const router = createBrowserRouter(routes, { basename: "/console" });
