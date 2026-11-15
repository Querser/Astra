// Headless browser exercise, exclusively against the temporary services in verify_chat_browser.py.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const { chromium } = require(process.env.ASTRA_PLAYWRIGHT || "playwright");

async function main({api, web, live, replay}) {
  const gate = process.env.ASTRA_QA_GATE;
  const browser = await chromium.launch({channel: process.env.ASTRA_CHROME_CHANNEL || "chrome", headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 900}});
    page.setDefaultTimeout(45000);
    const get = async (path) => {
      const r = await fetch(api + "/api/v1" + path);
      assert.ok(r.ok, "GET " + path + ": " + r.status);
      return r.json();
    };
    const [a, b] = await get("/crew");
    assert.ok(a && b);
    const history = (owner) => get("/assistant/chat/" + owner.id);
    let postStarted, pendingPostCount = 0;
    await page.route("**/api/v1/**", async route => {
      const path = new URL(route.request().url()).pathname + new URL(route.request().url()).search;
      const isChatPost = path.endsWith("/assistant/chat") && route.request().method() === "POST";
      if (isChatPost) { pendingPostCount++; postStarted?.(); }
      try {
        const response = await route.fetch({url: api + path, timeout: 180000});
        await route.fulfill({response});
      } catch (error) {
        // Reload or browser disposal can abort the intercepted response. API persistence is checked below.
        if (!/closed|canceled|aborted|disposed|Target page/i.test(String(error))) throw error;
      } finally { if (isChatPost) pendingPostCount--; }
    });
    const workspace = async () => {
      await page.getByRole("button", {name:"Add Complaint"}).click();
      await page.locator("#chat-message").waitFor();
    };
    const chat = page.locator("#workspace-complaint"), draft = chat.locator("textarea");
    const switchTo = async owner => {
      await page.getByLabel("Select profile").selectOption(owner.id);
      await chat.locator(".chat-heading").getByText(owner.display_name, {exact:false}).waitFor();
    };
    const send = async msg => {
      const started = new Promise(resolve => { postStarted = resolve; });
      await draft.fill(msg);
      await draft.press("Enter");
      await started;
      postStarted = null;
    };
    const eventually = async fn => {
      for (let i = 0; i < 1000; i++) {
        if (await fn()) return;
        await new Promise(r=>setTimeout(r,120));
      }
      assert.fail("Expected application state did not arrive");
    };
    const waitHistory = async (len) => eventually(async()=> (await history(a)).length === len);
    await page.goto(web);
    await workspace();
    const mobile = await browser.newPage({viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true});
    await mobile.route("**/api/v1/**", async route => {
      const path = new URL(route.request().url()).pathname + new URL(route.request().url()).search;
      const response = await route.fetch({url: api + path, timeout: 180000});
      await route.fulfill({response});
    });
    await mobile.goto(web);
    await mobile.getByRole("button", {name:"Add Complaint"}).click();
    await mobile.locator("#chat-message").waitFor();
    assert.ok(await mobile.getByLabel("Select profile").isVisible());
    assert.ok((await mobile.evaluate(() => document.documentElement.scrollWidth)) <= 390,
      "Mobile page should not overflow horizontally");
    await mobile.unrouteAll({behavior: "wait"});
    await mobile.close();
    await page.getByText("Points: 84", {exact:true}).waitFor();
    assert.equal(await page.locator("#workspace-research .science-card").count(), 16);
    assert.ok(await page.locator("#workspace-research a[href^='http']").count() >= 3);
    assert.ok((await page.locator("#workspace-research").textContent()).includes("equivalent dose rate in the export is not available"));
    assert.ok((await page.locator("#workspace-research").textContent()).includes("not the data of the selected ASTRA profile"));
    const unlinkedText = await page.evaluate(() => {
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      const chunks = [];
      while (walker.nextNode()) {
        const parent = walker.currentNode.parentElement;
        if (parent && !parent.closest("a")) chunks.push(walker.currentNode.textContent || "");
      }
      return chunks.join(" ");
    });
    assert.doesNotMatch(unlinkedText, /NASA|Canadian Space Agency|\bCSA\b|OCHMO|OSDR|Inspiration4/i);
    console.log("Browser research sources: 16 cards, 84 RadLab points, OSD-575 separated");
    await switchTo(b);
    await draft.fill("Profile B draft");
    const report = page.locator("#workspace-report tbody");
    await report.waitFor();
    const bReport = await report.textContent();
    await switchTo(a);
    await draft.fill("Profile A draft");
    await switchTo(b);
    assert.equal(await draft.inputValue(), "Profile B draft");
    await switchTo(a);
    assert.equal(await draft.inputValue(), "Profile A draft");

    if (!live) {
      for (const [index, outcome] of ["ok", "fail"].entries()) {
        for (const marker of [gate, gate + ".entered"]) if (fs.existsSync(marker)) fs.unlinkSync(marker);
        await send(index ? "4" : "Synthetic complaint");
        await eventually(()=>fs.existsSync(gate + ".entered"));
        await switchTo(b);
        assert.equal(await draft.inputValue(), "Profile B draft");
        assert.equal(await chat.locator(".chat-bubble").count(), 0);
        assert.equal(await draft.isEnabled(), true);
        await switchTo(a);
        assert.equal(await draft.isDisabled(), true);
        await switchTo(b);
        if (!index) {
          await page.reload();
          await workspace();
          await switchTo(b);
          assert.equal(await draft.inputValue(), "Profile B draft");
        }
        fs.writeFileSync(gate, outcome);
        await waitHistory(2 * (index + 1));
        assert.deepEqual(await history(b), []);
        assert.equal(await chat.locator(".chat-bubble").count(), 0);
        await report.waitFor();
        assert.equal(await report.textContent(), bReport);
        await switchTo(a);
        await eventually(async()=>await chat.locator("article.chat-bubble").count() === 2*(index+1) && await draft.isEnabled());
        const rows = await history(a);
        assert.ok(rows.every(r=>r.crew_member_id === a.id));
        assert.equal(new Set(rows.map(r=>r.id)).size, rows.length);
        const last = rows.at(-1);
        assert.equal(last.engine.startsWith("local_model_error:"), outcome==="fail");
        const memory = await get("/assistant/chat/" + a.id + "/memory");
        if (!index) {
          assert.ok(JSON.stringify(memory).includes(last.id));
          assert.ok(JSON.stringify(memory).includes("vomited"));
        }
        await page.reload();
        await workspace();
        await switchTo(a);
        await eventually(async()=>await chat.locator("article.chat-bubble").count() === rows.length && await draft.isEnabled());
        console.log("Browser A1/A2/A3",outcome,"restored",rows.length,"unique owned turns");
      }
      const existing = (await history(a))[0];
      await page.evaluate(({owner,id}) => sessionStorage.setItem("astra.chat.pending." + owner,
        JSON.stringify({request_id:id, message:"Synthetic conflict", at:new Date().toISOString()})),
        {owner:a.id, id:existing.request_id});
      await page.reload();
      await workspace();
      await switchTo(a);
      await chat.getByText(/request identifier is already linked/i).waitFor();
      assert.equal(await chat.getByRole("button",{name:"Repeat request"}).count(), 0);
      assert.equal(await draft.isEnabled(), true);
      assert.equal((await history(a)).length, 4);
      await switchTo(b);
      assert.equal(await chat.getByText(/request identifier is already linked/i).count(), 0);
    } else {
      const constructed = ["I have a headache", "This morning, 2/10", "No nausea or vomiting",
        "The pain is gone", "Analyze all my measurements and forecasts: what has changed?"];
      const turns = replay.length ? [...replay, constructed.at(-1)] : constructed;
      let previous = "";
      for (const [index, message] of turns.entries()) {
        await send(message);
        if (index === 0) {
          await switchTo(b);
          assert.ok(pendingPostCount > 0, "Profile switch should occur while the model responds");
          assert.equal(await chat.locator(".chat-bubble").count(), 0);
          assert.deepEqual(await history(b), []);
        }
        await waitHistory((index + 1) * 2);
        if (index === 0) await switchTo(a);
        await eventually(async () => await chat.locator("article.chat-bubble").count() === (index + 1) * 2 && await draft.isEnabled());
        const rows = await history(a);
        const answer = rows.at(-1);
        assert.equal(rows.at(-2).body, message);
        assert.equal(answer.engine, "local_model:" + (process.env.ASTRA_OLLAMA_MODEL || "qwen3:8b"));
        assert.doesNotMatch(answer.body, /[\u0410-\u042f\u0430-\u044f\u0401\u0451]/);
        assert.notEqual(answer.body, previous);
        assert.deepEqual(await history(b), []);
        previous = answer.body;
        if (message.includes("forecasts")) {
          assert.match(answer.body, /forecast|prediction/i);
          assert.match(answer.body, /pulse|heart rate|sleep|activity|oxygen/i);
        }
        console.log("Live browser turn", index + 1, answer.engine, answer.body.length, "characters");
      }
      console.log("Live browser conversation and profile isolation passed");
    }
  } finally { await browser.close(); }
}
main(JSON.parse(fs.readFileSync(0,"utf8"))).catch(e=>{console.error(e);process.exitCode=1;});
