export function countWords(text) {
  return text
    .trim()
    .split(/\s+/)
    .filter((w) => w.length > 0).length;
}

export function validateSubmissionForm({ formData, photo }) {
  const errors = {};

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email.trim())) {
    errors.email = "Please enter a valid email";
  }

  if (formData.affiliation.trim().length < 3) {
    errors.affiliation = "Please enter a valid affiliation";
  }

  if (countWords(formData.abstract_text) > 250) {
    errors.abstract_text = "Abstract must not exceed 250 words";
  }

  if (!formData.arrival) {
    errors.arrival = "Please select arrival date";
  }

  if (!formData.departure) {
    errors.departure = "Please select departure date";
  }

  if (
    formData.arrival &&
    formData.departure &&
    formData.departure <= formData.arrival
  ) {
    errors.departure = "Departure date must be after arrival date";
  }

  if (photo && photo.size > 5 * 1024 * 1024) {
    errors.photo = "Photo size must not exceed 5MB";
  }

  return errors;
}
