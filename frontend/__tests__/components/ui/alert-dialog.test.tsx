/**
 * Tests for the AlertDialog UI component.
 *
 * AlertDialog wraps @radix-ui/react-alert-dialog with project styling.
 * The Radix portal renders dialog content to document.body, so we use
 * getByRole / queryByRole to locate it regardless of where it lands in the DOM.
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

/** Minimal confirm dialog that reuses all the named exports. */
function ConfirmDialog({
  open,
  onOpenChange,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
}) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete item?</AlertDialogTitle>
          <AlertDialogDescription>This cannot be undone.</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>Delete</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

describe("AlertDialog", () => {
  it("does not render dialog content when closed", () => {
    render(<ConfirmDialog open={false} onOpenChange={vi.fn()} onConfirm={vi.fn()} />);
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it("renders dialog content when open", () => {
    render(<ConfirmDialog open={true} onOpenChange={vi.fn()} onConfirm={vi.fn()} />);
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
  });

  it("displays title and description when open", () => {
    render(<ConfirmDialog open={true} onOpenChange={vi.fn()} onConfirm={vi.fn()} />);
    expect(screen.getByText("Delete item?")).toBeInTheDocument();
    expect(screen.getByText("This cannot be undone.")).toBeInTheDocument();
  });

  it("calls onConfirm when the action button is clicked", () => {
    const onConfirm = vi.fn();
    render(<ConfirmDialog open={true} onOpenChange={vi.fn()} onConfirm={onConfirm} />);
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("calls onOpenChange(false) when the cancel button is clicked", () => {
    const onOpenChange = vi.fn();
    render(<ConfirmDialog open={true} onOpenChange={onOpenChange} onConfirm={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("disables action and cancel buttons when the disabled prop is set", () => {
    render(
      <AlertDialog open={true} onOpenChange={vi.fn()}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirm deletion</AlertDialogTitle>
            <AlertDialogDescription>This action cannot be undone.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled>Cancel</AlertDialogCancel>
            <AlertDialogAction disabled onClick={vi.fn()}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    );
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Delete" })).toBeDisabled();
  });
});
