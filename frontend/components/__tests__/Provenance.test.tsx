import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Provenance from "../Provenance";

describe("Provenance", () => {
  it("renders source name and link", () => {
    render(
      <Provenance
        sourceName="Test Legal Organ"
        sourceUrl="https://example.com/notice/1"
        retrievedAt="2026-10-15T12:00:00Z"
      />,
    );
    expect(screen.getByText(/Test Legal Organ/)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /View source/ });
    expect(link).toHaveAttribute("href", "https://example.com/notice/1");
  });

  it("renders nothing when no source is available", () => {
    const { container } = render(<Provenance />);
    expect(container).toBeEmptyDOMElement();
  });
});
