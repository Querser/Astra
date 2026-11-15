import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import "./telemetry/telemetry.css";
import "./styles.css";
import { reportClientEvent } from "./api";

window.addEventListener("error", () => reportClientEvent("ui_exception"));
window.addEventListener("unhandledrejection", () => reportClientEvent("ui_exception"));

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
