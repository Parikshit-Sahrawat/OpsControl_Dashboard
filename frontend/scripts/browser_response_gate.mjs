// Test-only: delay delivery of genuine browser fetch responses, not requests.
// No Playwright routes, replayed credentials, fabricated bodies, or TLS changes.
export async function holdBrowserResponses(page, suffix) {
  await page.evaluate((suffix) => {
    const key = "__opscontrolResponseGate";
    if (window[key] && !window[key].state.released) throw Error("Response gate already installed");
    const original = window.fetch;
    let release;
    const ready = new Promise(resolve => { release = resolve; });
    const state = { pending:0, completed:0, received:0, released:false };
    const wrapper = async function (...args) {
      const response = await Reflect.apply(original, this, args);
      const input = args[0];
      const method = args[1]?.method || (input instanceof Request ? input.method : "GET");
      const path = new URL(input instanceof Request ? input.url : input, location.href).pathname;
      if (!state.released && method.toUpperCase() === "GET" && path.endsWith(suffix)) {
        state.pending++; state.received++;
        try { await ready; state.completed++; }
        finally { state.pending--; }
      }
      return response;
    };
    window.fetch = wrapper;
    window[key] = {
      state,
      release() {
        if (state.released) return;
        if (window.fetch !== wrapper) throw Error("Another fetch interceptor replaced the owned gate");
        state.released = true;
        window.fetch = original;
        release();
      },
    };
  }, suffix);
  const state = () => page.evaluate(() => ({...window.__opscontrolResponseGate.state}));
  return {
    state,
    async release() {
      await page.evaluate(() => window.__opscontrolResponseGate.release());
      await page.waitForFunction(() => window.__opscontrolResponseGate.state.pending === 0);
      return state();
    },
  };
}
