"use client";

import type { BlockProps, SeparatorAttributes } from "@/types/blocks";
import { Separator } from "@/components/ui/separator";

export function SeparatorBlock({
  isSelected,
}: BlockProps<SeparatorAttributes>) {
  return (
    <div
      className={`py-2 ${isSelected ? "ring-2 ring-primary/20 rounded" : ""}`}
    >
      <Separator />
    </div>
  );
}
