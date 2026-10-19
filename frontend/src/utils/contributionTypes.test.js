import {
  allowedContributionTypes,
  contributionTypeLabel,
  defaultContributionType,
} from "./contributionTypes";

describe("contributionTypes", () => {
  test("defaults to all three types when the backend sends no flags", () => {
    expect(allowedContributionTypes({}).map(({ value }) => value)).toEqual([
      "talk",
      "poster",
      "attend",
    ]);
    expect(defaultContributionType({})).toBe("talk");
  });

  test("filters by the conference flags and defaults to Talk first", () => {
    const info = {
      registration_allow_talk: false,
      registration_allow_poster: true,
      registration_allow_attend: true,
    };

    expect(allowedContributionTypes(info).map(({ value }) => value)).toEqual([
      "poster",
      "attend",
    ]);
    expect(defaultContributionType(info)).toBe("poster");
  });

  test("keeps a submission's current type selectable after it is disabled", () => {
    const info = {
      registration_allow_talk: true,
      registration_allow_poster: false,
      registration_allow_attend: false,
    };

    expect(
      allowedContributionTypes(info, "poster").map(({ value }) => value)
    ).toEqual(["talk", "poster"]);
  });

  test("labels known values and falls back to the raw value", () => {
    expect(contributionTypeLabel("attend")).toBe("Just attend");
    expect(contributionTypeLabel("unknown")).toBe("unknown");
  });
});
