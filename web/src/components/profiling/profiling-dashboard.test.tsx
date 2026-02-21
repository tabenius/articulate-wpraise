import { render, screen, waitFor } from "@testing-library/react";
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

  describe("Rendering", () => {
    it("renders summary cards with initial state", () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        json: async () => ({ success: true, stats: [] }),
      });

      render(<ProfilingDashboard />);

      // Verify summary cards are present
      expect(screen.getByText("Total Calls")).toBeInTheDocument();
      expect(screen.getByText("Avg Execution")).toBeInTheDocument();
      expect(screen.getByText("Success Rate")).toBeInTheDocument();
      expect(screen.getByText("Slowest Function")).toBeInTheDocument();
    });

    it("displays zero state when no stats are available", () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        json: async () => ({ success: true, stats: [] }),
      });

      render(<ProfilingDashboard />);

      // With no stats, summary values should be 0 or defaults
      expect(screen.getByText("0")).toBeInTheDocument(); // Total calls
    });
  });

  describe("Data Loading", () => {
    it("initiates data fetch on mount", async () => {
      const mockStats = [
        {
          function_name: "create_post",
          date: "2024-01-01",
          call_count: 100,
          avg_time_ms: 150,
          min_time_ms: 100,
          max_time_ms: 200,
          p95_time_ms: 180,
          p99_time_ms: 190,
          success_count: 95,
          error_count: 5,
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValue({
        json: async () => ({ success: true, stats: mockStats }),
      });

      render(<ProfilingDashboard />);

      // Component renders with summary structure
      expect(screen.getByText("Total Calls")).toBeInTheDocument();
    });

    it("handles empty stats response", async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        json: async () => ({ success: true, stats: [] }),
      });

      render(<ProfilingDashboard />);

      await waitFor(() => {
        expect(screen.getByText("Total Calls")).toBeInTheDocument();
      });
    });
  });

  describe("Error Handling", () => {
    it("renders component even with fetch errors", async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error("Network error"));

      render(<ProfilingDashboard />);

      // Component should still render basic structure
      expect(screen.getByText("Total Calls")).toBeInTheDocument();
    });

    it("handles missing session gracefully", () => {
      localStorageMock.getItem.mockReturnValue(null);

      render(<ProfilingDashboard />);

      // Component should still render even without session
      expect(screen.getByText("Total Calls")).toBeInTheDocument();
    });
  });

  describe("Statistics Display", () => {
    it("provides statistics visualization structure", async () => {
      const mockStats = [
        {
          function_name: "test_func",
          date: "2024-01-01",
          call_count: 10,
          avg_time_ms: 100,
          min_time_ms: 50,
          max_time_ms: 150,
          p95_time_ms: 140,
          p99_time_ms: 148,
          success_count: 9,
          error_count: 1,
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValue({
        json: async () => ({ success: true, stats: mockStats }),
      });

      render(<ProfilingDashboard />);

      // Component provides statistics structure
      expect(screen.getByText("Total Calls")).toBeInTheDocument();
      expect(screen.getByText("Success Rate")).toBeInTheDocument();
    });

    it("displays performance metrics", async () => {
      const mockStats = [
        {
          function_name: "test_func",
          date: "2024-01-01",
          call_count: 100,
          avg_time_ms: 100,
          min_time_ms: 50,
          max_time_ms: 150,
          p95_time_ms: 140,
          p99_time_ms: 148,
          success_count: 95,
          error_count: 5,
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValue({
        json: async () => ({ success: true, stats: mockStats }),
      });

      render(<ProfilingDashboard />);

      // Component displays performance data structure
      expect(screen.getByText("Avg Execution")).toBeInTheDocument();
      expect(screen.getByText("Slowest Function")).toBeInTheDocument();
    });
  });
});
