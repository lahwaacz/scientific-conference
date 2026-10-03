import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { buildMediaUrl, fetchWithAuth } from "../../utils/api";
import Loader from "../ui/Loader/Loader";
import Modal from "../ui/Modal/Modal";
import Title from "../ui/Title/Title";
import styles from "./EditWebInfoHiking.module.css";

export default function EditWebInfoHiking() {
  const [routes, setRoutes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedRoute, setSavedRoute] = useState(null);
  const [error] = useState("");
  const [modal, setModal] = useState({
    isOpen: false,
    title: "",
    message: "",
    onConfirm: null,
    type: "default",
  });

  function openModal(config) {
    setModal({
      isOpen: true,
      ...config,
    });
  }

  function closeModal() {
    setModal((prev) => ({ ...prev, isOpen: false }));
  }

  useEffect(() => {
    fetchWithAuth(`/api/hiking/`)
      .then((r) => r.json())
      .then((data) => {
        setRoutes(data);
        setLoading(false);
      });
  }, []);

  function handleRouteChange(routeIndex, field, value) {
    const updated = [...routes];
    updated[routeIndex] = { ...updated[routeIndex], [field]: value };
    setRoutes(updated);
  }

  function addRoute() {
    setRoutes([
      ...routes,
      { name: "", way_description: "", map_url: "", stops: [], _isNew: true },
    ]);
  }

  async function deleteRoute(routeIndex) {
    const route = routes[routeIndex];

    try {
      if (route.id) {
        const res = await fetchWithAuth(`/api/hiking/admin/`, {
          method: "DELETE",
          body: JSON.stringify({ id: route.id }),
        });

        if (!res.ok && res.status !== 204) {
          const errorText = await res.text();
          openModal({
            title: "Delete failed",
            message: errorText || "Failed to delete route.",
            type: "danger",
            onConfirm: closeModal,
          });
          return;
        }
      }

      setRoutes((prev) => prev.filter((_, i) => i !== routeIndex));

      openModal({
        title: "Success",
        message: "Route deleted successfully.",
        type: "success",
        onConfirm: closeModal,
      });
    } catch (error) {
      openModal({
        title: "Connection error",
        message: error.message || "Server is unreachable.",
        type: "danger",
        onConfirm: closeModal,
      });
    }
  }
  function confirmDeleteRoute(routeIndex) {
    openModal({
      title: "Delete route",
      message: "Delete this route and all its stops?",
      type: "danger",
      onConfirm: async () => {
        closeModal();
        await deleteRoute(routeIndex);
      },
    });
  }

  async function saveRoute(routeIndex) {
    const route = routes[routeIndex];
    setSaving(true);

    try {
      let res;

      if (route.id) {
        res = await fetchWithAuth(`/api/hiking/admin/`, {
          method: "PATCH",
          body: JSON.stringify({
            id: route.id,
            name: route.name,
            way_description: route.way_description,
            map_url: route.map_url,
          }),
        });
      } else {
        res = await fetchWithAuth("/api/hiking/admin/", {
          method: "POST",
          body: JSON.stringify({
            name: route.name,
            way_description: route.way_description,
            map_url: route.map_url,
          }),
        });
      }

      if (!res.ok) {
        const errorText = await res.text();
        openModal({
          title: "Save failed",
          message: errorText || "Failed to save route.",
          type: "danger",
          onConfirm: closeModal,
        });
        return;
      }

      const savedRouteData = await res.json();
      const updated = [...routes];
      updated[routeIndex] = { ...savedRouteData, stops: route.stops || [] };
      setRoutes(updated);
      setSavedRoute(routeIndex);

      openModal({
        title: "Success",
        message: "Route saved successfully.",
        type: "success",
        onConfirm: closeModal,
      });
    } catch (error) {
      openModal({
        title: "Connection error",
        message: error.message || "Server is unreachable.",
        type: "danger",
        onConfirm: closeModal,
      });
    } finally {
      setSaving(false);
    }
  }

  function handleStopChange(routeIndex, stopIndex, field, value) {
    const updated = [...routes];
    const stops = [...updated[routeIndex].stops];
    stops[stopIndex] = { ...stops[stopIndex], [field]: value };
    updated[routeIndex] = { ...updated[routeIndex], stops };
    setRoutes(updated);
  }

  function handleStopPhoto(routeIndex, stopIndex, file) {
    const updated = [...routes];
    const stops = [...updated[routeIndex].stops];
    stops[stopIndex] = {
      ...stops[stopIndex],
      _photoFile: file,
      _photoPreview: URL.createObjectURL(file),
    };
    updated[routeIndex] = { ...updated[routeIndex], stops };
    setRoutes(updated);
  }

  function addStop(routeIndex) {
    const updated = [...routes];
    const stops = [...(updated[routeIndex].stops || [])];
    stops.push({ name: "", description: "", photo: null, order: stops.length });
    updated[routeIndex] = { ...updated[routeIndex], stops };
    setRoutes(updated);
  }

  async function deleteStop(routeIndex, stopIndex) {
    const stop = routes[routeIndex].stops[stopIndex];

    try {
      if (stop.id) {
        const res = await fetchWithAuth(`/api/hiking/stops/${stop.id}/`, {
          method: "DELETE",
        });

        if (!res.ok && res.status !== 204) {
          const errorText = await res.text();
          openModal({
            title: "Delete failed",
            message: errorText || "Failed to delete stop.",
            type: "danger",
            onConfirm: closeModal,
          });
          return;
        }
      }

      setRoutes((prev) => {
        const updated = [...prev];
        updated[routeIndex] = {
          ...updated[routeIndex],
          stops: updated[routeIndex].stops.filter((_, i) => i !== stopIndex),
        };
        return updated;
      });

      openModal({
        title: "Success",
        message: "Stop deleted successfully.",
        type: "success",
        onConfirm: closeModal,
      });
    } catch (error) {
      openModal({
        title: "Connection error",
        message: error.message || "Server is unreachable.",
        type: "danger",
        onConfirm: closeModal,
      });
    }
  }
  function confirmDeleteStop(routeIndex, stopIndex) {
    openModal({
      title: "Delete stop",
      message: "Delete this stop?",
      type: "danger",
      onConfirm: async () => {
        closeModal();
        await deleteStop(routeIndex, stopIndex);
      },
    });
  }

  async function saveStop(stop, routeId) {
    const fd = new FormData();
    fd.append("name", stop.name || "");
    fd.append("description", stop.description || "");
    fd.append("order", stop.order ?? 0);
    fd.append("route", routeId);
    if (stop._photoFile) fd.append("photo", stop._photoFile);
    if (stop.id) {
      return fetchWithAuth(`/api/hiking/stops/${stop.id}/`, {
        method: "PATCH",
        body: fd,
      });
    } else {
      return fetchWithAuth(`/api/hiking/stops/`, { method: "POST", body: fd });
    }
  }

  async function saveAllStops(routeIndex) {
    const route = routes[routeIndex];

    if (!route.id) {
      openModal({
        title: "Route required",
        message: "Save the route first before adding stops.",
        type: "danger",
        onConfirm: closeModal,
      });
      return;
    }

    setSaving(true);

    try {
      const results = await Promise.all(
        route.stops.map((s) => saveStop(s, route.id))
      );

      for (const res of results) {
        if (!res.ok) {
          const errorText = await res.text();
          openModal({
            title: "Save failed",
            message: errorText || "Failed to save stops.",
            type: "danger",
            onConfirm: closeModal,
          });
          return;
        }
      }

      const updatedStops = await Promise.all(results.map((r) => r.json()));
      const updated = [...routes];
      updated[routeIndex] = { ...updated[routeIndex], stops: updatedStops };
      setRoutes(updated);
      setSavedRoute(`stops-${routeIndex}`);

      openModal({
        title: "Success",
        message: "Stops saved successfully.",
        type: "success",
        onConfirm: closeModal,
      });
    } catch (error) {
      openModal({
        title: "Connection error",
        message: error.message || "Server is unreachable.",
        type: "danger",
        onConfirm: closeModal,
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={styles.container}>
      <Link to="/admin-panel/edit-web-info" className={styles.backButton}>
        ← BACK
      </Link>
      <Title text="Edit Hiking" />

      {loading ? (
        <Loader />
      ) : (
        <div className={styles.fadeIn}>
          {error && <p className={styles.error}>{error}</p>}

          {routes.length === 0 && (
            <p className={styles.emptyMsg} style={{ marginTop: 24 }}>
              No routes added yet.
            </p>
          )}

          {routes.map((route, ri) => (
            <section key={route.id ?? `new-${ri}`} className={styles.section}>
              <div className={styles.routeHeader}>
                <h2 className={styles.sectionTitle}>
                  {route.name || `Route ${ri + 1}`}
                </h2>
                <button
                  type="button"
                  className={styles.deleteButton}
                  onClick={() => confirmDeleteRoute(ri)}
                >
                  ✕ DELETE ROUTE
                </button>
              </div>

              <div className={styles.field}>
                <label>Route Name</label>
                <input
                  value={route.name || ""}
                  onChange={(e) =>
                    handleRouteChange(ri, "name", e.target.value)
                  }
                />
              </div>

              <div className={styles.field}>
                <label>Way Description</label>
                <textarea
                  rows={4}
                  value={route.way_description || ""}
                  onChange={(e) =>
                    handleRouteChange(ri, "way_description", e.target.value)
                  }
                />
              </div>

              <div className={styles.field}>
                <label>Map URL</label>
                <small className={styles.hint}>
                  Link to Google Maps or any map service
                </small>
                <input
                  type="url"
                  value={route.map_url || ""}
                  onChange={(e) =>
                    handleRouteChange(ri, "map_url", e.target.value)
                  }
                  placeholder="https://..."
                />
              </div>

              <div className={styles.actions}>
                {savedRoute === ri && (
                  <span className={styles.savedMsg}>✓ Route saved</span>
                )}
                <button
                  type="button"
                  className={styles.saveButton}
                  onClick={() => saveRoute(ri)}
                  disabled={saving}
                >
                  {saving ? "Saving..." : "SAVE ROUTE"}
                </button>
              </div>

              <div className={styles.stopsBlock}>
                <h3 className={styles.stopsTitle}>Stops</h3>

                {!route.id && (
                  <p className={styles.hint}>
                    Save the route first to add stops.
                  </p>
                )}
                {route.id && (route.stops || []).length === 0 && (
                  <p className={styles.emptyMsg}>No stops added yet.</p>
                )}

                {route.id &&
                  (route.stops || []).map((stop, si) => (
                    <div
                      key={stop.id ?? `new-stop-${si}`}
                      className={styles.stopRow}
                    >
                      <div className={styles.photoCol}>
                        {stop._photoPreview ? (
                          <img
                            src={stop._photoPreview}
                            alt="preview"
                            className={styles.stopPhoto}
                          />
                        ) : stop.photo ? (
                          <img
                            src={buildMediaUrl(stop.photo)}
                            alt={stop.name}
                            className={styles.stopPhoto}
                          />
                        ) : (
                          <div className={styles.photoPlaceholder} />
                        )}
                        <label className={styles.photoLabel}>
                          Change photo
                          <input
                            type="file"
                            accept="image/*"
                            onChange={(e) =>
                              handleStopPhoto(ri, si, e.target.files[0])
                            }
                            className={styles.fileInputHidden}
                          />
                        </label>
                      </div>

                      <div className={styles.stopFields}>
                        <div className={styles.row}>
                          <div className={styles.field}>
                            <label>Stop Name</label>
                            <input
                              value={stop.name || ""}
                              onChange={(e) =>
                                handleStopChange(ri, si, "name", e.target.value)
                              }
                            />
                          </div>
                          <div className={styles.field}>
                            <label>Order</label>
                            <input
                              type="number"
                              value={stop.order ?? si}
                              onChange={(e) =>
                                handleStopChange(
                                  ri,
                                  si,
                                  "order",
                                  e.target.value
                                )
                              }
                              style={{ maxWidth: 80 }}
                            />
                          </div>
                        </div>
                        <div className={styles.field}>
                          <label>Description</label>
                          <textarea
                            rows={2}
                            value={stop.description || ""}
                            onChange={(e) =>
                              handleStopChange(
                                ri,
                                si,
                                "description",
                                e.target.value
                              )
                            }
                          />
                        </div>
                      </div>

                      <button
                        type="button"
                        className={styles.deleteButtonSmall}
                        onClick={() => confirmDeleteStop(ri, si)}
                      >
                        ✕
                      </button>
                    </div>
                  ))}

                {route.id && (
                  <div className={styles.personActions}>
                    <button
                      type="button"
                      className={styles.addButton}
                      onClick={() => addStop(ri)}
                    >
                      + ADD STOP
                    </button>
                    <div className={styles.saveRow}>
                      {savedRoute === `stops-${ri}` && (
                        <span className={styles.savedMsg}>✓ Stops saved</span>
                      )}
                      <button
                        type="button"
                        className={styles.saveButton}
                        onClick={() => saveAllStops(ri)}
                        disabled={saving}
                      >
                        {saving ? "Saving..." : "SAVE STOPS"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </section>
          ))}

          <div style={{ marginTop: 24 }}>
            <button
              type="button"
              className={styles.addButton}
              onClick={addRoute}
            >
              + ADD ROUTE
            </button>
          </div>
        </div>
      )}
      <Modal
        isOpen={modal.isOpen}
        title={modal.title}
        message={modal.message}
        type={modal.type}
        onConfirm={modal.onConfirm}
        onCancel={closeModal}
      />
    </div>
  );
}
