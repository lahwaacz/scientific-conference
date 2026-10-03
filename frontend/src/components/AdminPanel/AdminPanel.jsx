import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import styles from "./AdminPanel.module.css";
import Loader from "../ui/Loader/Loader";
import Title from "../ui/Title/Title";
import Modal from "../ui/Modal/Modal";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { fetchWithAuth } from "../../utils/api";
import { fas } from "@fortawesome/free-solid-svg-icons";
import { far } from "@fortawesome/free-regular-svg-icons";
import { fab } from "@fortawesome/free-brands-svg-icons";

export default function AdminPanel() {
  library.add(fas, far, fab);

  const [, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState({
    isOpen: false,
    title: "",
    message: "",
    onConfirm: null,
    type: "default",
  });

  const navigate = useNavigate();

  function openModal(config) {
    setModal({
      isOpen: true,
      ...config,
    });
  }

  function closeModal() {
    setModal((prev) => ({ ...prev, isOpen: false }));
  }

  async function handleDownloadProgram() {
    try {
      const res = await fetchWithAuth("/api/admin/program/download/");

      if (!res.ok) {
        const errorText = await res.text();
        openModal({
          title: "Download failed",
          message: errorText || "Failed to download program PDF.",
          type: "danger",
          onConfirm: closeModal,
        });
        return;
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "program.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      openModal({
        title: "Connection error",
        message: error.message || "Server is unreachable.",
        type: "danger",
        onConfirm: closeModal,
      });
    }
  }

  async function handleDownloadBadges() {
    try {
      const res = await fetchWithAuth("/api/admin/badges/download/");

      if (!res.ok) {
        const errorText = await res.text();
        openModal({
          title: "Download failed",
          message: errorText || "Failed to generate badges.",
          type: "danger",
          onConfirm: closeModal,
        });
        return;
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "badges.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      openModal({
        title: "Connection error",
        message: error.message || "Server is unreachable.",
        type: "danger",
        onConfirm: closeModal,
      });
    }
  }

  useEffect(() => {
    async function fetchAdminData() {
      try {
        const res = await fetchWithAuth("/api/admin-panel/");

        if (!res.ok) {
          setError("Access denied");
          return;
        }

        const responseData = await res.json();
        setData(responseData);
      } catch {
        setError("Connection error");
      } finally {
        setLoading(false);
      }
    }

    fetchAdminData();
  }, []);

  function handleLogout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    navigate("/");
  }

  if (error) {
    return (
      <div className={styles.container}>
        <Title text={error} />
        <p className={styles.redirecting}>Unable to load admin panel.</p>
        <button className={styles.logoutButton} onClick={() => navigate("/")}>
          Back to home
        </button>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <Title text="Admin Panel" />

      {loading ? (
        <Loader />
      ) : (
        <div className={styles.fadeIn}>
          <div className={styles.buttonGrid}>
            <Link
              to="/admin-panel/participants-info"
              className={styles.adminButton}
            >
              <span className={styles.iconWrapper}>
                <FontAwesomeIcon
                  icon="fa-solid fa-user-group"
                  className={styles.adminIcon}
                />
              </span>
              <h3 className={styles.buttonTitle}>Participants Info</h3>
              <p className={styles.description}>View all participants</p>
            </Link>

            <Link
              to="/admin-panel/edit-participants"
              className={styles.adminButton}
            >
              <span className={styles.iconWrapper}>
                <FontAwesomeIcon
                  icon="fa-solid fa-user-gear"
                  className={styles.adminIcon}
                />
              </span>
              <h3 className={styles.buttonTitle}>
                Edit Participants and Abstracts
              </h3>
              <p className={styles.description}>
                Add, edit or remove participants and their abstracts
              </p>
            </Link>

            <button
              onClick={handleDownloadBadges}
              className={styles.adminButton}
            >
              <span className={styles.iconWrapper}>
                <FontAwesomeIcon
                  icon="fa-solid fa-newspaper"
                  className={styles.adminIcon}
                />
              </span>
              <h3 className={styles.buttonTitle}>Download Badges</h3>
              <p className={styles.description}>
                Generate and download participant badges
              </p>
            </button>

            <Link to="/admin-panel/edit-program" className={styles.adminButton}>
              <span className={styles.iconWrapper}>
                <FontAwesomeIcon
                  icon="fa-solid fa-calendar"
                  className={styles.adminIcon}
                />
              </span>
              <h3 className={styles.buttonTitle}>Edit Program</h3>
              <p className={styles.description}>Manage conference schedule</p>
            </Link>

            <Link
              to="/admin-panel/edit-web-info"
              className={styles.adminButton}
            >
              <span className={styles.iconWrapper}>
                <FontAwesomeIcon
                  icon="fa-solid fa-globe"
                  className={styles.adminIcon}
                />
              </span>
              <h3 className={styles.buttonTitle}>Edit Web Info</h3>
              <p className={styles.description}>Update website content</p>
            </Link>

            <button
              onClick={handleDownloadProgram}
              className={styles.adminButton}
            >
              <span className={styles.iconWrapper}>
                <FontAwesomeIcon
                  icon="fa-solid fa-download"
                  className={styles.adminIcon}
                />
              </span>
              <h3 className={styles.buttonTitle}>Download Program PDF</h3>
              <p className={styles.description}>Export conference program</p>
            </button>
          </div>

          <button className={styles.logoutButton} onClick={handleLogout}>
            Logout
          </button>
        </div>
      )}

      <Modal
        isOpen={modal.isOpen}
        title={modal.title}
        message={modal.message}
        type={modal.type}
        onConfirm={modal.onConfirm}
        onCancel={closeModal}
      />
    </div>
  );
}
