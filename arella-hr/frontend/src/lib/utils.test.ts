import { describe, it, expect } from "vitest";
import { cn } from "./utils";

describe("cn", () => {
  it("joins simple class names", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("ignores falsy values", () => {
    expect(cn("a", undefined, null, false, "", "b")).toBe("a b");
  });

  it("supports conditional objects and arrays", () => {
    expect(cn("base", { active: true, hidden: false }, ["extra"])).toBe("base active extra");
  });

  it("merges conflicting tailwind classes (last wins)", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
    expect(cn("text-red-500", "text-blue-500")).toBe("text-blue-500");
  });

  it("keeps independent classes when merging", () => {
    expect(cn("flex items-center", "justify-end")).toBe("flex items-center justify-end");
  });
});
