"use client";

import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { useState } from "react";
import { ArrowLeftRight, ArrowUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";

type SplitDirection = "horizontal" | "vertical";

interface MultiSplitViewProps {
  top: React.ReactNode;
  bottom: React.ReactNode;
  initialDirection?: SplitDirection;
  showDirectionToggle?: boolean;
}

/**
 * Advanced split view that supports toggling between horizontal and vertical layouts
 */
export function MultiSplitView({
  top,
  bottom,
  initialDirection = "horizontal",
  showDirectionToggle = true,
}: MultiSplitViewProps) {
  const [direction, setDirection] = useState<SplitDirection>(initialDirection);

  const toggleDirection = () => {
    setDirection((prev) => (prev === "horizontal" ? "vertical" : "horizontal"));
  };

  const isHorizontal = direction === "horizontal";

  return (
    <div className="relative h-full w-full">
      {showDirectionToggle && (
        <div className="absolute top-2 right-2 z-10">
          <Button
            variant="outline"
            size="sm"
            onClick={toggleDirection}
            title={`Switch to ${isHorizontal ? "vertical" : "horizontal"} split`}
          >
            {isHorizontal ? (
              <ArrowUpDown className="h-4 w-4" />
            ) : (
              <ArrowLeftRight className="h-4 w-4" />
            )}
            <span className="ml-2 hidden sm:inline">
              {isHorizontal ? "Vertical" : "Horizontal"}
            </span>
          </Button>
        </div>
      )}

      <PanelGroup direction={direction} className="h-full">
        <Panel defaultSize={50} minSize={25} maxSize={75} id="top-panel" order={1}>
          {top}
        </Panel>

        <PanelResizeHandle
          className={`bg-border hover:bg-primary/20 transition-colors group ${
            isHorizontal ? "w-1 cursor-col-resize" : "h-1 cursor-row-resize"
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

        <Panel defaultSize={50} minSize={25} id="bottom-panel" order={2}>
          {bottom}
        </Panel>
      </PanelGroup>
    </div>
  );
}

interface NestedSplitViewProps {
  topLeft: React.ReactNode;
  topRight: React.ReactNode;
  bottom: React.ReactNode;
  topSplit?: number;
  bottomSplit?: number;
}

/**
 * Nested split view: horizontal split at top, full-width panel at bottom
 * Perfect for: editor + preview on top, console/chat at bottom
 */
export function NestedSplitView({
  topLeft,
  topRight,
  bottom,
  topSplit = 50,
  bottomSplit = 70,
}: NestedSplitViewProps) {
  return (
    <PanelGroup direction="vertical" className="h-full">
      {/* Top section with horizontal split */}
      <Panel defaultSize={bottomSplit} minSize={30} id="top-section" order={1}>
        <PanelGroup direction="horizontal">
          <Panel defaultSize={topSplit} minSize={25} maxSize={75} id="top-left" order={1}>
            {topLeft}
          </Panel>

          <PanelResizeHandle className="w-1 bg-border hover:bg-primary/20 transition-colors cursor-col-resize group">
            <div className="w-full h-full flex items-center justify-center">
              <div className="w-0.5 h-8 bg-border group-hover:bg-primary/40 rounded-full transition-colors" />
            </div>
          </PanelResizeHandle>

          <Panel defaultSize={100 - topSplit} minSize={25} id="top-right" order={2}>
            {topRight}
          </Panel>
        </PanelGroup>
      </Panel>

      {/* Vertical resize handle */}
      <PanelResizeHandle className="h-1 bg-border hover:bg-primary/20 transition-colors cursor-row-resize group">
        <div className="w-full h-full flex items-center justify-center">
          <div className="h-0.5 w-8 bg-border group-hover:bg-primary/40 rounded-full transition-colors" />
        </div>
      </PanelResizeHandle>

      {/* Bottom section */}
      <Panel defaultSize={100 - bottomSplit} minSize={15} id="bottom-section" order={2}>
        {bottom}
      </Panel>
    </PanelGroup>
  );
}
