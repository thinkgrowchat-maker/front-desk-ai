const $ = (sel) => document.querySelector(sel);
const messagesEl = $("#messages");
const inputEl = $("#input");
const sendBtn = $("#send");

// Conversation history sent to the backend so follow-up questions have context.
const history = [];

// --- health / status ------------------------------------------------------- //
fetch("/api/health")
  .then((r) => r.json())
  .then((h) => {
    const pill = $("#mode-pill");
    if (h.liveAI) {
      pill.textContent = "● Live · " + (h.providerLabel || "AI");
      pill.className = "pill pill-live";
    } else {
      pill.textContent = "● Demo mode";
      pill.className = "pill pill-demo";
    }
    $("#model-pill").textContent = h.model || "";
  })
  .catch(() => {
    $("#mode-pill").textContent = "offline";
  });

// --- rendering -------------------------------------------------------------- //
function addBubble(text, who, { escalated = false } = {}) {
  const div = document.createElement("div");
  div.className = `bubble ${who}` + (escalated ? " escalated" : "");
  const p = document.createElement("p");
  p.textContent = text;
  div.appendChild(p);
  if (escalated) {
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = "Handed off to the team";
    div.appendChild(badge);
  }
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function updateInspector(reply) {
  const status = $("#ins-status");
  if (reply.escalate) {
    status.className = "status-line escalated";
    status.textContent = "Escalated — handed off to a human";
  } else {
    status.className = "status-line answered";
    status.textContent = "Answered from the knowledge base";
  }

  const box = $("#ins-sources");
  box.innerHTML = "";
  const used = new Set(reply.usedSourceIds || []);
  const sources = reply.sources || [];
  if (!sources.length) {
    box.innerHTML = '<div class="empty">No relevant knowledge matched this question.</div>';
  } else {
    for (const s of sources) {
      const pct = Math.round(Math.min(1, s.score) * 100);
      const isUsed = used.has(s.id);
      const el = document.createElement("div");
      el.className = "source" + (isUsed ? " used" : "");
      el.innerHTML = `
        <div class="source-top">
          <span class="source-title">${s.title}</span>
          <span class="source-id">${s.id}</span>
        </div>
        <div class="bar"><span style="width:${pct}%"></span></div>
        <div class="source-score">
          similarity ${s.score.toFixed(3)}
          ${isUsed ? '<span class="used-tag">· cited</span>' : ""}
        </div>`;
      box.appendChild(el);
    }
  }

  const escWrap = $("#ins-escalation-wrap");
  if (reply.escalate && reply.escalationReason) {
    escWrap.hidden = false;
    $("#ins-escalation").textContent = reply.escalationReason;
  } else {
    escWrap.hidden = true;
  }
}

// --- sending ---------------------------------------------------------------- //
async function ask(message) {
  addBubble(message, "user");
  history.push({ role: "user", content: message });
  inputEl.value = "";
  sendBtn.disabled = true;

  const typing = addBubble("typing…", "bot");
  typing.classList.add("typing");

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message, history: history.slice(0, -1) }),
    });
    const reply = await res.json();
    typing.remove();

    if (reply.error) {
      addBubble("Sorry — something went wrong on our end.", "bot");
      return;
    }
    addBubble(reply.answer, "bot", { escalated: reply.escalate });
    history.push({ role: "assistant", content: reply.answer });
    updateInspector(reply);
  } catch (e) {
    typing.remove();
    addBubble("Sorry — I couldn't reach the server.", "bot");
  } finally {
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

$("#composer").addEventListener("submit", (e) => {
  e.preventDefault();
  const msg = inputEl.value.trim();
  if (msg) ask(msg);
});

$("#chips").addEventListener("click", (e) => {
  if (e.target.classList.contains("chip")) ask(e.target.textContent.trim());
});
