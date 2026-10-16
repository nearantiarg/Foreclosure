import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import EmptyState from "../EmptyState";

// Tests use only static fixture strings — never production data.
describe("EmptyState", () => {
  it("renders the honest empty-state message with last ingestion and source", () => {
    render(<EmptyState lastIngestion="2026-10-15T12:00:00Z" source="test-source" />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    // The phrase appears in both the message and the detail line.
    expect(
      screen.getAllByText(/No verified records ingested yet for this filter/).length,
    ).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/source: test-source/)).toBeInTheDocument();
  });

  it("renders unknown when no ingestion timestamp is available", () => {
    render(<EmptyState lastIngestion={null} source={null} />);
    expect(screen.getByText(/last ingestion: unknown/)).toBeInTheDocument();
  });
});
