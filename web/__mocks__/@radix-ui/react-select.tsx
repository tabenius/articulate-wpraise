import React from 'react';

export const Root = ({ children, ...props }: any) => <div data-testid="select-root" {...props}>{children}</div>;
export const Trigger = ({ children, ...props }: any) => <button data-testid="select-trigger" role="combobox" {...props}>{children}</button>;
export const Value = ({ children, placeholder, ...props }: any) => <span data-testid="select-value" {...props}>{children || placeholder}</span>;
export const Icon = ({ children, ...props }: any) => <span data-testid="select-icon" {...props}>{children}</span>;
export const Portal = ({ children }: any) => <>{children}</>;
export const Content = ({ children, ...props }: any) => <div data-testid="select-content" {...props}>{children}</div>;
export const Viewport = ({ children, ...props }: any) => <div data-testid="select-viewport" {...props}>{children}</div>;
export const Item = ({ children, value, ...props }: any) => <div data-testid="select-item" role="option" data-value={value} {...props}>{children}</div>;
export const ItemText = ({ children, ...props }: any) => <span data-testid="select-item-text" {...props}>{children}</span>;
export const ItemIndicator = ({ children, ...props }: any) => <span data-testid="select-item-indicator" {...props}>{children}</span>;
export const ScrollUpButton = ({ children, ...props }: any) => <div data-testid="select-scroll-up" {...props}>{children}</div>;
export const ScrollDownButton = ({ children, ...props }: any) => <div data-testid="select-scroll-down" {...props}>{children}</div>;
export const Label = ({ children, ...props }: any) => <div data-testid="select-label" {...props}>{children}</div>;
export const Separator = (props: any) => <div data-testid="select-separator" {...props} />;
export const Group = ({ children, ...props }: any) => <div data-testid="select-group" {...props}>{children}</div>;
