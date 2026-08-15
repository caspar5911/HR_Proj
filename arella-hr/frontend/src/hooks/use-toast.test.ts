import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  toast,
  pushToast,
  dismissToast,
  clearToasts,
  getToasts,
} from "./use-toast";

describe("toast store", () => {
  beforeEach(() => {
    clearToasts();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("toast.success pushes a success toast with a unique id", () => {
    const id1 = toast.success("Saved");
    const id2 = toast.error("Failed");
    const items = getToasts();
    expect(items).toHaveLength(2);
    expect(items[0]).toMatchObject({ id: id1, title: "Saved", variant: "success" });
    expect(items[1]).toMatchObject({ id: id2, title: "Failed", variant: "error" });
    expect(id1).not.toBe(id2);
  });

  it("toast.info sets variant info and an optional description", () => {
    toast.info("Heads up", "details here");
    expect(getToasts()[0]).toMatchObject({
      title: "Heads up",
      description: "details here",
      variant: "info",
    });
  });

  it("pushToast defaults variant to default", () => {
    pushToast({ title: "Plain" });
    expect(getToasts()[0].variant).toBe("default");
  });

  it("dismissToast removes only the given toast", () => {
    const a = toast.success("A");
    const b = toast.success("B");
    dismissToast(a);
    expect(getToasts()).toHaveLength(1);
    expect(getToasts()[0].id).toBe(b);
  });

  it("dismissToast is a no-op for unknown ids", () => {
    toast.success("A");
    dismissToast(99999);
    expect(getToasts()).toHaveLength(1);
  });

  it("auto-dismisses after 4 seconds", () => {
    toast.success("Temporary");
    expect(getToasts()).toHaveLength(1);
    vi.advanceTimersByTime(3999);
    expect(getToasts()).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(getToasts()).toHaveLength(0);
  });

  it("clearToasts empties the list", () => {
    toast.success("A");
    toast.error("B");
    clearToasts();
    expect(getToasts()).toHaveLength(0);
  });
});
