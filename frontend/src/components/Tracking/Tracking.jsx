import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { buildApiUrl, buildMediaUrl } from "../../utils/api";
import {
  submissionEditEffectiveDeadline,
  submissionEditWindowStatus,
} from "../../utils/registrationWindow";
import { countWords, validateSubmissionForm } from "../../utils/submissionForm";
import { useConferenceInfo } from "../hooks/useConferenceInfo";
import SubmissionFields from "../SubmissionFields/SubmissionFields";
import Loader from "../ui/Loader/Loader";
import Title from "../ui/Title/Title";
import styles from "./Tracking.module.css";

// Date inputs want yyyy-MM-dd; the API dates may carry a time component.
const toDateInputValue = (value) => (value ? String(value).slice(0, 10) : "");

const toFormData = (submission) => ({
  name: submission.name || "",
  email: submission.email || "",
  affiliation: submission.affiliation || "",
  abstract_title: submission.abstract_title || "",
  abstract_text: submission.abstract_text || "",
  additional_authors: submission.additional_authors || "",
  additional_affiliations: submission.additional_affiliations || "",
  arrival: toDateInputValue(submission.arrival_date),
  departure: toDateInputValue(submission.departure_date),
  info: submission.info || "",
  is_student: Boolean(submission.is_student),
});

const toApiPayload = (formData) => ({
  name: formData.name,
  email: formData.email,
  affiliation: formData.affiliation,
  abstract_title: formData.abstract_title,
  abstract_text: formData.abstract_text,
  additional_authors: formData.additional_authors,
  additional_affiliations: formData.additional_affiliations,
  arrival_date: formData.arrival,
  departure_date: formData.departure,
  info: formData.info,
  is_student: formData.is_student,
});

// Backend 400 keys arrive in API naming; SubmissionFields keys are form-local.
const REVERSE_FIELD_MAP = {
  arrival_date: "arrival",
  departure_date: "departure",
};

const toFormErrors = (errorData) => {
  const mapped = {};
  Object.entries(errorData).forEach(([key, value]) => {
    mapped[REVERSE_FIELD_MAP[key] || key] = Array.isArray(value)
      ? value.join(" ")
      : String(value);
  });
  return mapped;
};

const formatTimestamp = (iso) =>
  new Date(iso).toLocaleString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

const formatDate = (iso) =>
  new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

