// Learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom'

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() {
    return [];
  }
  unobserve() {}
};

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
};

// Mock all shadcn/ui components
jest.mock('@/components/ui/card', () => ({
  Card: ({ children, ...props }) => <div data-testid="card" {...props}>{children}</div>,
  CardHeader: ({ children, ...props }) => <div data-testid="card-header" {...props}>{children}</div>,
  CardTitle: ({ children, ...props }) => <div data-testid="card-title" {...props}>{children}</div>,
  CardDescription: ({ children, ...props }) => <div data-testid="card-description" {...props}>{children}</div>,
  CardContent: ({ children, ...props }) => <div data-testid="card-content" {...props}>{children}</div>,
  CardFooter: ({ children, ...props }) => <div data-testid="card-footer" {...props}>{children}</div>,
}));

jest.mock('@/components/ui/tabs', () => {
  const React = require('react');
  const TabsContext = React.createContext({ value: '', setValue: (v) => {} });

  const Tabs = ({ children, defaultValue, onValueChange, ...props }) => {
    const [value, setValue] = React.useState(defaultValue || '');
    const handleValueChange = (newValue) => {
      setValue(newValue);
      if (onValueChange) onValueChange(newValue);
    };
    return (
      <TabsContext.Provider value={{ value, setValue: handleValueChange }}>
        <div data-testid="tabs" {...props}>{children}</div>
      </TabsContext.Provider>
    );
  };

  const TabsList = ({ children, ...props }) => (
    <div data-testid="tabs-list" role="tablist" {...props}>{children}</div>
  );

  const TabsTrigger = ({ children, value, ...props }) => {
    const context = React.useContext(TabsContext);
    return (
      <button
        data-testid="tabs-trigger"
        role="tab"
        aria-label={value}
        onClick={() => context.setValue(value)}
        aria-selected={context.value === value}
        {...props}
      >
        {children}
      </button>
    );
  };

  const TabsContent = ({ children, value, ...props }) => {
    const context = React.useContext(TabsContext);
    return context.value === value ? (
      <div data-testid="tabs-content" {...props}>{children}</div>
    ) : null;
  };

  return {
    Tabs,
    TabsList,
    TabsTrigger,
    TabsContent,
  };
});

jest.mock('@/components/ui/select', () => {
  const React = require('react');
  return {
    Select: ({ children, onValueChange, defaultValue, value, ...props }) => {
      const [selectValue, setSelectValue] = React.useState(defaultValue || value || '');
      return (
        <div data-testid="select" {...props}>
          {React.Children.map(children, child => {
            if (React.isValidElement(child)) {
              return React.cloneElement(child, { onValueChange, selectValue, setSelectValue });
            }
            return child;
          })}
        </div>
      );
    },
    SelectGroup: ({ children, ...props }) => <div data-testid="select-group" {...props}>{children}</div>,
    SelectValue: ({ children, placeholder, ...props }) => (
      <span data-testid="select-value" {...props}>{children || placeholder}</span>
    ),
    SelectTrigger: ({ children, ...props }) => (
      <button data-testid="select-trigger" role="combobox" {...props}>{children}</button>
    ),
    SelectContent: ({ children, ...props }) => <div data-testid="select-content" {...props}>{children}</div>,
    SelectLabel: ({ children, ...props }) => <div data-testid="select-label" {...props}>{children}</div>,
    SelectItem: ({ children, value, onValueChange, setSelectValue, ...props }) => (
      <div
        data-testid="select-item"
        onClick={() => {
          if (setSelectValue) setSelectValue(value);
          if (onValueChange) onValueChange(value);
        }}
        {...props}
      >
        {children}
      </div>
    ),
    SelectSeparator: (props) => <hr data-testid="select-separator" {...props} />,
  };
});

jest.mock('@/components/ui/badge', () => ({
  Badge: ({ children, ...props }) => <span data-testid="badge" {...props}>{children}</span>,
}));

jest.mock('@/components/ui/scroll-area', () => ({
  ScrollArea: ({ children, ...props }) => <div data-testid="scroll-area" {...props}>{children}</div>,
}));

jest.mock('@/components/ui/button', () => ({
  Button: ({ children, ...props }) => <button data-testid="button" {...props}>{children}</button>,
}));

jest.mock('@/components/ui/input', () => ({
  Input: ({ onValueChange, ...props }) => {
    const handleChange = (e) => {
      if (props.onChange) props.onChange(e);
      if (onValueChange) onValueChange(e.target.value);
    };
    return <input data-testid="input" {...props} onChange={handleChange} />;
  },
}));

jest.mock('@/components/ui/label', () => ({
  Label: ({ children, ...props }) => <label data-testid="label" {...props}>{children}</label>,
}));

jest.mock('@/components/ui/switch', () => ({
  Switch: ({ onCheckedChange, checked, ...props }) => {
    const handleChange = () => {
      if (onCheckedChange) onCheckedChange(!checked);
    };
    return (
      <button
        data-testid="switch"
        role="switch"
        aria-checked={checked}
        onClick={handleChange}
        {...props}
      />
    );
  },
}));

jest.mock('@/components/ui/slider', () => ({
  Slider: ({ onValueChange, value, ...props }) => {
    const handleChange = (e) => {
      if (onValueChange) onValueChange([Number(e.target.value)]);
    };
    return (
      <input
        data-testid="slider"
        type="range"
        value={value?.[0] || 0}
        onChange={handleChange}
        {...props}
      />
    );
  },
}));

jest.mock('@/components/ui/textarea', () => ({
  Textarea: (props) => <textarea data-testid="textarea" {...props} />,
}));

jest.mock('@/components/ui/checkbox', () => ({
  Checkbox: (props) => <input data-testid="checkbox" type="checkbox" {...props} />,
}));

jest.mock('@/components/ui/dialog', () => ({
  Dialog: ({ children, open }) => open ? <div data-testid="dialog">{children}</div> : null,
  DialogTrigger: ({ children, ...props }) => <button data-testid="dialog-trigger" {...props}>{children}</button>,
  DialogContent: ({ children, ...props }) => <div data-testid="dialog-content" {...props}>{children}</div>,
  DialogHeader: ({ children, ...props }) => <div data-testid="dialog-header" {...props}>{children}</div>,
  DialogFooter: ({ children, ...props }) => <div data-testid="dialog-footer" {...props}>{children}</div>,
  DialogTitle: ({ children, ...props }) => <h2 data-testid="dialog-title" {...props}>{children}</h2>,
  DialogDescription: ({ children, ...props }) => <p data-testid="dialog-description" {...props}>{children}</p>,
}));

jest.mock('@/components/ui/separator', () => ({
  Separator: (props) => <hr data-testid="separator" {...props} />,
}));

jest.mock('@/components/ui/tooltip', () => ({
  TooltipProvider: ({ children }) => <>{children}</>,
  Tooltip: ({ children }) => <>{children}</>,
  TooltipTrigger: ({ children, ...props }) => <span data-testid="tooltip-trigger" {...props}>{children}</span>,
  TooltipContent: ({ children, ...props }) => <div data-testid="tooltip-content" {...props}>{children}</div>,
}));

jest.mock('@/components/ui/progress', () => ({
  Progress: ({ value, ...props }) => (
    <div
      data-testid="progress"
      role="progressbar"
      aria-valuenow={value}
      {...props}
    />
  ),
}));
