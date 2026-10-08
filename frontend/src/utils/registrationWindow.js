/**
 * Registration window: [registration_opening, registration_deadline],
 * each bound optional. Dates are "YYYY-MM-DD" strings, so bounds compare
 * lexicographically. A conference whose date_end has passed always has
 * closed registration. Returns "open" | "not-open" | "closed" (the
 * deadline has passed) | "ended" (the conference itself is over);
 * no bounds on an unended conference means open; a null info behaves
 * the same way, so callers that need a distinct loading state must
 * check for it themselves.
 */
// Local (not UTC) calendar date as "YYYY-MM-DD".
function localDateStr(date) {
  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
}

// Previous day of a "YYYY-MM-DD" string, in the same format; UTC-only
// arithmetic so no timezone can drift the calendar date.
function dayBefore(dateStr) {
  const [y, m, d] = dateStr.split("-").map(Number);
  const date = new Date(Date.UTC(y, m - 1, d));
  date.setUTCDate(date.getUTCDate() - 1);
  return [
    date.getUTCFullYear(),
    String(date.getUTCMonth() + 1).padStart(2, "0"),
    String(date.getUTCDate()).padStart(2, "0"),
  ].join("-");
}

export function registrationWindowStatus(info, today = new Date()) {
  const todayStr = localDateStr(today);

  if (info?.registration_opening && todayStr < info.registration_opening) {
    return "not-open";
  }
  if (info?.registration_deadline && todayStr > info.registration_deadline) {
    return "closed";
  }
  if (info?.date_end && todayStr > info.date_end) {
    return "ended";
  }
  return "open";
}

/**
 * Effective submission-editing deadline as a "YYYY-MM-DD" string:
 * the explicit `submission_edit_deadline`, else the day before
 * `date_start`, else `date_end`; it is always capped at `date_end`
 * (the conference end date ends editing). Null when none of the
 * three is set (editing never closes).
 */
export function submissionEditEffectiveDeadline(info) {
  let deadline = null;
  if (info?.submission_edit_deadline) deadline = info.submission_edit_deadline;
  else if (info?.date_start) deadline = dayBefore(info.date_start);
  if (info?.date_end && (deadline === null || info.date_end < deadline)) {
    deadline = info.date_end;
  }
  return deadline;
}

/**
 * Submission-editing window, independent of the registration window.
 * Editing closes after the effective deadline: an explicit
 * `submission_edit_deadline` when set, otherwise the day before
 * `date_start`; with neither set, editing stays open until
 * `date_end`. The deadline is always capped at `date_end` — the
 * conference end date ends editing even when a later explicit
 * deadline is set. Registration closing never blocks an edit.
 * Returns "open" | "closed".
 */
export function submissionEditWindowStatus(info, today = new Date()) {
  const deadline = submissionEditEffectiveDeadline(info);
  if (deadline && localDateStr(today) > deadline) return "closed";
  return "open";
}
