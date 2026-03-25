import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("App", () => {
  it("temel ekranı ve başlangıç durumunu gösterir", () => {
    render(<App />);

    expect(screen.getByText("Frontend TTS Console")).toBeInTheDocument();
    expect(screen.getByTestId("status-badge")).toHaveTextContent("Disconnected");
    expect(screen.getByRole("button", { name: "Speak" })).toBeDisabled();
    expect(screen.getByText("Dev seed aktif: ornek metin ve loglar yuklendi.")).toBeInTheDocument();
  });
});
