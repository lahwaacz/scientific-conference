import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import App from "./App";
import reportWebVitals from "./reportWebVitals";
import "bootstrap/dist/css/bootstrap.min.css";
import { applyBaseUrlToFetch } from "./configuredFetch";
import { initConferenceSlug } from "./utils/conferenceSlug";

if (
  import.meta.env.VITE_BACKEND_API_BASE_URL !== undefined &&
  import.meta.env.VITE_BACKEND_API_BASE_URL !== ""
) {
  applyBaseUrlToFetch(import.meta.env.VITE_BACKEND_API_BASE_URL);
}

// Capture the conference slug before render (module singleton).
initConferenceSlug();

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://web.dev/articles/vitals
reportWebVitals();
