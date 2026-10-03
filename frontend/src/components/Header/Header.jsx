import styles from "./Header.module.css";
import { ReactComponent as LogoIcon } from "../../assets/logo.svg";
import { Link, useLocation } from "react-router-dom";
import { useState, useEffect } from "react";
import { useLockBodyScroll } from "./../hooks/useLockBodyScroll";

export default function Header() {
  const [menuOpen, setMenuOpen] = useState(false);

  const toggleMenu = () => setMenuOpen((prev) => !prev);
  useLockBodyScroll(menuOpen);
  const closeMenu = () => setMenuOpen(false);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
  }, [menuOpen]);

  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Logo onNavigate={closeMenu} />

        <button
          className={styles.burger}
          onClick={toggleMenu}
          aria-label="Toggle menu"
          aria-expanded={menuOpen}
        >
          {menuOpen ? (
            <span className={styles.closeIcon}>✕</span>
          ) : (
            <>
              <span className={styles.line}></span>
              <span className={styles.line}></span>
              <span className={styles.line}></span>
            </>
          )}
        </button>

        {menuOpen && <div className={styles.overlay} onClick={closeMenu} />}

        <Navbar isOpen={menuOpen} onNavigate={closeMenu} />
      </div>
    </header>
  );
}

function Logo({ onNavigate }) {
  const location = useLocation();

  const handleLogoClick = (e) => {
    if (location.pathname === "/") {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
    onNavigate?.();
  };

  return (
    <Link className={styles.logo} to="/" onClick={handleLogoClick}>
      <LogoIcon className={styles.logoIcon} />
    </Link>
  );
}

function Navbar({ isOpen, onNavigate }) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  let timeout;

  const open = () => {
    clearTimeout(timeout);
    setDropdownOpen(true);
  };

  const close = () => {
    timeout = setTimeout(() => setDropdownOpen(false), 250);
  };

  const handleClick = () => {
    setDropdownOpen((prev) => !prev);
  };

  return (
    <nav className={`${styles.navBar} ${isOpen ? styles.navBarOpen : ""}`}>
      <div className={styles.navList}>
        <div className={styles.navItem}>
          <Link
            className={`nav-link ${styles.whiteLink}`}
            to="/registration"
            onClick={onNavigate}
          >
            Registration
          </Link>
        </div>

        <div className={styles.navItem}>
          <Link
            className={`nav-link ${styles.whiteLink}`}
            to="/program"
            onClick={onNavigate}
          >
            Program
          </Link>
        </div>

        <div className={styles.navItem}>
          <Link
            className={`nav-link ${styles.whiteLink}`}
            to="/participants"
            onClick={onNavigate}
          >
            Participants
          </Link>
        </div>

        <div className={styles.navItem}>
          <Link
            className={`nav-link ${styles.whiteLink}`}
            to="/abstracts"
            onClick={onNavigate}
          >
            Abstracts
          </Link>
        </div>

        {/* DROPDOWN */}
        <div
          className={`${styles.navItem} ${styles.dropdownWrapper}`}
          onMouseEnter={open}
          onMouseLeave={close}
        >
          <div className={styles.venueRow}>
            <Link
              className={`nav-link ${styles.whiteLink} ${styles.venueLink}`}
              to="/venue"
              onClick={onNavigate}
            >
              Venue
            </Link>
            <span
              className={styles.arrow}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                handleClick();
              }}
            >
              ▼
            </span>
          </div>

          {dropdownOpen && (
            <div className={styles.dropdownMenu}>
              <Link
                to="/accommodation"
                className={styles.dropdownItem}
                onClick={onNavigate}
              >
                Accommodation
              </Link>
              <Link
                to="/hiking"
                className={styles.dropdownItem}
                onClick={onNavigate}
              >
                Hiking excursion
              </Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
