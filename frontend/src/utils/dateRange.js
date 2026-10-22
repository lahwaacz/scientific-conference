const DATE_ONLY_RE = /^(\d{4})-(\d{2})-(\d{2})$/;

function parseDate(dateStr) {
  const match = DATE_ONLY_RE.exec(dateStr);
  if (!match) {
    return new Date(dateStr);
  }
  const [, year, month, day] = match;
  return new Date(Number(year), Number(month) - 1, Number(day));
}

function formatDate(dateStr) {
  const d = parseDate(dateStr);
  return d.toLocaleDateString("en-GB", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

export function formatDateRange(startStr, endStr) {
  const start = parseDate(startStr);
  const end = parseDate(endStr);

  if (
    start.getFullYear() === end.getFullYear() &&
    start.getMonth() === end.getMonth()
  ) {
    const monthYear = start.toLocaleDateString("en-GB", {
      month: "long",
      year: "numeric",
    });
    if (start.getDate() === end.getDate()) {
      return `${start.getDate()} ${monthYear}`;
    }
    return `${start.getDate()}–${end.getDate()} ${monthYear}`;
  }

  return `${formatDate(startStr)} – ${formatDate(endStr)}`;
}
