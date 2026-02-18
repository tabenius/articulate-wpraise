"use client";

import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";

type SplitDirection = "horizontal" | "vertical";

interface SplitViewProps {
  left: React.ReactNode;
  right: React.ReactNode;
  direction?: SplitDirection;
  defaultSize?: number;
  leftId?: string;
  rightId?: string;
}

export function SplitView({
  left,
  right,
  direction = "horizontal",
  defaultSize = 50,
  leftId = "left-panel",
  rightId = "right-panel",
}: SplitViewProps) {
  const isHorizontal = direction === "horizontal";

  return (
    <PanelGroup direction={direction} className="h-full">
      <Panel
        defaultSize={defaultSize}
        minSize={25}
        maxSize={75}
        id={leftId}
        order={1}
      >
        {left}
      </Panel>

      <PanelResizeHandle
        className={`bg-border hover:bg-primary/20 transition-colors group ${
          isHorizontal
            ? "w-1 cursor-col-resize"
            : "h-1 cursor-row-resize"
        }`}
      >
        <div className="w-full h-full flex items-center justify-center">
          <div
            className={`bg-border group-hover:bg-primary/40 rounded-full transition-colors ${
              isHorizontal ? "w-0.5 h-8" : "h-0.5 w-8"
            }`}
          />
        </div>
      </PanelResizeHandle>

      <Panel
        defaultSize={100 - defaultSize}
        minSize={25}
        id={rightId}
        order={2}
      >
        {right}
      </Panel>
    </PanelGroup>
  );
}
