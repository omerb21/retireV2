import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import App from "./App";


describe("App", () => {
  it("renders frontend shell heading", () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    expect(screen.getByText("Retirement Planning V2 - Frontend Shell")).toBeInTheDocument();
  });
});
