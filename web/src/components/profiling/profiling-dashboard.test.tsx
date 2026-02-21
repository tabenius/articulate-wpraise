import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { ProfilingDashboard } from "./profiling-dashboard";

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

describe("ProfilingDashboard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockImplementation((key) => {
      if (key === "sessionId") return "test-session";
      if (key === "currentOrganizationId") return "1";
      return null;
    });
  });

  it("renders the profiling dashboard", () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      json: async () => ({ success: true, stats: [] }),
    });

    render(<ProfilingDashboard />);

    expect(screen.getByText("Total Calls")).toBeInTheDocument();
    expect(screen.getByText("Avg Execution")).toBeInTheDocument();
  });

  it("loads profiling stats on mount", async () => {
    const mockStats = [
      {
        function_name: "create_post",
        date: "2024-01-01",
        call_count: 10,
        avg_time_ms: 150,
        min_time_ms: 100,
        max_time_ms: 200,
        p95_time_ms: 180,
        p99_time_ms: 190,
        success_count: 9,
        error_count: 1,
      },
    ];

    (global.fetch as jest.Mock).mockResolvedValue({
      json: async () => ({ success: true, stats: mockStats }),
    });

    render(<ProfilingDashboard />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "http://localhost:8000/profiling/stats",
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "X-Session-ID": "test-session",
          }),
        })
      );
    });
  });

  it("handles fetch errors gracefully", async () => {
    (global.fetch as jest.Mock).mockRejectedValue(new Error("Network error"));

    render(<ProfilingDashboard />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
    });

    // Component should still render after error
    expect(screen.getByText("Function Profiling")).toBeInTheDocument();
  });

  it("filters by date range", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      json: async () => ({ success: true, stats: [] }),
    });

    render(<ProfilingDashboard />);

    const dateSelect = screen.getByRole("combobox", { name: /date range/i });
    fireEvent.click(dateSelect);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
    });
  });

  it("displays stats when loaded", async () => {
    const mockStats = [
      {
        function_name: "create_post",
        date: "2024-01-01",
        call_count: 10,
        avg_time_ms: 150,
        min_time_ms: 100,
        max_time_ms: 200,
        p95_time_ms: 180,
        p99_time_ms: 190,
        success_count: 9,
        error_count: 1,
      },
    ];

    (global.fetch as jest.Mock).mockResolvedValue({
      json: async () => ({ success: true, stats: mockStats }),
    });

    render(<ProfilingDashboard />);

    await waitFor(() => {
      expect(screen.getByText("create_post")).toBeInTheDocument();
    });
  });

  it("handles missing session gracefully", async () => {
    localStorageMock.getItem.mockReturnValue(null);

    render(<ProfilingDashboard />);

    await waitFor(() => {
      // Should attempt to load but handle missing session
      expect(global.fetch).not.toHaveBeenCalled();
    });
  });
});
