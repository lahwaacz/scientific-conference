import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchWithAuth } from "../../utils/api";
import Loader from "../ui/Loader/Loader";
import Title from "../ui/Title/Title";
import styles from "./EditProgramInfo.module.css";

export default function EditProgramInfo() {
  const [form, setForm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchWithAuth(`/api/conference-info/`)
      .then((r) => r.json())
      .then((data) => {
        setForm(data);
        setLoading(false);
      });
  }, []);

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    setSaved(false);
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const res = await fetchWithAuth(`/api/conference-info/edit/`, {
        method: "PATCH",
        body: JSON.stringify({
          program_text: form.program_text,
        }),
      });
      if (!res.ok) throw new Error();
      setSaved(true);
    } catch {
      setError("Failed to save. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={styles.container}>
      <Link to="/admin-panel/edit-program" className={styles.backButton}>
        ← BACK
      </Link>
      <Title text="Edit Program Info" />

      {loading ? (
        <Loader />
      ) : (
        <form
          onSubmit={handleSave}
          className={`${styles.form} ${styles.fadeIn}`}
        >
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Program Page Text</h2>

            <div className={styles.field}>
              <label>Program Page Text</label>
              <small className={styles.hint}>
                Shown above the schedule; Markdown formatting is supported
              </small>
              <textarea
                name="program_text"
                rows={10}
                value={form.program_text || ""}
                onChange={handleChange}
              />
            </div>
          </section>

          {error && <p className={styles.error}>{error}</p>}

          <div className={styles.actions}>
            {saved && (
              <span className={styles.savedMsg}>✓ Saved successfully</span>
            )}
            <button
              type="submit"
              className={styles.saveButton}
              disabled={saving}
            >
              {saving ? "Saving..." : "SAVE CHANGES"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
