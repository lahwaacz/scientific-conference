import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchWithAuth } from "../../utils/api";
import Loader from "../ui/Loader/Loader";
import Title from "../ui/Title/Title";
import styles from "./EditWebInfoRegistration.module.css";

export default function EditWebInfoRegistration() {
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
          registration_fee_note: form.registration_fee_note,
          registration_instructions: form.registration_instructions,
          registration_deadline: form.registration_deadline,
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
      <Link to="/admin-panel/edit-web-info" className={styles.backButton}>
        ← BACK
      </Link>
      <Title text="Edit Registration" />

      {loading ? (
        <Loader />
      ) : (
        <form
          onSubmit={handleSave}
          className={`${styles.form} ${styles.fadeIn}`}
        >
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Registration Page Texts</h2>

            <div className={styles.field}>
              <label>Fee Note</label>
              <small className={styles.hint}>
                Shown at the top of the registration page and form
              </small>
              <input
                name="registration_fee_note"
                value={form.registration_fee_note || ""}
                onChange={handleChange}
              />
            </div>

            <div className={styles.field}>
              <label>
                Required Registration Data
                <span className={styles.hintInline}>
                  {" "}
                  (one item per line — shown as numbered list)
                </span>
              </label>
              <textarea
                name="registration_instructions"
                rows={7}
                value={form.registration_instructions || ""}
                onChange={handleChange}
                placeholder={
                  "Name\nYour contact address and e-mail\nAffiliation\nThe abstract of your contribution\nArrival and departure dates"
                }
              />
            </div>

            <div className={styles.field}>
              <label>Registration Deadline</label>
              <small className={styles.hint}>
                Shown as "Please submit your registration until [date]"
              </small>
              <input
                name="registration_deadline"
                type="date"
                value={form.registration_deadline || ""}
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
