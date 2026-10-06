import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { buildMediaUrl, fetchWithAuth } from "../../utils/api";
import Loader from "../ui/Loader/Loader";
import Title from "../ui/Title/Title";
import styles from "./EditWebInfoHome.module.css";

export default function EditWebInfoHome() {
  const [form, setForm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [organizers, setOrganizers] = useState([]);
  const [committee, setCommittee] = useState([]);
  const [personSaved, setPersonSaved] = useState("");
  const [personError, setPersonError] = useState("");
  const [cardPhotoFile, setCardPhotoFile] = useState(null);
  const [heroPhoto, setHeroPhoto] = useState(null);
  const [heroPhotoFile, setHeroPhotoFile] = useState(null);

  useEffect(() => {
    Promise.all([
      fetchWithAuth(`/api/conference-info/`).then((r) => r.json()),
      fetchWithAuth(`/api/organizers/`).then((r) => r.json()),
      fetchWithAuth(`/api/committees/`).then((r) => r.json()),
    ]).then(([info, orgs, comm]) => {
      // `year` is derived from date_start on the backend and the
      // photos are only replaced via the file inputs, so none of them
      // belongs in form state or the PATCH body.
      const { year, card_photo, hero_photo, venue_photo, ...formInfo } = info;
      setHeroPhoto(hero_photo || null);
      setForm({
        title: "",
        location: "",
        date_start: "",
        date_end: "",
        short_description: "",
        badge_title: "",
        ...formInfo,
      });
      setOrganizers(orgs);
      setCommittee(comm);
      setLoading(false);
    });
  }, []);

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    setSaved(false);
  }

  function handleCardPhotoChange(e) {
    setCardPhotoFile(e.target.files[0]);
    setSaved(false);
  }

  function handleHeroPhotoChange(e) {
    setHeroPhotoFile(e.target.files[0]);
    setSaved(false);
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const fd = new FormData();
      for (const [key, value] of Object.entries(form)) {
        fd.append(key, value ?? "");
      }
      // Absent key = keep the existing photo (card and hero alike).
      if (cardPhotoFile) fd.append("card_photo", cardPhotoFile);
      if (heroPhotoFile) fd.append("hero_photo", heroPhotoFile);

      const res = await fetchWithAuth(`/api/conference-info/edit/`, {
        method: "PATCH",
        body: fd,
      });
      if (!res.ok) throw new Error();
      setSaved(true);
    } catch {
      setError("Failed to save. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  function handlePersonChange(list, setList, index, field, value) {
    const updated = [...list];
    updated[index] = { ...updated[index], [field]: value };
    setList(updated);
  }

  function handlePersonPhoto(list, setList, index, file) {
    const updated = [...list];
    updated[index] = { ...updated[index], _photoFile: file };
    setList(updated);
  }

  async function savePerson(endpoint, person) {
    const fd = new FormData();
    fd.append("name", person.name || "");
    fd.append("department", person.department || "");
    fd.append("email", person.email || "");
    if (person._photoFile) fd.append("photo", person._photoFile);

    const url = person.id
      ? `/api/${endpoint}/${person.id}/`
      : `/api/${endpoint}/`;

    const method = person.id ? "PATCH" : "POST";

    const res = await fetchWithAuth(url, { method, body: fd });

    const text = await res.text();

    if (!res.ok) {
      throw new Error(text || `Request failed with ${res.status}`);
    }

    return text ? JSON.parse(text) : person;
  }

  async function deletePerson(endpoint, id, list, setList) {
    //if (!window.confirm('Delete this person?')) return;
    if (id) {
      await fetchWithAuth(`/api/${endpoint}/${id}/`, { method: "DELETE" });
    }
    setList(list.filter((p) => p.id !== id));
  }

  function addPerson(list, setList) {
    setList([...list, { name: "", department: "", email: "", photo: null }]);
  }

  async function saveAllPersons(endpoint, list, setList) {
    setSaving(true);
    setPersonError("");
    setPersonSaved("");

    try {
      const updated = await Promise.all(
        list.map((p) => savePerson(endpoint, p))
      );
      //const updated = await Promise.all(results.map(r => r.json()));
      setList(updated);
      setPersonSaved(endpoint);
    } catch {
      setPersonError("Failed to save. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={styles.container}>
      <Link to="/admin-panel/edit-web-info" className={styles.backButton}>
        ← BACK
      </Link>
      <Title text="Edit Home" />

      {loading ? (
        <Loader />
      ) : (
        <div className={styles.fadeIn}>
          {/* Conference Info Form */}
          <form onSubmit={handleSave} className={styles.form}>
            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>Hero</h2>

              <div className={styles.field}>
                <label>Conference Title</label>
                <input
                  name="title"
                  value={form.title || ""}
                  onChange={handleChange}
                />
              </div>

              <div className={styles.field}>
                <label>Short Description</label>
                <input
                  name="short_description"
                  value={form.short_description || ""}
                  onChange={handleChange}
                />
              </div>

              <div className={styles.row}>
                <div className={styles.field}>
                  <label>Location</label>
                  <input
                    name="location"
                    value={form.location || ""}
                    onChange={handleChange}
                  />
                </div>
                <div className={styles.field}>
                  <label>Badge Title</label>
                  <input
                    name="badge_title"
                    value={form.badge_title || ""}
                    onChange={handleChange}
                  />
                </div>
              </div>

              <div className={styles.row}>
                <div className={styles.field}>
                  <label>Date Start</label>
                  <input
                    name="date_start"
                    type="date"
                    value={form.date_start || ""}
                    onChange={handleChange}
                  />
                </div>
                <div className={styles.field}>
                  <label>Date End</label>
                  <input
                    name="date_end"
                    type="date"
                    value={form.date_end || ""}
                    onChange={handleChange}
                  />
                </div>
              </div>

              <div className={styles.field}>
                <label>
                  Card photo{" "}
                  <span className={styles.hint}>
                    (leave empty to keep the current photo)
                  </span>
                </label>
                <input
                  type="file"
                  name="card_photo"
                  accept="image/*"
                  onChange={handleCardPhotoChange}
                />
              </div>

              <div className={styles.field}>
                <label>
                  Hero photo{" "}
                  <span className={styles.hint}>
                    (leave empty to keep the current photo)
                  </span>
                </label>
                {heroPhotoFile ? (
                  <img
                    src={URL.createObjectURL(heroPhotoFile)}
                    alt="New hero preview"
                    className={styles.photoPreview}
                  />
                ) : heroPhoto ? (
                  <img
                    src={buildMediaUrl(heroPhoto)}
                    alt="Conference hero"
                    className={styles.photoPreview}
                  />
                ) : null}
                <input
                  type="file"
                  name="hero_photo"
                  accept="image/*"
                  onChange={handleHeroPhotoChange}
                />
              </div>

              <div className={styles.field}>
                <label>Description</label>
                <textarea
                  name="description"
                  rows={5}
                  value={form.description || ""}
                  onChange={handleChange}
                />
              </div>
            </section>

            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>Registration</h2>

              <div className={styles.field}>
                <label>Fee Note</label>
                <input
                  name="registration_fee_note"
                  value={form.registration_fee_note || ""}
                  onChange={handleChange}
                />
              </div>

              <div className={styles.field}>
                <label>
                  Registration Instructions{" "}
                  <span className={styles.hint}>(one item per line)</span>
                </label>
                <textarea
                  name="registration_instructions"
                  rows={6}
                  value={form.registration_instructions || ""}
                  onChange={handleChange}
                />
              </div>

              <div className={styles.field}>
                <label>Registration Deadline</label>
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

          {/* Organising Committee */}
          <PersonSection
            title="Organising Committee"
            list={committee}
            saving={saving}
            savedMsg={
              personSaved === "committees" ? "✓ Saved successfully" : ""
            }
            errorMsg={personError}
            onSaveAll={() =>
              saveAllPersons("committees", committee, setCommittee)
            }
            onDelete={(id) =>
              deletePerson("committees", id, committee, setCommittee)
            }
            onChange={(i, field, val) =>
              handlePersonChange(committee, setCommittee, i, field, val)
            }
            onPhoto={(i, file) =>
              handlePersonPhoto(committee, setCommittee, i, file)
            }
            onAdd={() => addPerson(committee, setCommittee)}
          />

          {/* Organisers  */}
          <PersonSection
            title="Organisers"
            list={organizers}
            saving={saving}
            savedMsg={
              personSaved === "organizers" ? "✓ Saved successfully" : ""
            }
            errorMsg={personError}
            onSaveAll={() =>
              saveAllPersons("organizers", organizers, setOrganizers)
            }
            onDelete={(id) =>
              deletePerson("organizers", id, organizers, setOrganizers)
            }
            onChange={(i, field, val) =>
              handlePersonChange(organizers, setOrganizers, i, field, val)
            }
            onPhoto={(i, file) =>
              handlePersonPhoto(organizers, setOrganizers, i, file)
            }
            onAdd={() => addPerson(organizers, setOrganizers)}
          />
        </div>
      )}
    </div>
  );
}

function PersonSection({
  title,
  list,
  onSaveAll,
  onDelete,
  onChange,
  onPhoto,
  onAdd,
  saving,
  savedMsg,
  errorMsg,
}) {
  return (
    <section className={styles.section} style={{ marginTop: 40 }}>
      <h2 className={styles.sectionTitle}>{title}</h2>

      {list.length === 0 && (
        <p className={styles.emptyMsg}>No people added yet.</p>
      )}

      {list.map((person, i) => (
        <div key={person.id ?? `new-${i}`} className={styles.personRow}>
          <div className={styles.photoCol}>
            {person._photoFile ? (
              <img
                src={URL.createObjectURL(person._photoFile)}
                alt="preview"
                className={styles.personPhoto}
              />
            ) : person.photo ? (
              <img
                src={person.photo}
                alt={person.name}
                className={styles.personPhoto}
              />
            ) : (
              <div className={styles.photoPlaceholder} />
            )}
            <label className={styles.photoLabel}>
              Change photo
              <input
                type="file"
                accept="image/*"
                onChange={(e) => onPhoto(i, e.target.files[0])}
                className={styles.fileInputHidden}
              />
            </label>
          </div>

          <div className={styles.personFields}>
            <div className={styles.field}>
              <label>Name</label>
              <input
                value={person.name || ""}
                onChange={(e) => onChange(i, "name", e.target.value)}
              />
            </div>
            <div className={styles.field}>
              <label>Department / Affiliation</label>
              <input
                value={person.department || ""}
                onChange={(e) => onChange(i, "department", e.target.value)}
              />
            </div>
            <div className={styles.field}>
              <label>Email</label>
              <input
                type="email"
                value={person.email || ""}
                onChange={(e) => onChange(i, "email", e.target.value)}
              />
            </div>
          </div>

          <button
            type="button"
            className={styles.deleteButton}
            onClick={() => onDelete(person.id)}
          >
            ✕
          </button>
        </div>
      ))}

      {errorMsg && <p className={styles.error}>{errorMsg}</p>}

      <div className={styles.personActions}>
        <button type="button" className={styles.addButton} onClick={onAdd}>
          + ADD PERSON
        </button>
        <div className={styles.saveRow}>
          {savedMsg && <span className={styles.savedMsg}>{savedMsg}</span>}
          <button
            type="button"
            className={styles.saveButton}
            onClick={onSaveAll}
            disabled={saving}
          >
            {saving ? "Saving..." : `SAVE ${title.toUpperCase()}`}
          </button>
        </div>
      </div>
    </section>
  );
}
