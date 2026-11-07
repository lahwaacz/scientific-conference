import { registrationRequirements } from "./registrationRequirements";

const combinations = [
  { label: "talk only", allowed: ["talk"] },
  { label: "poster only", allowed: ["poster"] },
  { label: "attend only", allowed: ["attend"] },
  { label: "talk and poster", allowed: ["talk", "poster"] },
  { label: "talk and attend", allowed: ["talk", "attend"] },
  { label: "poster and attend", allowed: ["poster", "attend"] },
  { label: "all types", allowed: ["talk", "poster", "attend"] },
];

function conferenceInfo(allowed, collectDates) {
  return {
    registration_allow_talk: allowed.includes("talk"),
    registration_allow_poster: allowed.includes("poster"),
    registration_allow_attend: allowed.includes("attend"),
    registration_collect_dates: collectDates,
  };
}

function expectedRequirements(allowed, collectDates) {
  const expected = ["Name", "Your e-mail", "Affiliation"];
  if (allowed.length > 1) expected.push("Participation type");
  if (allowed.includes("talk") && allowed.includes("poster")) {
    expected.push("Title and abstract of your talk or poster");
  } else if (allowed.includes("talk")) {
    expected.push("Title and abstract of your talk");
  } else if (allowed.includes("poster")) {
    expected.push("Title and abstract of your poster");
  }
  if (collectDates) expected.push("Arrival and departure dates");
  return expected;
}

describe("registrationRequirements", () => {
  test.each(combinations)("$label with collected dates", ({ allowed }) => {
    expect(registrationRequirements(conferenceInfo(allowed, true))).toEqual(
      expectedRequirements(allowed, true)
    );
  });

  test.each(combinations)("$label with dates disabled", ({ allowed }) => {
    expect(registrationRequirements(conferenceInfo(allowed, false))).toEqual(
      expectedRequirements(allowed, false)
    );
  });

  test("defaults to all contribution types and collected dates for old payloads", () => {
    expect(registrationRequirements({})).toEqual([
      "Name",
      "Your e-mail",
      "Affiliation",
      "Participation type",
      "Title and abstract of your talk or poster",
      "Arrival and departure dates",
    ]);
  });
});
