export function conferenceTitle(info) {
  return [info?.title, info?.year].filter(Boolean).join(" ");
}
