/**
 * Registration window: [registration_opening, registration_deadline],
 * each bound optional. Dates are "YYYY-MM-DD" strings, so bounds compare
 * lexicographically. A conference whose date_end has passed always has
 * closed registration. Returns "open" | "not-open" | "closed"; no bounds
 * (or no info yet) on an unended conference means open.
 */
export function registrationWindowStatus(info, today = new Date()) {
  const todayStr = [
    today.getFullYear(),
    String(today.getMonth() + 1).padStart(2, "0"),
    String(today.getDate()).padStart(2, "0"),
  ].join("-");

  if (info?.registration_opening && todayStr < info.registration_opening) {
    return "not-open";
  }
  if (info?.registration_deadline && todayStr > info.registration_deadline) {
    return "closed";
  }
  if (info?.date_end && todayStr > info.date_end) {
    return "closed";
  }
  return "open";
}
