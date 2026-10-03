import {
  clearProgramDirty,
  isProgramDirty,
  markProgramDirty,
} from "./programRefresh";

describe("programRefresh dirty flag", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test("is false before anything is marked", () => {
    expect(isProgramDirty()).toBe(false);
  });

  test("is true after markProgramDirty", () => {
    markProgramDirty();
    expect(isProgramDirty()).toBe(true);
    expect(localStorage.getItem("program_needs_refresh")).not.toBeNull();
  });

  test("is false again after clearProgramDirty", () => {
    markProgramDirty();
    clearProgramDirty();
    expect(isProgramDirty()).toBe(false);
  });
});
