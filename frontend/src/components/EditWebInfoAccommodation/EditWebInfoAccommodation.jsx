import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { buildMediaUrl, fetchWithAuth } from "../../utils/api";
import Loader from "../ui/Loader/Loader";
import Modal from "../ui/Modal/Modal";
import Title from "../ui/Title/Title";
import styles from "./EditWebInfoAccommodation.module.css";

export default function EditWebInfoAccommodation() {
  const [description, setDescription] = useState("");
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingInfo, setSavingInfo] = useState(false);
  const [savingOptions, setSavingOptions] = useState(false);
  const [savedInfo, setSavedInfo] = useState(false);
  const [savedOptions, setSavedOptions] = useState(false);
  const [error] = useState("");

  const [modal, setModal] = useState({
    isOpen: false,
    title: "",
    message: "",
    onConfirm: null,
    type: "default",
  });

  function openModal(config) {
    setModal({
      isOpen: true,
      ...config,
    });
  }

  function closeModal() {
    setModal((prev) => ({ ...prev, isOpen: false }));
  }

  useEffect(() => {
    fetchWithAuth(`/api/accommodation/`)
      .then((r) => r.json())
      .then((data) => {
        setDescription(data.description || "");
        setOptions(data.options || []);
        setLoading(false);
      });
  }, []);

  async function handleSaveInfo(e) {
    e.preventDefault();
    setSavingInfo(true);

    try {
      const res = await fetchWithAuth("/api/admin/accommodation/", {
        method: "PATCH",
        body: JSON.stringify({ description }),
      });

      if (!res.ok) {
        const errorText = await res.text();
        openModal({
          title: "Save failed",
          message: errorText || "Failed to save description.",
          type: "danger",
          onConfirm: closeModal,
        });
        return;
      }

      setSavedInfo(true);
      openModal({
        title: "Success",
        message: "Description saved successfully.",
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
      setSavingInfo(false);
    }
  }

  function handleOptionChange(index, field, value) {
    const updated = [...options];
    updated[index] = { ...updated[index], [field]: value };
    setOptions(updated);
    setSavedOptions(false);
  }

  function handleOptionPhoto(index, file) {
    const updated = [...options];
    updated[index] = {
      ...updated[index],
      _photoFile: file,
      _photoPreview: URL.createObjectURL(file),
    };
    setOptions(updated);
  }

  function addOption() {
    setOptions([
      ...options,
      {
        name: "",
        description: "",
        url: "",
        photo: null,
        order: options.length,
      },
    ]);
  }

  async function deleteOption(id, index) {
    try {
      if (id) {
        const res = await fetchWithAuth(
          `/api/admin/accommodation/options/${id}/`,
          {
            method: "DELETE",
          }
        );

        if (!res.ok && res.status !== 204) {
          const errorText = await res.text();
          openModal({
            title: "Delete failed",
            message: errorText || "Failed to delete option.",
            type: "danger",
            onConfirm: closeModal,
          });
          return;
        }
      }

      setOptions((prev) => prev.filter((_, i) => i !== index));

      openModal({
        title: "Success",
        message: "Option deleted successfully.",
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
    }
  }
  function confirmDeleteOption(id, index) {
    openModal({
      title: "Delete option",
      message: "Delete this option permanently?",
      type: "danger",
      onConfirm: async () => {
        closeModal();
        await deleteOption(id, index);
      },
    });
  }

  async function saveOption(option) {
    const fd = new FormData();
    fd.append("name", option.name || "");
    fd.append("description", option.description || "");
    fd.append("url", option.url || "");
    fd.append("order", option.order ?? 0);
    if (option._photoFile) fd.append("photo", option._photoFile);

    if (option.id) {
      return fetchWithAuth(`/api/admin/accommodation/options/${option.id}/`, {
        method: "PATCH",
        body: fd,
      });
    } else {
      return fetchWithAuth(`/api/admin/accommodation/options/`, {
        method: "POST",
        body: fd,
      });
    }
  }

  async function handleSaveOptions() {
    setSavingOptions(true);

    try {
      const results = await Promise.all(options.map((o) => saveOption(o)));

      for (const res of results) {
        if (!res.ok) {
          const errorText = await res.text();
          openModal({
            title: "Save failed",
            message: errorText || "Failed to save options.",
            type: "danger",
            onConfirm: closeModal,
          });
          return;
        }
      }

      const updated = await Promise.all(results.map((r) => r.json()));
      setOptions(updated);
      setSavedOptions(true);

      openModal({
        title: "Success",
        message: "Accommodation options saved successfully.",
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
      setSavingOptions(false);
    }
  }

  return (
    <div className={styles.container}>
      <Link to="/admin-panel/edit-web-info" className={styles.backButton}>
        ← BACK
      </Link>
      <Title text="Edit Accommodation" />

      {loading ? (
        <Loader />
      ) : (
        <div className={styles.fadeIn}>
          {/* ── Description ── */}
          <form onSubmit={handleSaveInfo} className={styles.form}>
            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>General Description</h2>
              <div className={styles.field}>
                <label>Text shown at the top of the Accommodation page</label>
                <textarea
                  rows={5}
                  value={description}
                  onChange={(e) => {
                    setDescription(e.target.value);
                    setSavedInfo(false);
                  }}
                />
              </div>
            </section>

            {error && <p className={styles.error}>{error}</p>}

            <div className={styles.actions}>
              {savedInfo && <span className={styles.savedMsg}>✓ Saved</span>}
              <button
                type="submit"
                className={styles.saveButton}
                disabled={savingInfo}
              >
                {savingInfo ? "Saving..." : "SAVE DESCRIPTION"}
              </button>
            </div>
          </form>

          {/* ── Options ── */}
          <section className={styles.section} style={{ marginTop: 40 }}>
            <h2 className={styles.sectionTitle}>Accommodation Options</h2>

            {options.length === 0 && (
              <p className={styles.emptyMsg}>No options added yet.</p>
            )}

            {options.map((option, i) => (
              <div key={option.id ?? `new-${i}`} className={styles.optionRow}>
                <div className={styles.photoCol}>
                  {option._photoPreview ? (
                    <img
                      src={option._photoPreview}
                      alt="preview"
                      className={styles.optionPhoto}
                    />
                  ) : option.photo ? (
                    <img
                      src={buildMediaUrl(option.photo)}
                      alt={option.name}
                      className={styles.optionPhoto}
                    />
                  ) : (
                    <div className={styles.photoPlaceholder} />
                  )}
                  <label className={styles.photoLabel}>
                    Change photo
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => handleOptionPhoto(i, e.target.files[0])}
                      className={styles.fileInputHidden}
                    />
                  </label>
                </div>

                <div className={styles.optionFields}>
                  <div className={styles.row}>
                    <div className={styles.field}>
                      <label>Name</label>
                      <input
                        value={option.name || ""}
                        onChange={(e) =>
                          handleOptionChange(i, "name", e.target.value)
                        }
                      />
                    </div>
                    <div className={styles.field}>
                      <label>Order</label>
                      <input
                        type="number"
                        value={option.order ?? i}
                        onChange={(e) =>
                          handleOptionChange(i, "order", e.target.value)
                        }
                        style={{ maxWidth: 80 }}
                      />
                    </div>
                  </div>

                  <div className={styles.field}>
                    <label>Description</label>
                    <textarea
                      rows={2}
                      value={option.description || ""}
                      onChange={(e) =>
                        handleOptionChange(i, "description", e.target.value)
                      }
                    />
                  </div>

                  <div className={styles.field}>
                    <label>Website URL</label>
                    <input
                      type="url"
                      value={option.url || ""}
                      onChange={(e) =>
                        handleOptionChange(i, "url", e.target.value)
                      }
                      placeholder="https://..."
                    />
                  </div>
                </div>

                <button
                  type="button"
                  className={styles.deleteButton}
                  onClick={() => confirmDeleteOption(option.id, i)}
                >
                  ✕
                </button>
              </div>
            ))}

            <div className={styles.personActions}>
              <button
                type="button"
                className={styles.addButton}
                onClick={addOption}
              >
                + ADD OPTION
              </button>
              <div className={styles.saveRow}>
                {savedOptions && (
                  <span className={styles.savedMsg}>✓ Saved</span>
                )}
                <button
                  type="button"
                  className={styles.saveButton}
                  onClick={handleSaveOptions}
                  disabled={savingOptions}
                >
                  {savingOptions ? "Saving..." : "SAVE OPTIONS"}
                </button>
              </div>
            </div>
            <Modal
              isOpen={modal.isOpen}
              title={modal.title}
              message={modal.message}
              type={modal.type}
              onConfirm={modal.onConfirm}
              onCancel={closeModal}
            />
          </section>
        </div>
      )}
    </div>
  );
}
