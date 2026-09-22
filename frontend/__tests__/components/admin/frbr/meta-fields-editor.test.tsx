// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>
//
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MetaFieldsEditor, EditableKeyField } from "@/components/admin/frbr/meta-fields-editor";

describe("EditableKeyField", () => {
  it("renders the formatted key value", () => {
    render(<EditableKeyField value="original_language" onChange={vi.fn()} />);
    expect(screen.getByText("Original Language")).toBeInTheDocument();
  });

  it("renders edit button", () => {
    render(<EditableKeyField value="pages" onChange={vi.fn()} />);
    expect(screen.getByTestId("edit-key-button")).toBeInTheDocument();
  });

  it("switches to edit mode when pencil is clicked", () => {
    render(<EditableKeyField value="pages" onChange={vi.fn()} />);
    fireEvent.click(screen.getByTestId("edit-key-button"));
    expect(screen.getByTestId("editable-key-input")).toBeInTheDocument();
  });

  it("saves on Enter key press", () => {
    const onChange = vi.fn();
    render(<EditableKeyField value="pages" onChange={onChange} />);
    fireEvent.click(screen.getByTestId("edit-key-button"));
    const input = screen.getByTestId("editable-key-input");
    fireEvent.change(input, { target: { value: "new_key" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith("new_key");
  });

  it("cancels on Escape key press", () => {
    const onChange = vi.fn();
    render(<EditableKeyField value="pages" onChange={onChange} />);
    fireEvent.click(screen.getByTestId("edit-key-button"));
    const input = screen.getByTestId("editable-key-input");
    fireEvent.change(input, { target: { value: "new_key" } });
    fireEvent.keyDown(input, { key: "Escape" });
    expect(onChange).not.toHaveBeenCalled();
    // Should return to display mode
    expect(screen.queryByTestId("editable-key-input")).not.toBeInTheDocument();
  });

  it("saves on blur", () => {
    const onChange = vi.fn();
    render(<EditableKeyField value="pages" onChange={onChange} />);
    fireEvent.click(screen.getByTestId("edit-key-button"));
    const input = screen.getByTestId("editable-key-input");
    fireEvent.change(input, { target: { value: "updated_key" } });
    fireEvent.blur(input);
    expect(onChange).toHaveBeenCalledWith("updated_key");
  });

  it("displays 'Key' when value is empty", () => {
    render(<EditableKeyField value="" onChange={vi.fn()} />);
    expect(screen.getByText("Key")).toBeInTheDocument();
  });
});

describe("MetaFieldsEditor", () => {
  it("renders the Dynamic Metadata heading", () => {
    render(<MetaFieldsEditor fields={[]} onChange={vi.fn()} />);
    expect(screen.getByText("Dynamic Metadata")).toBeInTheDocument();
  });

  it("renders existing fields", () => {
    const fields = [
      { key: "pages", value: "412" },
      { key: "type", value: "Book" },
    ];
    render(<MetaFieldsEditor fields={fields} onChange={vi.fn()} />);
    expect(screen.getByDisplayValue("412")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Book")).toBeInTheDocument();
  });

  it("renders Add Field button", () => {
    render(<MetaFieldsEditor fields={[]} onChange={vi.fn()} />);
    expect(screen.getByTestId("add-meta-field")).toBeInTheDocument();
  });

  it("calls onChange with new field when Add Field is clicked", () => {
    const onChange = vi.fn();
    render(<MetaFieldsEditor fields={[{ key: "pages", value: "412" }]} onChange={onChange} />);
    fireEvent.click(screen.getByTestId("add-meta-field"));
    expect(onChange).toHaveBeenCalledWith([
      { key: "pages", value: "412" },
      { key: "", value: "" },
    ]);
  });

  it("calls onChange when value input changes", () => {
    const onChange = vi.fn();
    const fields = [{ key: "pages", value: "412" }];
    render(<MetaFieldsEditor fields={fields} onChange={onChange} />);
    fireEvent.change(screen.getByTestId("meta-value-0"), { target: { value: "500" } });
    expect(onChange).toHaveBeenCalledWith([{ key: "pages", value: "500" }]);
  });

  it("calls onChange when remove button is clicked", () => {
    const onChange = vi.fn();
    const fields = [
      { key: "pages", value: "412" },
      { key: "type", value: "Book" },
    ];
    render(<MetaFieldsEditor fields={fields} onChange={onChange} />);
    fireEvent.click(screen.getByTestId("remove-meta-0"));
    expect(onChange).toHaveBeenCalledWith([{ key: "type", value: "Book" }]);
  });

  it("calls onChange with updated key when EditableKeyField changes", () => {
    const onChange = vi.fn();
    const fields = [{ key: "pages", value: "412" }];
    render(<MetaFieldsEditor fields={fields} onChange={onChange} />);
    // Click the edit button for the key
    fireEvent.click(screen.getByTestId("edit-key-button"));
    const input = screen.getByTestId("editable-key-input");
    fireEvent.change(input, { target: { value: "page_count" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith([{ key: "page_count", value: "412" }]);
  });

  it("renders empty state with just the Add Field button", () => {
    render(<MetaFieldsEditor fields={[]} onChange={vi.fn()} />);
    expect(screen.queryByTestId("meta-value-0")).not.toBeInTheDocument();
    expect(screen.getByTestId("add-meta-field")).toBeInTheDocument();
  });

  it("renders multiple fields with correct indices", () => {
    const fields = [
      { key: "a", value: "1" },
      { key: "b", value: "2" },
      { key: "c", value: "3" },
    ];
    render(<MetaFieldsEditor fields={fields} onChange={vi.fn()} />);
    expect(screen.getByTestId("meta-value-0")).toHaveValue("1");
    expect(screen.getByTestId("meta-value-1")).toHaveValue("2");
    expect(screen.getByTestId("meta-value-2")).toHaveValue("3");
    expect(screen.getByTestId("remove-meta-0")).toBeInTheDocument();
    expect(screen.getByTestId("remove-meta-1")).toBeInTheDocument();
    expect(screen.getByTestId("remove-meta-2")).toBeInTheDocument();
  });
});
