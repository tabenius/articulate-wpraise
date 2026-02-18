# Split View Components

Three flexible split view components for building complex layouts.

## 1. SplitView (Enhanced)

Simple two-panel split with configurable direction.

### Features
- ✅ Horizontal or vertical split
- ✅ Resizable panels
- ✅ Customizable default sizes
- ✅ Min/max size constraints

### Usage

```tsx
import { SplitView } from "@/components/layout/split-view";

// Horizontal split (left | right)
<SplitView
  left={<ChatPanel />}
  right={<EditorPanel />}
  direction="horizontal"
  defaultSize={40}
/>

// Vertical split (top / bottom)
<SplitView
  left={<EditorPanel />}
  right={<PreviewPanel />}
  direction="vertical"
  defaultSize={60}
/>
```

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `left` | ReactNode | required | Content for first panel |
| `right` | ReactNode | required | Content for second panel |
| `direction` | "horizontal" \| "vertical" | "horizontal" | Split direction |
| `defaultSize` | number | 50 | Default size of left/top panel (%) |
| `leftId` | string | "left-panel" | Panel ID for persistence |
| `rightId` | string | "right-panel" | Panel ID for persistence |

## 2. MultiSplitView

Two-panel split with toggle button to switch between horizontal and vertical.

### Features
- ✅ Toggle between horizontal/vertical
- ✅ Persistent resize state
- ✅ Optional direction toggle button
- ✅ Smooth transitions

### Usage

```tsx
import { MultiSplitView } from "@/components/layout/multi-split-view";

<MultiSplitView
  top={<EditorPanel />}
  bottom={<PreviewPanel />}
  initialDirection="horizontal"
  showDirectionToggle={true}
/>
```

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `top` | ReactNode | required | Content for first panel |
| `bottom` | ReactNode | required | Content for second panel |
| `initialDirection` | "horizontal" \| "vertical" | "horizontal" | Starting direction |
| `showDirectionToggle` | boolean | true | Show direction toggle button |

## 3. NestedSplitView

Three-panel layout: horizontal split on top, full-width panel on bottom.

### Features
- ✅ Three resizable panels
- ✅ Perfect for editor + preview + console
- ✅ Independent resize controls
- ✅ Customizable split ratios

### Layout

```
┌─────────────┬─────────────┐
│   topLeft   │  topRight   │  ← Horizontal split
│             │             │
├─────────────┴─────────────┤  ← Vertical divider
│         bottom            │  ← Full width
└───────────────────────────┘
```

### Usage

```tsx
import { NestedSplitView } from "@/components/layout/multi-split-view";

<NestedSplitView
  topLeft={<EditorPanel />}
  topRight={<PreviewPanel />}
  bottom={<ChatPanel />}
  topSplit={50}      // 50/50 split on top
  bottomSplit={70}   // Top section is 70% of height
/>
```

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `topLeft` | ReactNode | required | Content for top-left panel |
| `topRight` | ReactNode | required | Content for top-right panel |
| `bottom` | ReactNode | required | Content for bottom panel |
| `topSplit` | number | 50 | Horizontal split ratio (%) |
| `bottomSplit` | number | 70 | Vertical split ratio (%) |

## Common Use Cases

### 1. Chat + Editor (Horizontal)
```tsx
<SplitView
  left={<ChatSidebar />}
  right={<Editor />}
  direction="horizontal"
  defaultSize={40}
/>
```

### 2. Editor + Preview (Vertical)
```tsx
<SplitView
  left={<Editor />}
  right={<Preview />}
  direction="vertical"
  defaultSize={60}
/>
```

### 3. Editor + Preview with Toggle
```tsx
<MultiSplitView
  top={<Editor />}
  bottom={<Preview />}
  showDirectionToggle={true}
/>
```

### 4. Full IDE Layout
```tsx
<NestedSplitView
  topLeft={<Editor />}
  topRight={<Preview />}
  bottom={<ChatConsole />}
  topSplit={60}
  bottomSplit={75}
/>
```

## Styling

All split views use:
- **Resize handles**: 1px border with hover effect
- **Visual indicator**: Rounded pill on hover
- **Smooth transitions**: 200ms ease
- **Accessible cursors**: col-resize / row-resize

## Persistence

Panel sizes are automatically persisted by panel IDs. Customize IDs for multiple instances:

```tsx
<SplitView
  leftId="editor-panel"
  rightId="preview-panel"
  // ... sizes will be saved per ID
/>
```
