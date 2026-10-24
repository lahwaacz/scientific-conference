import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { canManageConference } from "../../utils/access";
import { fetchWithAuth } from "../../utils/api";
import { getConferenceSlug } from "../../utils/conferenceSlug";
import Loader from "../ui/Loader/Loader";
import styles from "./ProtectedRoute.module.css";

export default function ProtectedRoute({ children }) {
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    let cancelled = false;

    fetchWithAuth("/api/auth/user/")
      .then(async (res) => {
        if (!res.ok) {
          return "denied";
        }
        const user = await res.json();
        return canManageConference(user, getConferenceSlug())
          ? "allowed"
          : "forbidden";
      })
      .then((next) => {
        if (!cancelled) {
          setStatus(next);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStatus("denied");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (status === "checking") {
    return <Loader />;
  }

  if (status === "denied") {
    return <Navigate to="/" replace />;
  }

  if (status === "forbidden") {
    return (
      <div className={styles.noAccess}>
        <p>You do not have access to this conference.</p>
        <Link to="/">Back to the conference home</Link>
      </div>
    );
  }

  return children;
}
