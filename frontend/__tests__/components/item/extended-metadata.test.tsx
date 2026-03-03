import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ExtendedMetadata } from "@/components/item/extended-metadata";

describe("ExtendedMetadata", () => {
  it("renders nothing when no relevant metadata is present", () => {
    const { container } = render(<ExtendedMetadata meta={{}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders categories when present", () => {
    render(<ExtendedMetadata meta={{ Categories: ["Sci-Fi", "Thriller"] }} />);
    expect(screen.getByText("Sci-Fi")).toBeInTheDocument();
    expect(screen.getByText("Thriller")).toBeInTheDocument();
  });

  it("renders description when present", () => {
    const desc = "This is a test description.";
    render(<ExtendedMetadata meta={{ Description: desc }} />);
    expect(screen.getByText(desc)).toBeInTheDocument();
  });

  it("renders additional details in a collapsible section", () => {
    const meta = {
      Publisher: "Test Publisher",
      Language: "English",
      // These keys should be hidden by default logic in the component
      Title: "Hidden Title",
      Year: "2023",
      cover_status: "ready"
    };

    render(<ExtendedMetadata meta={meta} />);

    // Initially hidden
    expect(screen.queryByText("Test Publisher")).not.toBeInTheDocument();

    // Expand
    const button = screen.getByText("Additional Details");
    fireEvent.click(button);

    // Now visible
    expect(screen.getByText("Test Publisher")).toBeInTheDocument();
    expect(screen.getByText("Language")).toBeInTheDocument();
    expect(screen.getByText("English")).toBeInTheDocument();

    // Hidden keys should remain hidden even when expanded
    expect(screen.queryByText("Hidden Title")).not.toBeInTheDocument();
  });
});