export default function Tracking() {
  const { trackingToken } = useParams();
  const info = useConferenceInfo();
  const trackUrl = buildApiUrl(`/api/track/${trackingToken}/`);

  const [submission, setSubmission] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);

  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState(null);
  const [photo, setPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [errors, setErrors] = useState({});
  const [wordCount, setWordCount] = useState(0);
  const [saving, setSaving] = useState(false);
  const [savedMessage, setSavedMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch(trackUrl)
      .then(async (response) => {
        if (cancelled) return;
        if (response.status === 404) {
          setNotFound(true);
        } else if (response.ok) {
          setSubmission(await response.json());
        } else {
          setLoadFailed(true);
        }
      })
      .catch(() => {
        if (!cancelled) setLoadFailed(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [trackUrl]);

  // Post-save refresh: best effort, keeps the stale rendering on failure.
  const refetchSubmission = useCallback(async () => {
    try {
      const response = await fetch(trackUrl);
      if (response.ok) {
        setSubmission(await response.json());
      }
    } catch {
      // Stale data stays visible; the saved confirmation already told the
      // user their edit landed.
    }
  }, [trackUrl]);

  const startEditing = () => {
    setFormData(toFormData(submission));
    setWordCount(countWords(submission.abstract_text || ""));
    setPhoto(null);
    setPhotoPreview(submission.photo ? buildMediaUrl(submission.photo) : null);
    setErrors({});
    setSavedMessage("");
    setEditing(true);
  };

  const cancelEditing = () => {
    setEditing(false);
    setFormData(null);
    setPhoto(null);
    setPhotoPreview(null);
    setErrors({});
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
    if (name === "abstract_text") {
      setWordCount(countWords(value));
    }
  };

  const handlePhotoChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.type.startsWith("image/")) {
        setErrors({ ...errors, photo: "Please select a valid image file" });
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        setErrors({ ...errors, photo: "Photo size must not exceed 5MB" });
        return;
      }
      setPhoto(file);
      const reader = new FileReader();
      reader.onloadend = () => setPhotoPreview(reader.result);
      reader.readAsDataURL(file);
      const newErrors = { ...errors };
      delete newErrors.photo;
      setErrors(newErrors);
    }
  };

  const clearFileInput = () => {
    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) fileInput.value = "";
  };

  // A freshly picked photo is discarded locally; a server-side photo is
  // deleted via the update serializer's explicit-null path.
  const handleRemovePhoto = async () => {
    if (photo) {
      setPhoto(null);
      setPhotoPreview(
        submission.photo ? buildMediaUrl(submission.photo) : null
      );
      clearFileInput();
      return;
    }
    setSaving(true);
    try {
      const response = await fetch(trackUrl, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ photo: null }),
      });
      if (response.ok) {
        setPhotoPreview(null);
        clearFileInput();
        setSavedMessage("Photo removed.");
        await refetchSubmission();
      } else {
        setErrors({ detail: "Failed to remove the photo. Please try again." });
      }
    } catch {
      setErrors({ detail: "Connection error. Please try again." });
    } finally {
      setSaving(false);
    }
  };

  // Photo rides along only when a new file exists (multipart); otherwise
  // the key is omitted entirely so the stored photo is kept.
  const handleSubmit = async (e) => {
    e.preventDefault();
    const newErrors = validateSubmissionForm({ formData, photo });
    setErrors(newErrors);
    if (Object.keys(newErrors).length > 0) {
      return;
    }
    setSaving(true);
    try {
      const payload = toApiPayload(formData);
      let response;
      if (photo) {
        const submitData = new FormData();
        Object.entries(payload).forEach(([key, value]) => {
          submitData.append(key, value);
        });
        submitData.append("photo", photo);
        response = await fetch(trackUrl, { method: "PATCH", body: submitData });
      } else {
        response = await fetch(trackUrl, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      }
      if (response.ok) {
        setSavedMessage("Changes saved.");
        setEditing(false);
        setFormData(null);
        setPhoto(null);
        setPhotoPreview(null);
        setErrors({});
        await refetchSubmission();
      } else if (response.status === 400) {
        setErrors(toFormErrors(await response.json()));
      } else {
        setErrors({
          detail: `Saving failed (error ${response.status}). Please try again.`,
        });
      }
    } catch {
      setErrors({ detail: "Connection error. Please try again." });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <section className={styles.section}>
        <Title text="Your Submission" />
        <Loader />
      </section>
    );
  }

  if (notFound) {
    return (
      <section className={styles.section}>
        <Title text="Your Submission" />
        <div className={styles.panel}>
          <p className={styles.notFoundText}>
            Submission not found. Check your tracking link or contact the
            organizers.
          </p>
          <a className={styles.button} href="#/registration">
            Back to registration
          </a>
        </div>
      </section>
    );
  }

  if (loadFailed || !submission) {
    return (
      <section className={styles.section}>
        <Title text="Your Submission" />
        <div className={styles.panel}>
          <p className={styles.notFoundText}>
            Could not load your submission. Please try again later.
          </p>
        </div>
      </section>
    );
  }

  const isApproved = submission.status === "approved";
  const editWindowStatus = info ? submissionEditWindowStatus(info) : null;
  const editLocked = editWindowStatus === "closed";

  const rows = [
    ["Name", submission.name],
    ["Email", submission.email],
    ["Affiliation", submission.affiliation],
    ["Abstract title", submission.abstract_title],
    ["Abstract", submission.abstract_text],
    ["Additional authors", submission.additional_authors],
    ["Additional affiliations", submission.additional_affiliations],
    ["Arrival", submission.arrival_date && formatDate(submission.arrival_date)],
    [
      "Departure",
      submission.departure_date && formatDate(submission.departure_date),
    ],
    ["Student", submission.is_student ? "Yes" : "No"],
    ["Additional information", submission.info],
  ];

  return (
    <section className={styles.section}>
      <Title text="Your Submission" />
      <div className={styles.fadeIn}>
        {savedMessage && <p className={styles.savedNotice}>{savedMessage}</p>}

        <div className={styles.panel}>
          <div className={styles.headerRow}>
            <p className={styles.reference}>
              {submission.participant_reference}
            </p>
            <span
              className={
                isApproved ? styles.badgePublished : styles.badgePending
              }
            >
              {isApproved ? "Published" : "Pending review"}
            </span>
          </div>

          <p className={styles.timestamp}>
            Submitted: {formatTimestamp(submission.submitted_at)}
          </p>
          {submission.reviewed_at && (
            <p className={styles.timestamp}>
              Reviewed: {formatTimestamp(submission.reviewed_at)}
            </p>
          )}

          {editing ? (
            <form className={styles.form} onSubmit={handleSubmit}>
              {isApproved && (
                <p className={styles.approvedNotice}>
                  Saving changes sends your submission back for review.
                </p>
              )}
              {errors.detail && (
                <p className={styles.errorText}>{errors.detail}</p>
              )}
              <SubmissionFields
                formData={formData}
                errors={errors}
                photoPreview={photoPreview}
                onChange={handleChange}
                onPhotoChange={handlePhotoChange}
                onRemovePhoto={handleRemovePhoto}
                wordCount={wordCount}
              />
              <div className={styles.formActions}>
                <button
                  type="submit"
                  className={styles.button}
                  disabled={saving}
                >
                  {saving ? "Saving..." : "Save changes"}
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={cancelEditing}
                  disabled={saving}
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <>
              <dl className={styles.fields}>
                {rows.map(([label, value]) =>
                  value ? (
                    <div className={styles.fieldRow} key={label}>
                      <dt className={styles.fieldLabel}>{label}</dt>
                      <dd className={styles.fieldValue}>{value}</dd>
                    </div>
                  ) : null
                )}
                {submission.photo && (
                  <div className={styles.fieldRow}>
                    <dt className={styles.fieldLabel}>Photo</dt>
                    <dd className={styles.fieldValue}>
                      <img
                        className={styles.photoImg}
                        src={buildMediaUrl(submission.photo)}
                        alt="Participant portrait"
                      />
                    </dd>
                  </div>
                )}
              </dl>

              {editWindowStatus === "open" && (
                <button
                  type="button"
                  className={styles.button}
                  onClick={startEditing}
                >
                  Edit submission
                </button>
              )}
              {editLocked && (
                <p className={styles.lockedNotice}>
                  {`Editing submissions closed on ${formatDate(submissionEditEffectiveDeadline(info))} — your submission can no longer be edited online. Contact the organizers for changes.`}
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
