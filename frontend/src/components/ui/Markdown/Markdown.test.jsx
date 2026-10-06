import { render, screen } from "@testing-library/react";
import Markdown from "./Markdown";

describe("Markdown", () => {
  test("renders nothing without text", () => {
    const { container } = render(<Markdown text="" />);

    expect(container).toBeEmptyDOMElement();
  });

  test("renders commonmark headings, lists and emphasis", () => {
    render(<Markdown text={"## Talks\n\n- first\n- *second*"} />);

    expect(
      screen.getByRole("heading", { level: 2, name: "Talks" })
    ).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText("second").tagName).toBe("EM");
  });

  test("does not render raw HTML from the text as markup", () => {
    const { container } = render(
      <Markdown text={'<script>alert("x")</script>'} />
    );

    expect(container.querySelector("script")).toBeNull();
  });

  test("neutralizes unsafe link targets", () => {
    const { container } = render(
      <Markdown text={"[click](javascript:alert(1))"} />
    );

    const link = container.querySelector("a");
    expect(link?.getAttribute("href") || "").not.toContain("javascript:");
  });
});
