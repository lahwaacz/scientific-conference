import { getConferenceSlug } from "./conferenceSlug";

function dirtyFlagKey() {
  return `program_needs_refresh_${getConferenceSlug() ?? "global"}`;
}

export function markProgramDirty() {
  localStorage.setItem(dirtyFlagKey(), Date.now().toString());
}

export function clearProgramDirty() {
  localStorage.removeItem(dirtyFlagKey());
}

export function isProgramDirty() {
  return !!localStorage.getItem(dirtyFlagKey());
}
