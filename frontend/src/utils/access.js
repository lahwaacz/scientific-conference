export function canManageConference(user, slug) {
  if (!user) {
    return false;
  }
  if (user.is_superuser) {
    return true;
  }
  if (!slug) {
    return false;
  }
  return (user.managed_conferences ?? []).includes(slug);
}
