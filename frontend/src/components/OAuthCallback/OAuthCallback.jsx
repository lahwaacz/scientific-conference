import { useEffect, useRef, useState } from "react";
import { buildApiUrl } from "../../utils/api";
import { getDeployedBasePath } from "../../utils/conferenceSlug";
import Loader from "../ui/Loader/Loader";
import styles from "./OAuthCallback.module.css";

function readCallbackParams() {
  const params = new URLSearchParams(window.location.search);
  return {
    code: params.get("code"),
    state: params.get("state"),
    error: params.get("error"),
  };
}

// Only root-relative targets may be followed: an absolute or
// protocol-relative "next" would be an open redirect, and browsers
// normalize backslashes to slashes ("/\evil" acts like "//evil").
function safeNext(next) {
  if (next?.startsWith("/") && !next.startsWith("//") && !next.includes("\\")) {
    return next;
  }
  // Never fall back to the domain root: on a subpath deployment that is
  // outside the SPA.
  return getDeployedBasePath();
}

export default function OAuthCallback() {
  const [failure, setFailure] = useState(null);
  // The authorization code is single-use: React StrictMode mounts effects
  // twice in dev, so the exchange is latched to run exactly once.
  const exchangeStarted = useRef(false);

  const { code, state, error } = readCallbackParams();
  const paramsError = error
    ? "Sign-in was cancelled or failed at the identity provider. Please try again."
    : !code || !state
      ? "Invalid sign-in response: the authorization code or state is missing."
      : null;

  useEffect(() => {
    if (paramsError || exchangeStarted.current) {
      return;
    }
    exchangeStarted.current = true;

    (async () => {
      try {
        const res = await fetch(buildApiUrl("/api/auth/gitlab/"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ code, state }),
        });

        if (!res.ok) {
          setFailure(
            "Sign-in failed. The authorization code may have expired — please try again."
          );
          return;
        }

        const data = await res.json();
        window.location.replace(safeNext(data.next));
      } catch {
        setFailure("Connection error while signing in. Please try again.");
      }
    })();
  }, []);

  const message = paramsError ?? failure;

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        {message ? (
          <>
            <h1 className={styles.title}>Sign-in failed</h1>
            <p className={styles.error}>{message}</p>
            <a className={styles.homeLink} href={getDeployedBasePath()}>
              Back to home
            </a>
          </>
        ) : (
          <>
            <h1 className={styles.title}>Signing you in…</h1>
            <Loader />
          </>
        )}
      </div>
    </div>
  );
}
