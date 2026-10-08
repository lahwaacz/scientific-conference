import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { buildApiUrl } from "../../utils/api";
import { registrationWindowStatus } from "../../utils/registrationWindow";
import { countWords, validateSubmissionForm } from "../../utils/submissionForm";
import { useConferenceInfo } from "../hooks/useConferenceInfo";
import { useUnsavedChangesGuard } from "../hooks/useUnsavedChangesGuard";
import SubmissionFields from "../SubmissionFields/SubmissionFields";
import Modal from "../ui/Modal/Modal";
import Title from "../ui/Title/Title";
import styles from "./RegistrationForm.module.css";

function useModal() {
  const [modal, setModal] = useState({ isOpen: false });

  const showAlert = useCallback((message, title = "") => {
    return new Promise((resolve) => {
      setModal({
        isOpen: true,
        title,
        message,
        confirmText: "OK",
        onConfirm: () => {
          setModal({ isOpen: false });
          resolve(true);
        },
        onCancel: null,
        type: "default",
      });
    });
  }, []);

  const showConfirm = useCallback((message, title = "") => {
    return new Promise((resolve) => {
      setModal({
        isOpen: true,
        title,
        message,
        confirmText: "Confirm",
        cancelText: "Cancel",
        onConfirm: () => {
          setModal({ isOpen: false });
          resolve(true);
        },
        onCancel: () => {
          setModal({ isOpen: false });
          resolve(false);
        },
        type: "default",
      });
    });
  }, []);

  return { modal, showAlert, showConfirm };
}

const initialFormData = {
  name: "",
  email: "",
  affiliation: "",
  abstract_title: "",
  abstract_text: "",
  additional_authors: "",
  additional_affiliations: "",
  arrival: "",
  departure: "",
  info: "",
  is_student: false,
};

