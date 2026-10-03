export function markProgramDirty() {
  localStorage.setItem("program_needs_refresh", Date.now().toString());
}

export function clearProgramDirty() {
  localStorage.removeItem("program_needs_refresh");
}

export function isProgramDirty() {
  return !!localStorage.getItem("program_needs_refresh");
}
