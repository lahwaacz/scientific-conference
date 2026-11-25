import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { buildMediaUrl, fetchWithAuth } from "../../utils/api";
import Loader from "../ui/Loader/Loader";
import Modal from "../ui/Modal/Modal";
import Title from "../ui/Title/Title";
import styles from "./EditWebInfoSponsors.module.css";

function revokePreview(url) {
  if (url && typeof URL.revokeObjectURL === "function") {
    URL.revokeObjectURL(url);
  }
}

export default function EditWebInfoSponsors() {
  const [sponsors, setSponsors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [saved, setSaved] = useState(false);
  const sponsorsRef = useRef(sponsors);
  const busy = saving || deleting;
  const [modal, setModal] = useState({
    isOpen: false,
    title: "",
    message: "",
    onConfirm: null,
    onCancel: null,
    type: "default",
  });

  function openModal(config) {
    setModal({
      isOpen: true,
      onCancel: null,
      ...config,
    });
  }

  function closeModal() {
    setModal((prev) => ({ ...prev, isOpen: false }));
  }

  useEffect(() => {
    sponsorsRef.current = sponsors;
  }, [sponsors]);

  useEffect(() => {
    return () => {
      for (const sponsor of sponsorsRef.current) {
        revokePreview(sponsor._logoPreview);
      }
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    fetchWithAuth("/api/sponsors/")
      .then(async (res) => {
        if (!res.ok) {
          const errorText = await res.text();
          throw new Error(errorText || "Failed to load sponsors.");
        }
        return res.json();
      })
      .then((data) => {
        if (cancelled) return;
        setSponsors(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch((error) => {
        if (cancelled) return;
        setLoading(false);
        openModal({
          title: "Connection error",
          message: error.message || "Server is unreachable.",
          type: "danger",
          onConfirm: closeModal,
        });
      });

    return () => {
      cancelled = true;
    };
  }, []);

  function handleSponsorChange(index, field, value) {
    if (busy) return;

    const updated = [...sponsors];
    updated[index] = { ...updated[index], [field]: value };
    setSponsors(updated);
    setSaved(false);
  }

  function handleSponsorLogo(index, file) {
    if (!file || busy) return;

    const updated = [...sponsors];
    revokePreview(updated[index]._logoPreview);
    updated[index] = {
      ...updated[index],
      _logoFile: file,
      _logoPreview: URL.createObjectURL(file),
    };
    setSponsors(updated);
    setSaved(false);
  }

  function addSponsor() {
    if (busy) return;

    setSponsors([
      ...sponsors,
      {
        name: "",
        url: "",
        logo: null,
        order: sponsors.length,
      },
    ]);
    setSaved(false);
  }

  async function deleteSponsor(id, index) {
    if (busy) return;
    setDeleting(true);

    try {
      if (id) {
        const res = await fetchWithAuth(`/api/admin/sponsors/${id}/`, {
          method: "DELETE",
        });

        if (!res.ok && res.status !== 204) {
          const errorText = await res.text();
          openModal({
            title: "Delete failed",
            message: errorText || "Failed to delete sponsor.",
            type: "danger",
            onConfirm: closeModal,
          });
          return;
        }
      }

      revokePreview(sponsors[index]?._logoPreview);
      setSponsors((prev) =>
        prev.filter((sponsor, i) => (id ? sponsor.id !== id : i !== index))
      );
      setSaved(false);
      openModal({
        title: "Success",
        message: "Sponsor deleted successfully.",
        type: "success",
        onConfirm: closeModal,
      });
    } catch (error) {
      openModal({
        title: "Connection error",
        message: error.message || "Server is unreachable.",
        type: "danger",
        onConfirm: closeModal,
      });
    } finally {
      setDeleting(false);
    }
  }

  function confirmDeleteSponsor(id, index) {
    if (busy) return;

    openModal({
      title: "Delete sponsor",
      message: "Delete this sponsor permanently?",
      type: "danger",
      onCancel: closeModal,
      onConfirm: async () => {
        closeModal();
        await deleteSponsor(id, index);
      },
    });
  }

  async function saveSponsor(sponsor) {
    const parsedOrder = Number.parseInt(sponsor.order, 10);
    const order = Number.isNaN(parsedOrder) ? 0 : parsedOrder;
    const fd = new FormData();
    fd.append("name", sponsor.name || "");
    fd.append("url", sponsor.url || "");
    fd.append("order", order);
    if (sponsor._logoFile) fd.append("logo", sponsor._logoFile);

    if (sponsor.id) {
      return fetchWithAuth(`/api/admin/sponsors/${sponsor.id}/`, {
        method: "PATCH",
        body: fd,
      });
    }

    return fetchWithAuth("/api/admin/sponsors/", {
      method: "POST",
      body: fd,
    });
  }

  async function handleSaveSponsors() {
    if (busy) return;
    setSaving(true);
    setSaved(false);

    try {
      const results = await Promise.allSettled(
        sponsors.map((sponsor) => saveSponsor(sponsor))
      );
      const updated = [];
      const errors = [];

      for (let index = 0; index < results.length; index += 1) {
        const sponsor = sponsors[index];
        const result = results[index];

        if (result.status === "rejected") {
          errors.push(result.reason?.message || "Server is unreachable.");
          updated.push(sponsor);
          continue;
        }

        const res = result.value;
        if (!res.ok) {
          errors.push(await res.text().catch(() => ""));
          updated.push(sponsor);
          continue;
        }

        try {
          updated.push(await res.json());
          revokePreview(sponsor._logoPreview);
        } catch {
          errors.push("Failed to read the server response.");
          updated.push(sponsor);
        }
      }

      setSponsors(updated);

      if (errors.length > 0) {
        openModal({
          title: "Save failed",
          message: errors[0] || "Failed to save sponsors.",
          type: "danger",
          onConfirm: closeModal,
        });
        return;
      }

      setSaved(true);
      openModal({
        title: "Success",
        message: "Sponsors saved successfully.",
        type: "success",
        onConfirm: closeModal,
      });
    } catch (error) {
      openModal({
        title: "Connection error",
        message: error.message || "Server is unreachable.",
        type: "danger",
        onConfirm: closeModal,
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={styles.container}>
      <Link to="/admin-panel/edit-web-info" className={styles.backButton}>
        ← BACK
      </Link>
      <Title text="Edit Sponsors" />

      {loading ? (
        <Loader />
      ) : (
        <div className={styles.fadeIn}>
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Sponsors</h2>

            {sponsors.length === 0 && (
              <p className={styles.emptyMsg}>No sponsors added yet.</p>
            )}

            {sponsors.map((sponsor, i) => {
              const rowKey = sponsor.id ?? `new-${i}`;

              return (
                <div key={rowKey} className={styles.sponsorRow}>
                  <div className={styles.logoCol}>
                    {sponsor._logoPreview ? (
                      <img
                        src={sponsor._logoPreview}
                        alt="Logo preview"
                        className={styles.sponsorLogo}
                      />
                    ) : sponsor.logo ? (
                      <img
                        src={buildMediaUrl(sponsor.logo)}
                        alt={sponsor.name || "Sponsor logo"}
                        className={styles.sponsorLogo}
                      />
                    ) : (
                      <div
                        className={styles.logoPlaceholder}
                        aria-hidden="true"
                      />
                    )}
                    <label className={styles.logoLabel}>
                      Change logo
                      <input
                        type="file"
                        accept="image/*,.svg"
                        onChange={(e) =>
                          handleSponsorLogo(i, e.target.files[0])
                        }
                        className={styles.fileInputHidden}
                        disabled={busy}
                      />
                    </label>
                  </div>

                  <div className={styles.sponsorFields}>
                    <div className={styles.row}>
                      <div className={styles.field}>
                        <label htmlFor={`sponsor-name-${rowKey}`}>Name</label>
                        <input
                          id={`sponsor-name-${rowKey}`}
                          value={sponsor.name || ""}
                          onChange={(e) =>
                            handleSponsorChange(i, "name", e.target.value)
                          }
                          disabled={busy}
                        />
                      </div>
                      <div className={`${styles.field} ${styles.orderField}`}>
                        <label htmlFor={`sponsor-order-${rowKey}`}>Order</label>
                        <input
                          id={`sponsor-order-${rowKey}`}
                          type="number"
                          min={0}
                          step={1}
                          value={sponsor.order ?? i}
                          onChange={(e) =>
                            handleSponsorChange(i, "order", e.target.value)
                          }
                          style={{ maxWidth: 80 }}
                          disabled={busy}
                        />
                      </div>
                    </div>

                    <div className={styles.field}>
                      <label htmlFor={`sponsor-url-${rowKey}`}>
                        Website URL
                      </label>
                      <input
                        id={`sponsor-url-${rowKey}`}
                        type="url"
                        value={sponsor.url || ""}
                        onChange={(e) =>
                          handleSponsorChange(i, "url", e.target.value)
                        }
                        placeholder="https://..."
                        disabled={busy}
                      />
                    </div>
                  </div>

                  <button
                    type="button"
                    className={styles.deleteButton}
                    aria-label={`Delete ${sponsor.name || `sponsor ${i + 1}`}`}
                    onClick={() => confirmDeleteSponsor(sponsor.id, i)}
                    disabled={busy}
                  >
                    ✕
                  </button>
                </div>
              );
            })}

            <div className={styles.sponsorActions}>
              <button
                type="button"
                className={styles.addButton}
                onClick={addSponsor}
                disabled={busy}
              >
                + ADD SPONSOR
              </button>
              <div className={styles.saveRow}>
                {saved && <span className={styles.savedMsg}>✓ Saved</span>}
                <button
                  type="button"
                  className={styles.saveButton}
                  onClick={handleSaveSponsors}
                  disabled={busy}
                >
                  {saving ? "Saving..." : "SAVE SPONSORS"}
                </button>
              </div>
            </div>
            <Modal
              isOpen={modal.isOpen}
              title={modal.title}
              message={modal.message}
              type={modal.type}
              onConfirm={modal.onConfirm}
              onCancel={modal.onCancel}
            />
          </section>
        </div>
      )}
    </div>
  );
}
