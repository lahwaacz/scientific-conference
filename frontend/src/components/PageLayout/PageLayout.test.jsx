import { render } from "@testing-library/react";
import { setTestLocation } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import PageLayout from "./PageLayout";

describe("PageLayout", () => {
  beforeEach(() => {
    setTestLocation({ pathname: "/", search: "" });
  });

  it("uses the unpadded Home layout on /", () => {
    const { container } = render(
      <PageLayout>
        <div>Home</div>
      </PageLayout>
    );

    expect(container.firstChild.className).toMatch(/home/);
  });

  it("uses the padded page layout on a non-Home route", () => {
    setTestLocation({ pathname: "/program", search: "" });

    const { container } = render(
      <PageLayout>
        <div>Program</div>
      </PageLayout>
    );

    expect(container.firstChild.className).toMatch(/page/);
  });

  it("treats a search string on / as Home", () => {
    setTestLocation({ pathname: "/", search: "?tab=info" });

    const { container } = render(
      <PageLayout>
        <div>Home</div>
      </PageLayout>
    );

    expect(container.firstChild.className).toMatch(/home/);
  });
});
