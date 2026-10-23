import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { fetchWithAuth } from "../../utils/api";
import Loader from "../ui/Loader/Loader";

export default function ProtectedRoute({ children }) {
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    let cancelled = false;

    fetchWithAuth("/api/auth/user/")
      .then((res) => {
        if (!cancelled) {
          setStatus(res.ok ? "allowed" : "denied");
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

  return children;
}
