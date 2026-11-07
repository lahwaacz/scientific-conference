export function formatFieldErrors(payload) {
  if (!payload || typeof payload !== "object") return "";
  return Object.entries(payload)
    .map(([field, value]) => {
      const message = Array.isArray(value) ? value.join(" ") : String(value);
      return field === "non_field_errors" ? message : `${field}: ${message}`;
    })
    .join("\n");
}