export default function RegistrationForm() {
  const info = useConferenceInfo();
  const { modal, showAlert } = useModal();
  const navigate = useNavigate();

  const [formData, setFormData] = useState(initialFormData);
  const [photo, setPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [errors, setErrors] = useState({});
  const [wordCount, setWordCount] = useState(0);
  const [successData, setSuccessData] = useState(null);
  const [copied, setCopied] = useState(false);

  const isDirty =
    photo !== null ||
    formData.is_student ||
    Object.keys(formData).some(
      (key) => key !== "is_student" && formData[key] !== ""
    );
  useUnsavedChangesGuard(
    isDirty,
    "Leave the registration form? Unsubmitted changes will be lost."
  );

  const validate = () => {
    const newErrors = validateSubmissionForm({ formData, photo });
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const trackingUrl = successData
    ? `${window.location.origin}${window.location.pathname}#/track/${successData.tracking_token}`
    : "";

  // Clearing the form state also disarms the unsaved-changes guard.
  const clearFormState = () => {
    setFormData({ ...initialFormData });
    setPhoto(null);
    setPhotoPreview(null);
    setErrors({});
    setWordCount(0);
  };

  const startNewRegistration = () => {
    setSuccessData(null);
    setCopied(false);
    clearFormState();
  };

  const copyTrackingLink = async () => {
    let copiedViaClipboard = false;
    if (navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(trackingUrl);
        copiedViaClipboard = true;
      } catch {
        copiedViaClipboard = false;
      }
    }
    if (!copiedViaClipboard) {
      const textarea = document.createElement("textarea");
      textarea.value = trackingUrl;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      textarea.remove();
    }
    setCopied(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (validate()) {
      try {
        const submitData = new FormData();
        submitData.append("name", formData.name);
        submitData.append("email", formData.email);
        submitData.append("affiliation", formData.affiliation);
        submitData.append("abstract_title", formData.abstract_title);
        submitData.append("abstract_text", formData.abstract_text);
        submitData.append("additional_authors", formData.additional_authors);
        submitData.append(
          "additional_affiliations",
          formData.additional_affiliations
        );
        submitData.append("arrival_date", formData.arrival);
        submitData.append("departure_date", formData.departure);
        submitData.append("info", formData.info);
        submitData.append("is_student", formData.is_student);

        if (photo) {
          submitData.append("photo", photo);
        }

        const response = await fetch(buildApiUrl("/api/submit/"), {
          method: "POST",
          body: submitData,
        });

        if (response.ok) {
          const data = await response.json();
          if (!data.participant_reference || !data.tracking_token) {
            throw new Error("Registration response is missing tracking fields");
          }
          setSuccessData({
            participant_reference: data.participant_reference,
            tracking_token: data.tracking_token,
          });
          clearFormState();
        } else {
          const errorData = await response.json();
          await showAlert(
            ` Registration failed: ${JSON.stringify(errorData)}`,
            "Error"
          );
        }
      } catch (error) {
        console.error("Error:", error);
        await showAlert(" Connection error. Please try again.", "Error");
      }
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({
      ...formData,
      [name]: type === "checkbox" ? checked : value,
    });

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

  const removePhoto = () => {
    setPhoto(null);
    setPhotoPreview(null);
    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) fileInput.value = "";
  };

  const deadlineStr = info?.registration_deadline
    ? new Date(info.registration_deadline).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : null;

  const formatDate = (iso) =>
    new Date(iso).toLocaleDateString("en-GB", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });

  if (!info) {
    return (
      <section className={styles.formSection}>
        <Title text="Registration Form" />
      </section>
    );
  }

  const windowStatus = registrationWindowStatus(info);

  if (windowStatus === "not-open") {
    return (
      <section className={styles.formSection}>
        <Title text="Registration Form" />
        <p className={styles.closedNotice}>
          Registration is not open yet. It opens on{" "}
          {formatDate(info.registration_opening)}.
        </p>
      </section>
    );
  }

  if (windowStatus === "closed" || windowStatus === "ended") {
    return (
      <section className={styles.formSection}>
        <Title text="Registration Form" />
        <p className={styles.closedNotice}>
          {windowStatus === "closed"
            ? `Registration is closed. The deadline was ${formatDate(info.registration_deadline)}.`
            : "Registration is closed. The conference has already taken place."}
        </p>
      </section>
    );
  }

  return (
    <section className={styles.formSection}>
      <Modal {...modal} />
      <Title text="Registration Form" />
      <div className={styles.fadeIn}>
        {info?.registration_fee_note && (
          <p className={styles.instructions}>{info.registration_fee_note}</p>
        )}

        {deadlineStr && (
          <p className={styles.deadline}>
            Please submit your registration until {deadlineStr}
          </p>
        )}

        {successData ? (
          <div className={styles.successPanel}>
            <p className={styles.successTitle}>Registration successful!</p>
            <p className={styles.successLabel}>Your participant reference:</p>
            <p className={styles.successReference}>
              {successData.participant_reference}
            </p>
            <p className={styles.successLabel}>Your tracking link:</p>
            <div className={styles.trackingRow}>
              <p className={styles.trackingUrl}>{trackingUrl}</p>
              <button
                type="button"
                className={styles.copyButton}
                onClick={copyTrackingLink}
              >
                {copied ? "Copied!" : "Copy link"}
              </button>
            </div>
            <p className={styles.warning}>
              Save this link — it is the only way to access and edit your
              submission. If you lose it, contact the organizers.
            </p>
            <button
              type="button"
              className={styles.button}
              onClick={() => navigate(`/track/${successData.tracking_token}`)}
            >
              Open my submission
            </button>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={startNewRegistration}
            >
              Submit another registration
            </button>
          </div>
        ) : (
          <form className={styles.form} onSubmit={handleSubmit}>
            <SubmissionFields
              formData={formData}
              errors={errors}
              photoPreview={photoPreview}
              onChange={handleChange}
              onPhotoChange={handlePhotoChange}
              onRemovePhoto={removePhoto}
              wordCount={wordCount}
            />

            <button type="submit" className={styles.button}>
              Submit
            </button>
          </form>
        )}
      </div>
    </section>
  );
}
