export const CONTRIBUTION_TYPES = [
  { value: "talk", label: "Talk" },
  { value: "poster", label: "Poster" },
  { value: "attend", label: "Just attend" },
];

export function allowedContributionTypes(info, current = null) {
  const hasFlags = CONTRIBUTION_TYPES.some(
    ({ value }) => info?.[`registration_allow_${value}`] !== undefined
  );
  const allowed = hasFlags
    ? CONTRIBUTION_TYPES.filter(
        ({ value }) => info[`registration_allow_${value}`] !== false
      )
    : CONTRIBUTION_TYPES;

  if (current && !allowed.some(({ value }) => value === current)) {
    const currentType = CONTRIBUTION_TYPES.find(
      ({ value }) => value === current
    );
    if (currentType) return [...allowed, currentType];
  }
  return allowed;
}

export function defaultContributionType(info) {
  const allowed = allowedContributionTypes(info);
  return allowed.some(({ value }) => value === "talk")
    ? "talk"
    : (allowed[0]?.value ?? "talk");
}

export function contributionTypeLabel(value) {
  return (
    CONTRIBUTION_TYPES.find((type) => type.value === value)?.label ?? value
  );
}
