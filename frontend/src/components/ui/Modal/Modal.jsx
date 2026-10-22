import { useEffect } from "react";
import { createPortal } from "react-dom";
import styles from "./Modal.module.css";

export default function Modal({
  isOpen,
  title,
  message,
  confirmText,
  cancelText = "Cancel",
  onConfirm,
  onCancel,
  type = "default",
  children,
}) {
  const isNotification = !onCancel;
  const confirmLabel = confirmText ?? (isNotification ? "OK" : "Confirm");

  useEffect(() => {
    if (!isOpen) return;

    const scrollbarWidth =
      window.innerWidth - document.documentElement.clientWidth;
    document.body.style.overflow = "hidden";
    document.body.style.paddingRight = `${scrollbarWidth}px`;

    return () => {
      document.body.style.overflow = "";
      document.body.style.paddingRight = "";
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return createPortal(
    <div className={styles.overlay}>
      <div className={`${styles.modal} ${styles[type]}`}>
        {title && <h3 className={styles.title}>{title}</h3>}
        {message && <p className={styles.message}>{message}</p>}
        {children}

        <div className={styles.actions}>
          {onCancel && (
            <button onClick={onCancel} className={styles.cancelBtn}>
              {cancelText}
            </button>
          )}
          {onConfirm && (
            <button onClick={onConfirm} className={styles.confirmBtn}>
              {confirmLabel}
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}
