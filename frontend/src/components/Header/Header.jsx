import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import LogoIcon from "../../assets/logo.svg";
import { buildApiUrl, fetchWithAuth } from "../../utils/api";
import { useLockBodyScroll } from "./../hooks/useLockBodyScroll";
import Modal from "../ui/Modal/Modal";
import styles from "./Header.module.css";

export default function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { pathname } = useLocation();
  const isAdmin =
    pathname === "/admin-panel" || pathname.startsWith("/admin-panel/");

  const toggleMenu = () => setMenuOpen((prev) => !prev);
  useLockBodyScroll(menuOpen);
  const closeMenu = () => setMenuOpen(false);

  // biome-ignore-start lint/a11y/noStaticElementInteractions lint/a11y/useKeyWithClickEvents: backdrop overlay and hover wrapper exist only as pointer shortcuts; the burger toggle and arrow buttons carry every interaction.
  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Logo onNavigate={closeMenu} isAdmin={isAdmin} />

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

        {menuOpen && (
          <div
            className={styles.overlay}
            onClick={closeMenu}
            role="presentation"
          />
        )}

        {isAdmin ? (
          <AdminNav isOpen={menuOpen} onNavigate={closeMenu} />
        ) : (
          <Navbar isOpen={menuOpen} onNavigate={closeMenu} />
        )}
      </div>
    </header>
  );
  // biome-ignore-end lint/a11y/noStaticElementInteractions lint/a11y/useKeyWithClickEvents: Header scope ends
}

function Logo({ onNavigate, isAdmin = false }) {
  const location = useLocation();
  const target = isAdmin ? "/admin-panel" : "/";

  const handleLogoClick = (e) => {
    if (location.pathname === target) {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
    onNavigate?.();
  };

  return (
    <Link
      className={styles.logo}
      to={target}
      onClick={handleLogoClick}
      aria-label={isAdmin ? "Admin panel home" : "Conference home"}
    >
      <LogoIcon className={styles.logoIcon} />
    </Link>
  );
}

function AdminNav({ isOpen, onNavigate }) {
  const [user, setUser] = useState(null);
  const [modal, setModal] = useState({ isOpen: false });
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    fetchWithAuth("/api/auth/user/")
      .then((res) => (res.ok ? res.json() : null))
      .then((payload) => {
        if (!cancelled) {
          setUser(payload);
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const closeModal = () => setModal((prev) => ({ ...prev, isOpen: false }));

  async function handleLogout() {
    try {
      const res = await fetchWithAuth("/api/auth/logout/", { method: "POST" });
      if (!res.ok) {
        setModal({
          isOpen: true,
          title: "Logout failed",
          message: "The server could not end the session. Please try again.",
          type: "danger",
        });
        return;
      }
      navigate("/");
    } catch (error) {
      setModal({
        isOpen: true,
        title: "Connection error",
        message: error.message || "Server is unreachable.",
        type: "danger",
      });
    }
  }

  return (
    <nav className={`${styles.navBar} ${isOpen ? styles.navBarOpen : ""}`}>
      <div className={styles.adminNavList}>
        {user?.username && (
          <div className={styles.adminNavItem}>
            <span className={styles.username}>{user.username}</span>
          </div>
        )}
        <div className={styles.adminNavItem}>
          <Link
            className={`nav-link ${styles.whiteLink}`}
            to="/"
            onClick={onNavigate}
          >
            View site
          </Link>
        </div>
        {user?.is_superuser && (
          <div className={styles.adminNavItem}>
            <a
              className={`nav-link ${styles.whiteLink}`}
              href={buildApiUrl("/admin/")}
            >
              Django admin
            </a>
          </div>
        )}
        <div className={styles.adminNavItem}>
          <button
            type="button"
            className={`nav-link ${styles.whiteLink} ${styles.logoutLink}`}
            onClick={handleLogout}
          >
            Logout
          </button>
        </div>
      </div>

      <Modal
        isOpen={modal.isOpen}
        title={modal.title}
        message={modal.message}
        type={modal.type}
        onConfirm={closeModal}
        onCancel={null}
      />
    </nav>
  );
}

function Navbar({ isOpen, onNavigate }) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [pinnedOpen, setPinnedOpen] = useState(false);
  // null = not yet known; false hides the link. Fetch failures and
  // non-list payloads fail open so a backend hiccup never hides nav.
  const [hasAccommodation, setHasAccommodation] = useState(null);
  const [hasHiking, setHasHiking] = useState(null);
  let timeout;

  useEffect(() => {
    fetch(buildApiUrl("/api/accommodation/"))
      .then((res) => (res.ok ? res.json() : null))
      .then((payload) =>
        setHasAccommodation(
          !payload ||
            Boolean(payload.description) ||
            (Array.isArray(payload.options) && payload.options.length > 0)
        )
      )
      .catch(() => setHasAccommodation(true));
    fetch(buildApiUrl("/api/hiking/"))
      .then((res) => (res.ok ? res.json() : null))
      .then((routes) =>
        setHasHiking(!Array.isArray(routes) || routes.length > 0)
      )
      .catch(() => setHasHiking(true));
  }, []);

  const open = () => {
    clearTimeout(timeout);
    setDropdownOpen(true);
  };

  const hasSubmenuItems = hasAccommodation !== false || hasHiking !== false;

  const close = () => {
    if (pinnedOpen) {
      return;
    }
    timeout = setTimeout(() => setDropdownOpen(false), 250);
  };

  const handleClick = () => {
    setDropdownOpen(!pinnedOpen);
    setPinnedOpen(!pinnedOpen);
  };

  // biome-ignore-start lint/a11y/noStaticElementInteractions: hover-only wrapper; the arrow button carries the interaction.

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

        {/* DROPDOWN — hidden entirely when neither section has content */}
        <div
          className={`${styles.navItem} ${styles.dropdownWrapper}`}
          onMouseEnter={hasSubmenuItems ? open : undefined}
          onMouseLeave={hasSubmenuItems ? close : undefined}
        >
          <div className={styles.venueRow}>
            <Link
              className={`nav-link ${styles.whiteLink} ${styles.venueLink}`}
              to="/venue"
              onClick={onNavigate}
            >
              Venue
            </Link>
            {(hasAccommodation !== false || hasHiking !== false) && (
              <button
                type="button"
                className={styles.arrow}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  handleClick();
                }}
                aria-label="Toggle venue submenu"
                aria-expanded={dropdownOpen}
              >
                ▼
              </button>
            )}
          </div>

          {dropdownOpen && hasSubmenuItems && (
            <div className={styles.dropdownMenu}>
              {hasAccommodation !== false && (
                <Link
                  to="/accommodation"
                  className={styles.dropdownItem}
                  onClick={onNavigate}
                >
                  Accommodation
                </Link>
              )}
              {hasHiking !== false && (
                <Link
                  to="/hiking"
                  className={styles.dropdownItem}
                  onClick={onNavigate}
                >
                  Hiking excursion
                </Link>
              )}
            </div>
          )}
        </div>
      </div>
    </nav>
  );
  // biome-ignore-end lint/a11y/noStaticElementInteractions: Navbar scope ends
}
