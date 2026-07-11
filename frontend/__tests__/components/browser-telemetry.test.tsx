// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>

import { render } from "@testing-library/react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { BrowserTelemetry } from "@/components/browser-telemetry";

// Mock the open telemetry modules so they don't hit the real network or env.
vi.mock("@opentelemetry/sdk-trace-web", () => ({
  WebTracerProvider: vi.fn().mockImplementation(() => ({
    register: vi.fn(),
  })),
}));

vi.mock("@opentelemetry/sdk-trace-base", () => ({
  BatchSpanProcessor: vi.fn(),
}));

vi.mock("@opentelemetry/exporter-trace-otlp-http", () => ({
  OTLPTraceExporter: vi.fn(),
}));

vi.mock("@opentelemetry/instrumentation-document-load", () => ({
  DocumentLoadInstrumentation: vi.fn(),
}));

vi.mock("@opentelemetry/instrumentation-user-interaction", () => ({
  UserInteractionInstrumentation: vi.fn(),
}));

vi.mock("@opentelemetry/instrumentation", () => ({
  registerInstrumentations: vi.fn(),
}));

vi.mock("@opentelemetry/resources", () => ({
  Resource: vi.fn(),
}));

vi.mock("@opentelemetry/semantic-conventions", () => ({
  SEMRESATTRS_SERVICE_NAME: "service.name",
}));

vi.mock("@opentelemetry/context-zone", () => ({
  ZoneContextManager: vi.fn(),
}));

describe("BrowserTelemetry Component", () => {
  beforeEach(() => {
    // Clear global state before each test
    delete (window as any).__OTEL_BROWSER_INITIALIZED__;
  });

  afterEach(() => {
    delete (window as any).__OTEL_BROWSER_INITIALIZED__;
  });

  it("renders null and does not output DOM nodes", () => {
    const { container } = render(<BrowserTelemetry />);
    expect(container.firstChild).toBeNull();
  });

  it("sets the initialization flag on window", async () => {
    expect((window as any).__OTEL_BROWSER_INITIALIZED__).toBeUndefined();
    render(<BrowserTelemetry />);
    // Wait for microtasks to resolve for dynamic imports
    await new Promise(resolve => setTimeout(resolve, 0));
    expect((window as any).__OTEL_BROWSER_INITIALIZED__).toBe(true);
  });
});
