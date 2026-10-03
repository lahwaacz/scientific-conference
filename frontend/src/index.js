import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import App from "./App";
import reportWebVitals from "./reportWebVitals";
import "bootstrap/dist/css/bootstrap.min.css";
import { applyBaseUrlToFetch } from "./configuredFetch";

if (
  process.env.REACT_APP_BACKEND_API_BASE_URL !== undefined &&
  process.env.REACT_APP_BACKEND_API_BASE_URL !== ""
) {
  applyBaseUrlToFetch(process.env.REACT_APP_BACKEND_API_BASE_URL);
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
