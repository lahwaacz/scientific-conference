import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./EditParticipants.module.css";
import Title from "../ui/Title/Title";
import avatar from "../../assets/avatar.png";
import Loader from "../ui/Loader/Loader";
import { fetchWithAuth, buildMediaUrl } from "../../utils/api";
import EditSubmissionModal from "../EditSubmissionModal/EditSubmissionModal";
import Modal from "../ui/Modal/Modal";
import { markProgramDirty } from "../../utils/programRefresh";

export default function EditParticipants() {
  const [submissions, setSubmissions] = useState([]);
  const [filter, setFilter] = useState("pending");
  const [loading, setLoading] = useState(true);
  const [editingSubmission, setEditingSubmission] = useState(null);
  const navigate = useNavigate();

  const [modal, setModal] = useState({
    isOpen: false,
    title: "",
    message: "",
    onConfirm: null,
    type: "default",
  });

  function openModal(config) {
    setModal({ isOpen: true, ...config });
  }
  function closeModal() {
    setModal((prev) => ({ ...prev, isOpen: false }));
  }

  useEffect(() => {
    fetchSubmissions();
  }, [filter]);
  async function fetchSubmissions() {
    setLoading(true);
    try {
      const res = await fetchWithAuth(
        `/api/admin/submissions/?status=${filter}`
      );

      if (res.ok) {
        const data = await res.json();
        setSubmissions(data);
      } else {
        const errorText = await res.text();
        openModal({
          title: "Load failed",
          message: errorText || "Failed to load submissions.",
          type: "danger",
          onConfirm: closeModal,
        });
      }
    } catch (error) {
      openModal({
        title: "Connection error",
        message: error.message || "Server is unreachable.",
        type: "danger",
        onConfirm: closeModal,
      });
    } finally {
      setLoading(false);
    }
  }

  async function publishSubmission(id) {
    try {
      const res = await fetchWithAuth(`/api/admin/submissions/${id}/publish/`, {
        method: "POST",
      });
      if (res.ok) {
        openModal({
          title: "Success",
          message: "Published successfully!",
          type: "success",
          onConfirm: closeModal,
        });
        fetchSubmissions();
      } else {
        const error = await res.json();
        openModal({
          title: "Error",
          message: error.error || "Unknown error",
          type: "danger",
          onConfirm: closeModal,
        });
      }
    } catch {
      openModal({
        title: "Connection error",
        message: "Server is unreachable.",
        type: "danger",
        onConfirm: closeModal,
      });
    }
  }

  function confirmPublish(id) {
    openModal({
      title: "Publish submission",
      message: "This will create a Participant and Abstract entry.",
      type: "default",
      onConfirm: async () => {
        closeModal();
        await publishSubmission(id);
      },
    });
  }

  async function deleteSubmission(id) {
    const submission = submissions.find((s) => s.id === id);
    const isApproved = submission?.status === "approved";
    try {
      const res = await fetchWithAuth(`/api/admin/submissions/${id}/`, {
        method: "DELETE",
      });

      if (res.ok || res.status === 204) {
        markProgramDirty();
        openModal({
          title: "Success",
          message: isApproved
            ? "Deleted successfully\n\nThe Participant and Abstract have been removed from the public site."
            : "Deleted successfully",
          onConfirm: closeModal,
        });
        fetchSubmissions();
      } else {
        const errorText = await res.text();
        openModal({
          title: "Delete failed",
          message: errorText,
          onConfirm: closeModal,
        });
      }
    } catch (error) {
      openModal({
        title: "Connection error",
        message: error.message,
        onConfirm: closeModal,
      });
    }
  }

  function confirmDelete(id, isApproved) {
    openModal({
      title: "Delete submission",
      message: isApproved
        ? "WARNING: This will also remove the published Participant and Abstract from the public site!"
        : "Delete this submission permanently? This cannot be undone.",
      onConfirm: async () => {
        closeModal();
        await deleteSubmission(id, isApproved);
      },
    });
  }

  function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  }

  function getStatusDisplay(status) {
    if (status === "approved") return "published";
    return status;
  }

  function getPhotoUrl(photoPath) {
    return buildMediaUrl(photoPath);
  }

  function handleSaveSubmission(updatedSubmission) {
    markProgramDirty();
    setSubmissions((prev) =>
      prev.map((sub) =>
        sub.id === updatedSubmission.id ? updatedSubmission : sub
      )
    );
  }

  const filterButtons = (
    <div className={styles.filterButtons}>
      <button
        className={filter === "pending" ? styles.active : ""}
        onClick={() => setFilter("pending")}
      >
        Pending
      </button>
      <button
        className={filter === "approved" ? styles.active : ""}
        onClick={() => setFilter("approved")}
      >
        Published
      </button>
      <button
        className={filter === "" ? styles.active : ""}
        onClick={() => setFilter("")}
      >
        All
      </button>
    </div>
  );

  return (
    <div className={styles.container}>
      <button
        onClick={() => navigate("/admin-panel")}
        className={styles.backBtn}
      >
        ← Back
      </button>
      <Title text="Participant Submissions" />
      {filterButtons}

      {loading ? (
        <Loader />
      ) : (
        <div className={styles.fadeIn}>
          {submissions.length === 0 ? (
            <div className={styles.noDataContainer}>
              <p className={styles.noData}>No submissions found</p>
            </div>
          ) : (
            <div className={styles.submissionsGrid}>
              {submissions.map((sub) => (
                <div key={sub.id} className={styles.submissionCard}>
                  <div className={styles.cardHeader}>
                    <div className={styles.headerLeft}>
                      <img
                        src={sub.photo ? getPhotoUrl(sub.photo) : avatar}
                        alt={sub.name}
                        className={styles.participantPhoto}
                        onError={(e) => {
                          e.target.src = avatar;
                        }}
                      />
                      <div>
                        <h3>{sub.name}</h3>
                        <p className={styles.email}>{sub.email}</p>
                      </div>
                    </div>
                    <span className={`${styles.badge} ${styles[sub.status]}`}>
                      {getStatusDisplay(sub.status)}
                    </span>
                  </div>

                  <div className={styles.cardBody}>
                    <div className={styles.infoRow}>
                      <strong>Affiliation:</strong>
                      <span>{sub.affiliation}</span>
                    </div>
                    <div className={styles.infoRow}>
                      <strong>Abstract Title:</strong>
                      <span
                        className={!sub.abstract_title ? styles.emptyValue : ""}
                      >
                        {sub.abstract_title || "—"}
                      </span>
                    </div>
                    <div className={styles.abstractSection}>
                      <strong>Abstract:</strong>
                      {sub.abstract_text ? (
                        <p className={styles.abstractText}>
                          {sub.abstract_text.length > 200
                            ? sub.abstract_text.substring(0, 200) + "..."
                            : sub.abstract_text}
                        </p>
                      ) : (
                        <p
                          className={`${styles.abstractText} ${styles.emptyValue}`}
                        >
                          —
                        </p>
                      )}
                    </div>
                    {sub.additional_authors && (
                      <div className={styles.infoRow}>
                        <strong>Co-authors:</strong>
                        <span>{sub.additional_authors}</span>
                      </div>
                    )}
                  </div>

                  <div className={styles.cardFooter}>
                    <div className={styles.datesSection}>
                      <div className={styles.dateInfo}>
                        <strong>Arrival:</strong>
                        <span>{formatDate(sub.arrival_date)}</span>
                      </div>
                      <div className={styles.dateInfo}>
                        <strong>Departure:</strong>
                        <span>{formatDate(sub.departure_date)}</span>
                      </div>
                      <div className={styles.dateInfo}>
                        <strong>Stay:</strong>
                        <span>{sub.stay_duration} days</span>
                      </div>
                    </div>
                    <div className={styles.metadata}>
                      <small>Submitted: {formatDate(sub.submitted_at)}</small>
                    </div>
                    <div className={styles.cardActions}>
                      {sub.status === "pending" && (
                        <button
                          className={styles.publishBtn}
                          onClick={() => confirmPublish(sub.id)}
                        >
                          Publish
                        </button>
                      )}
                      <button
                        className={styles.editBtn}
                        onClick={() => setEditingSubmission(sub)}
                      >
                        Edit
                      </button>
                      <button
                        className={styles.deleteBtn}
                        onClick={() =>
                          confirmDelete(sub.id, sub.status === "approved")
                        }
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {editingSubmission && (
        <EditSubmissionModal
          submission={editingSubmission}
          onClose={() => setEditingSubmission(null)}
          onSave={handleSaveSubmission}
        />
      )}
      <Modal
        isOpen={modal.isOpen}
        title={modal.title}
        message={modal.message}
        onConfirm={modal.onConfirm}
        onCancel={closeModal}
      />
    </div>
  );
}
