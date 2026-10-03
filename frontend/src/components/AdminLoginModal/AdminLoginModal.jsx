import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { fetchWithAuth } from "../../utils/api";
import styles from "./AdminLoginModal.module.css";

export default function AdminLoginModal({ onSuccess, onClose }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const passwordRef = useRef(null);

  useEffect(() => {
    passwordRef.current?.focus();
  }, []);

  useEffect(() => {
    const scrollbarWidth =
      window.innerWidth - document.documentElement.clientWidth;

    document.body.style.overflow = "hidden";
    document.body.style.paddingRight = `${scrollbarWidth}px`;

    return () => {
      document.body.style.overflow = "";
      document.body.style.paddingRight = "";
    };
  }, []);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetchWithAuth("/api/auth/login/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: "admin",
          password,
        }),
      });

      if (!res.ok) {
        setError("Wrong password");
        setLoading(false);
        return;
      }

      const data = await res.json();

      localStorage.setItem("access_token", data.access);
      localStorage.setItem("refresh_token", data.refresh);

      onSuccess();
    } catch {
      setError("Connection error");
      setLoading(false);
    }
  }

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

        <form onSubmit={submit}>
          <h3 className={styles.title}>Admin Login</h3>

          <input
            type="password"
            placeholder="Enter password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
            className={styles.input}
            ref={passwordRef}
          />

          {error && <p className={styles.error}>{error}</p>}

          <button type="submit" disabled={loading} className={styles.submitBtn}>
            {loading ? "Loading..." : "Login"}
          </button>
        </form>
      </div>
    </div>,
    document.body
  );
  // biome-ignore-end lint/a11y/noStaticElementInteractions lint/a11y/useKeyWithClickEvents: end of backdrop scope
}
