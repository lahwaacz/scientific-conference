import styles from './Footer.module.css';
import LogoIcon from '../../assets/logoWhite.png';
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import AdminLoginModal from '../AdminLoginModal/AdminLoginModal';
import { useConferenceInfo } from './../hooks/useConferenceInfo';
import { useLockBodyScroll } from './../hooks/useLockBodyScroll';

export default function Footer() {
  const location = useLocation();
  const navigate = useNavigate();
  const isAdminPage = location.pathname.startsWith("/admin-panel");
  const info = useConferenceInfo();
  const [isAdminOpen, setIsAdminOpen] = useState(false);

  useLockBodyScroll(isAdminOpen);

  function Logo() {
    return (
      <div className={styles.logo}>
        <img className={styles.logoIcon} src={LogoIcon} alt="Logo" />
      </div>
    );
  }

  function openAdmin(e) {
    e.preventDefault();
    setIsAdminOpen(true);
  }

  return (
    <footer className={styles.footer}>
      <div className={styles.footerContainer}>

        <div className={styles.column}>
          <Logo />
          <p>{info?.grant_text || ''}</p>
        </div>

        <div className={styles.column}>
          <h4>Venue</h4>
          <p>{info?.venue_text || ''}</p>
        </div>

        <div className={styles.column}>
          <h4>Conference office</h4>
          <p>{info?.conference_office_text || ''}</p>
        </div>

        <div className={styles.column}>
          <h4>Additional information</h4>
          <p>
            {info?.website_url && (
              <>URL: <a href={info.website_url} target="_blank" rel="noopener noreferrer">{info.website_url}</a><br /></>
            )}
            {info?.poster_url && (
              <>Conference poster: <a href={info.poster_url} target="_blank" rel="noopener noreferrer">WSC Poster</a><br /></>
            )}
            {info?.info_desk_email && (
              <>Information desk: <a href={`mailto:${info.info_desk_email}`}>{info.info_desk_email}</a></>
            )}
          </p>
        </div>

      </div>

      <hr className={styles.separator} />

      <div className={styles.bottomRow}>
        <p className={styles.bottomText}>{info?.copyright_text || ''}</p>
        {!isAdminPage && (
          <a href="#" className={styles.adminLink} onClick={openAdmin}>
            Administration
          </a>
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
