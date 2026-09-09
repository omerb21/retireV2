import { afterEach, describe, expect, it, vi } from "vitest";
import { importPensionProducts } from "./pensionProductsApi";

afterEach(() => vi.unstubAllGlobals());
describe("canonical multipart batch", () => {
  it.each([1, 3])("sends %i files in exactly one request using only the files field", async count => {
    const files = Array.from({ length: count }, (_, i) => new File(["source" + i], i + ".xml", { type: "application/xml" }));
    const result = { batch_identity: "identity", file_count: count, product_count: 0, products: [], diagnostics: [] };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => result });
    vi.stubGlobal("fetch", fetchMock);
    expect(await importPensionProducts(1, files)).toEqual(result);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/clients/1/pension-products/imports");
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
    expect(init.body.getAll("files")).toEqual(files);
    expect(init.body.has("file")).toBe(false);
    expect(init.headers).toBeUndefined(); // Browser owns the multipart boundary.
  });

  it("propagates the batch filename error without returning partial products", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 409, json: async () => ({ detail: { code: "SOURCE_BATCH_CONFLICT", message: "סתירה בקבצים a.xml, b.dat" } }) }));
    await expect(importPensionProducts(1, [new File(["a"], "a.xml"), new File(["b"], "b.dat")])).rejects.toThrow("a.xml, b.dat");
  });
});
