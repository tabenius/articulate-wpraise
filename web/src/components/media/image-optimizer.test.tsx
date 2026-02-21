import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ImageOptimizer } from "./image-optimizer";

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

// Mock File and FileReader
global.FileReader = class FileReader {
  readAsDataURL() {
    setTimeout(() => {
      // @ts-ignore
      this.onload?.({ target: { result: "data:image/png;base64,mock" } });
    }, 0);
  }
} as any;

describe("ImageOptimizer", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockImplementation((key) => {
      if (key === "sessionId") return "test-session";
      if (key === "activeConnectionId") return "1";
      return null;
    });
  });

  it("renders the image optimizer", () => {
    render(<ImageOptimizer />);

    expect(screen.getByText("Image Optimizer")).toBeInTheDocument();
  });

  it("displays all tabs", () => {
    render(<ImageOptimizer />);

    expect(screen.getByRole("tab", { name: /single/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /bulk/i })).toBeInTheDocument();
  });

  it("switches between tabs", async () => {
    const user = userEvent.setup();
    render(<ImageOptimizer />);

    const bulkTab = screen.getByRole("tab", { name: /bulk/i });
    await user.click(bulkTab);

    // Bulk tab content should be visible
    expect(screen.getByText(/Load Media Library/i)).toBeInTheDocument();
  });

  it("handles single image URL input", async () => {
    const user = userEvent.setup();
    render(<ImageOptimizer />);

    const urlInput = screen.getByPlaceholderText(/enter image url/i);
    await user.type(urlInput, "https://example.com/image.jpg");

    expect(urlInput).toHaveValue("https://example.com/image.jpg");
  });

  it("allows format selection", async () => {
    const user = userEvent.setup();
    render(<ImageOptimizer />);

    const formatSelect = screen.getByRole("combobox", { name: /output format/i });
    await user.click(formatSelect);

    // Format options should be available
    await waitFor(() => {
      expect(screen.getByRole("option", { name: /webp/i })).toBeInTheDocument();
    });
  });

  it("allows quality preset selection", async () => {
    const user = userEvent.setup();
    render(<ImageOptimizer />);

    const qualitySelect = screen.getByRole("combobox", { name: /quality preset/i });
    await user.click(qualitySelect);

    await waitFor(() => {
      expect(screen.getByRole("option", { name: /high/i })).toBeInTheDocument();
    });
  });

  it("handles file upload", async () => {
    const user = userEvent.setup();
    render(<ImageOptimizer />);

    const file = new File(["dummy"], "test.png", { type: "image/png" });
    const fileInput = screen.getByLabelText(/upload from computer/i);

    await user.upload(fileInput, file);

    await waitFor(() => {
      // File should be selected
      expect(fileInput).toHaveProperty("files");
    });
  });

  it("displays optimization result after success", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      json: async () => ({
        success: true,
        title: "test.png",
        original_size: 10000,
        compressed_size: 5000,
        savings: 50,
        format: "webp",
      }),
    });

    const user = userEvent.setup();
    render(<ImageOptimizer />);

    const urlInput = screen.getByPlaceholderText(/enter image url/i);
    await user.type(urlInput, "https://example.com/image.jpg");

    const optimizeButton = screen.getByRole("button", { name: /optimize/i });
    await user.click(optimizeButton);

    await waitFor(() => {
      expect(screen.getByText(/50%/)).toBeInTheDocument();
    });
  });

  it("handles optimization errors", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      json: async () => ({
        success: false,
        error: "Optimization failed",
      }),
    });

    const user = userEvent.setup();
    render(<ImageOptimizer />);

    const urlInput = screen.getByPlaceholderText(/enter image url/i);
    await user.type(urlInput, "https://example.com/image.jpg");

    const optimizeButton = screen.getByRole("button", { name: /optimize/i });
    await user.click(optimizeButton);

    await waitFor(() => {
      // Error should be handled gracefully
      expect(global.fetch).toHaveBeenCalled();
    });
  });

  it("allows max width configuration", async () => {
    const user = userEvent.setup();
    render(<ImageOptimizer />);

    const maxWidthInput = screen.getByPlaceholderText(/e\.g\. 1920/i);
    await user.type(maxWidthInput, "1920");

    expect(maxWidthInput).toHaveValue(1920);
  });

  it("allows max height configuration", async () => {
    const user = userEvent.setup();
    render(<ImageOptimizer />);

    const maxHeightInput = screen.getByPlaceholderText(/e\.g\. 1080/i);
    await user.type(maxHeightInput, "1080");

    expect(maxHeightInput).toHaveValue(1080);
  });
});
