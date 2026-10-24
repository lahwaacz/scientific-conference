import { faGitlab } from "@fortawesome/free-brands-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { fetchWithAuth } from "../../utils/api";
import { getConferenceSlug } from "../../utils/conferenceSlug";
import Loader from "../ui/Loader/Loader";
import styles from "./AdminLoginModal.module.css";

export default function AdminLoginModal({ onSuccess, onClose }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [redirecting, setRedirecting] = useState(false);
  // null = the config has not arrived yet, otherwise the /api/auth/config/
  // payload; configError is set when that request itself fails.
  const [config, setConfig] = useState(null);
  const [configError, setConfigError] = useState("");

  const usernameRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const res = await fetchWithAuth("/api/auth/config/");
        if (!res.ok) {
          throw new Error(`auth config responded ${res.status}`);
        }
        const data = await res.json();
        if (!cancelled) {
          setConfig(data);
        }
      } catch {
        if (!cancelled) {
          setConfigError(
            "Sign-in options could not be loaded. Please try again later."
          );
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  // The password inputs may not exist on mount (config pending or GitLab
  // only), so focus follows the config instead of firing once on mount.
  useEffect(() => {
    if (config?.password_login_enabled) {
      usernameRef.current?.focus();
    }
  }, [config]);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetchWithAuth("/api/auth/login/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        setError("Wrong username or password");
        setLoading(false);
        return;
      }

      onSuccess();
    } catch {
      setError("Connection error");
      setLoading(false);
    }
  }

  async function signInWithGitLab() {
    setError("");
    setRedirecting(true);

    try {
      const slug = getConferenceSlug();
      const res = await fetchWithAuth(
        `/api/auth/gitlab/authorize/?next=${encodeURIComponent(slug ?? "")}`,
        { credentials: "include" }
      );

      if (!res.ok) {
        throw new Error(`gitlab authorize responded ${res.status}`);
      }

      const data = await res.json();
      window.location.assign(data.url);
    } catch {
      setError("GitLab sign-in could not be started. Please try again.");
      setRedirecting(false);
    }
  }

  const showGitLab = Boolean(config?.gitlab_login_enabled);
  const showPassword = Boolean(config?.password_login_enabled);
  // The backend refuses to start with both disabled; stay readable anyway.
  const showMisconfiguration = config !== null && !showGitLab && !showPassword;

  // One shared form instance: usernameRef must attach to exactly one render.
  const passwordForm = (
    <form onSubmit={submit}>
      <input
        id="admin-login-username"
        name="username"
        type="text"
        placeholder="Enter username"
        aria-label="Username"
        autoComplete="username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        disabled={loading}
        className={styles.input}
        ref={usernameRef}
      />

      <input
        id="admin-login-password"
        name="password"
        type="password"
        placeholder="Enter password"
        aria-label="Password"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        disabled={loading}
        className={styles.input}
      />

      <button type="submit" disabled={loading} className={styles.submitBtn}>
        {loading ? "Loading..." : "Login"}
      </button>
    </form>
  );

  // biome-ignore-start lint/a11y/noStaticElementInteractions lint/a11y/useKeyWithClickEvents: backdrop close/stopPropagation are redundant with the close button; dialog role carries semantics.
  return createPortal(
    <div className={styles.overlay} onClick={onClose} role="presentation">
      <div
        className={styles.modal}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Admin login"
      >
        <button
          className={styles.closeBtn}
          onClick={onClose}
          type="button"
          aria-label="Close"
        >
          ×
        </button>

        <h3 className={styles.title}>Admin Login</h3>

        {config === null && !configError && <Loader />}
        {configError && <p className={styles.error}>{configError}</p>}

        {showGitLab && (
          <button
            type="button"
            className={styles.gitlabBtn}
            onClick={signInWithGitLab}
            disabled={redirecting}
          >
            <FontAwesomeIcon icon={faGitlab} aria-hidden="true" />
            {redirecting ? "Redirecting..." : "Sign in with GitLab"}
          </button>
        )}

        {error && <p className={styles.error}>{error}</p>}

        {showMisconfiguration && (
          <p className={styles.error}>
            Sign-in is not configured for this site. Please contact the site
            administrator.
          </p>
        )}

        {showPassword &&
          (showGitLab ? (
            <details className={styles.details} open>
              <summary className={styles.summary}>Special account</summary>
              {passwordForm}
            </details>
          ) : (
            passwordForm
          ))}
      </div>
    </div>,
    document.body
  );
  // biome-ignore-end lint/a11y/noStaticElementInteractions lint/a11y/useKeyWithClickEvents: end of backdrop scope
}
