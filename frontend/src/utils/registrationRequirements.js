import { allowedContributionTypes } from "./contributionTypes";

export function registrationRequirements(info) {
  const allowedTypes = allowedContributionTypes(info).map((type) => type.value);
  const allowsTalk = allowedTypes.includes("talk");
  const allowsPoster = allowedTypes.includes("poster");

  const requirements = ["Name", "Your e-mail", "Affiliation"];

  if (allowedTypes.length > 1) {
    requirements.push("Participation type");
  }

  if (allowsTalk && allowsPoster) {
    requirements.push("Title and abstract of your talk or poster");
  } else if (allowsTalk) {
    requirements.push("Title and abstract of your talk");
  } else if (allowsPoster) {
    requirements.push("Title and abstract of your poster");
  }

  if (info?.registration_collect_dates !== false) {
    requirements.push("Arrival and departure dates");
  }

  return requirements;
}
