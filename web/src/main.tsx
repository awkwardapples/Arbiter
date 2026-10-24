import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./design/fonts";
import "./design/tokens.css";
import "@xyflow/react/dist/base.css";
import { App } from "./app/App";

const root = document.getElementById("root");
if (root) {
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}
