import { useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import LogoIcon from "../../assets/logoWhite.png";
import { canManageConference } from "../../utils/access";
import { fetchWithAuth, refreshAccessToken } from "../../utils/api";
import { getConferenceSlug } from "../../utils/conferenceSlug";
import AdminLoginModal from "../AdminLoginModal/AdminLoginModal";
import { useConferenceInfo } from "./../hooks/useConferenceInfo";
import { useLockBodyScroll } from "./../hooks/useLockBodyScroll";
import styles from "./Footer.module.css";

async function probeAdminAccess() {
  const response = await fetchWithAuth("/api/auth/user/", {
    skipRefresh: true,
  });
  if (response.ok) {
    return canManageConference(await response.json(), getConferenceSlug());
  }
  if (response.status !== 401) {
    return false;
  }
  if (!(await refreshAccessToken({ reloadOnFailure: false }))) {
    return false;
  }
  const retry = await fetchWithAuth("/api/auth/user/", { skipRefresh: true });
  if (!retry.ok) {
    return false;
  }
  return canManageConference(await retry.json(), getConferenceSlug());
}

function Logo() {
  return (
    <div className={styles.logo}>
      <img className={styles.logoIcon} src={LogoIcon} alt="Logo" />
    </div>
  );
}

export default function Footer() {
  const location = useLocation();
  const navigate = useNavigate();
  const isAdminPage = location.pathname.startsWith("/admin-panel");
  const info = useConferenceInfo();
  const [isAdminOpen, setIsAdminOpen] = useState(false);
  const isProbingAuth = useRef(false);

  useLockBodyScroll(isAdminOpen);

  async function openAdmin(e) {
    e.preventDefault();
    if (isProbingAuth.current) {
      return;
    }

    isProbingAuth.current = true;
    let allowed = false;
    try {
      allowed = await probeAdminAccess();
    } catch {
      allowed = false;
    } finally {
      isProbingAuth.current = false;
    }

    if (allowed) {
      navigate("/admin-panel");
      return;
    }

    setIsAdminOpen(true);
  }

  return (
    <footer className={styles.footer}>
      <div className={styles.footerContainer}>
        <div className={styles.column}>
          <Logo />
          <p>{info?.grant_text || ""}</p>
        </div>

        <div className={styles.column}>
          <h4>Venue</h4>
          <p>{info?.footer_venue_text || ""}</p>
        </div>

        <div className={styles.column}>
          <h4>Conference office</h4>
          <p>{info?.conference_office_text || ""}</p>
        </div>

        <div className={styles.column}>
          <h4>Additional information</h4>
          <p>
            {info?.website_url && (
              <>
                URL:{" "}
                <a
                  href={info.website_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {info.website_url}
                </a>
                <br />
              </>
            )}
            {info?.poster_url && (
              <>
                Conference poster:{" "}
                <a
                  href={info.poster_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  WSC Poster
                </a>
                <br />
              </>
            )}
            {info?.info_desk_email && (
              <>
                Information desk:{" "}
                <a href={`mailto:${info.info_desk_email}`}>
                  {info.info_desk_email}
                </a>
              </>
            )}
          </p>
        </div>
      </div>

      <hr className={styles.separator} />

      <div className={styles.bottomRow}>
        <p className={styles.bottomText}>{info?.copyright_text || ""}</p>
        {!isAdminPage && (
          <button
            type="button"
            className={styles.adminLink}
            onClick={openAdmin}
          >
            Administration
          </button>
        )}
      </div>

      {isAdminOpen && (
        <AdminLoginModal
          onClose={() => setIsAdminOpen(false)}
          onSuccess={() => {
            setIsAdminOpen(false);
            navigate("/admin-panel");
          }}
        />
      )}
    </footer>
  );
}
