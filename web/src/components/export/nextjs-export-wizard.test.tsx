import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NextJSExportWizard } from "./nextjs-export-wizard";

// Mock the toast hook
jest.mock("@/hooks/use-toast", () => ({
  useToast: () => ({
    toast: jest.fn(),
  }),
}));

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  clear: jest.fn(),
};
global.localStorage = localStorageMock as any;

// Mock fetch
global.fetch = jest.fn();

// Mock URL.createObjectURL
global.URL.createObjectURL = jest.fn(() => "blob:mock-url");

describe("NextJSExportWizard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockImplementation((key) => {
      if (key === "sessionId") return "test-session";
      if (key === "activeConnectionId") return "1";
      return null;
    });
  });

  it("renders the export wizard", () => {
    render(<NextJSExportWizard />);

    expect(screen.getByText("Export to Next.js")).toBeInTheDocument();
  });

  it("displays configuration options", () => {
    render(<NextJSExportWizard />);

    expect(screen.getByText(/content format/i)).toBeInTheDocument();
    expect(screen.getByText(/render strategy/i)).toBeInTheDocument();
    expect(screen.getByText(/media strategy/i)).toBeInTheDocument();
  });

  it("allows content format selection", async () => {
    const user = userEvent.setup();
    render(<NextJSExportWizard />);

    const formatSelect = screen.getByRole("combobox", { name: /content format/i });
    await user.click(formatSelect);

    await waitFor(() => {
      expect(screen.getByRole("option", { name: /react components/i })).toBeInTheDocument();
    });
  });

  it("allows render strategy selection", async () => {
    const user = userEvent.setup();
    render(<NextJSExportWizard />);

    const strategySelect = screen.getByRole("combobox", { name: /render strategy/i });
    await user.click(strategySelect);

    await waitFor(() => {
      expect(screen.getByRole("option", { name: /static site generation/i })).toBeInTheDocument();
    });
  });

  it("allows media strategy selection", async () => {
    const user = userEvent.setup();
    render(<NextJSExportWizard />);

    const mediaSelect = screen.getByRole("combobox", { name: /media strategy/i });
    await user.click(mediaSelect);

    await waitFor(() => {
      expect(screen.getByRole("option", { name: /download all media/i })).toBeInTheDocument();
    });
  });

  it("starts export when button is clicked", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      json: async () => ({
        success: true,
        project_path: "/tmp/nextjs-export",
        files_created: 10,
      }),
    });

    const user = userEvent.setup();
    render(<NextJSExportWizard />);

    const exportButton = screen.getByRole("button", { name: /start export/i });
    await user.click(exportButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "http://localhost:8000/mcp/call-tool",
        expect.objectContaining({
          method: "POST",
        })
      );
    });
  });

  it("displays progress during export", async () => {
    (global.fetch as jest.Mock).mockImplementation(() =>
      new Promise(resolve => setTimeout(() => resolve({
        json: async () => ({
          success: true,
          project_path: "/tmp/nextjs-export",
        }),
      }), 100))
    );

    const user = userEvent.setup();
    render(<NextJSExportWizard />);

    const exportButton = screen.getByRole("button", { name: /start export/i });
    await user.click(exportButton);

    // Progress should be visible
    await waitFor(() => {
      expect(screen.getByRole("progressbar")).toBeInTheDocument();
    });
  });

  it("displays completion message after successful export", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      json: async () => ({
        success: true,
        project_path: "/tmp/nextjs-export",
        files_created: 10,
      }),
    });

    const user = userEvent.setup();
    render(<NextJSExportWizard />);

    const exportButton = screen.getByRole("button", { name: /start export/i });
    await user.click(exportButton);

    await waitFor(() => {
      expect(screen.getByText(/export complete/i)).toBeInTheDocument();
    });
  });

  it("handles export errors", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      json: async () => ({
        success: false,
        error: "Export failed",
      }),
    });

    const user = userEvent.setup();
    render(<NextJSExportWizard />);

    const exportButton = screen.getByRole("button", { name: /start export/i });
    await user.click(exportButton);

    await waitFor(() => {
      // Should handle error gracefully
      expect(global.fetch).toHaveBeenCalled();
    });
  });

  it("handles missing connection error", async () => {
    localStorageMock.getItem.mockReturnValue(null);

    const user = userEvent.setup();
    render(<NextJSExportWizard />);

    const exportButton = screen.getByRole("button", { name: /start export/i });
    await user.click(exportButton);

    await waitFor(() => {
      // Should not call fetch without connection
      expect(global.fetch).not.toHaveBeenCalled();
    });
  });

  it("allows reset after export", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      json: async () => ({
        success: true,
        project_path: "/tmp/nextjs-export",
      }),
    });

    const user = userEvent.setup();
    render(<NextJSExportWizard />);

    const exportButton = screen.getByRole("button", { name: /start export/i });
    await user.click(exportButton);

    await waitFor(() => {
      expect(screen.getByText(/export complete/i)).toBeInTheDocument();
    });

    const resetButton = screen.getByRole("button", { name: /export another/i });
    await user.click(resetButton);

    // Should return to configuration
    expect(screen.getByText(/content format/i)).toBeInTheDocument();
  });

  it("includes context in tool call", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      json: async () => ({
        success: true,
        project_path: "/tmp/nextjs-export",
      }),
    });

    const user = userEvent.setup();
    render(<NextJSExportWizard />);

    const exportButton = screen.getByRole("button", { name: /start export/i });
    await user.click(exportButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('"connection_id":1'),
        })
      );
    });
  });
});
