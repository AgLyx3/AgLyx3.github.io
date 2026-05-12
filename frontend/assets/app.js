(function () {
  "use strict";

  const config = {
    // Override with window.APP_CONFIG = { backendBaseUrl: "http://localhost:8000" }
    backendBaseUrl:
      (window.APP_CONFIG && window.APP_CONFIG.backendBaseUrl) ||
      localStorage.getItem("backendBaseUrl") ||
      "https://backend-green-zeta-37.vercel.app",
  };

  function endpoint(path) {
    return config.backendBaseUrl.replace(/\/$/, "") + path;
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  function linkify(value) {
    return value.replace(
      /(?<![="'])(https?:\/\/[^\s<>"']+)/g,
      '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
    );
  }

  function formatAssistantHtml(value) {
    const escaped = escapeHtml(value);
    const withBold = escaped.replace(/\*\*([^*\n][\s\S]*?)\*\*/g, (_, inner) => {
      const trimmed = inner.trim();
      return trimmed ? `<strong>${trimmed}</strong>` : `**${inner}**`;
    });
    const paragraphs = withBold
      .split(/\n\n+/)
      .map((part) => part.trim())
      .filter(Boolean);
    return paragraphs.length
      ? paragraphs.map((part) => `<p>${linkify(part)}</p>`).join("")
      : `<p>${linkify(withBold)}</p>`;
  }

  function createEl(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (typeof text === "string") el.textContent = text;
    return el;
  }

  function setStatus(el, message) {
    if (el) el.textContent = message || "";
  }

  function normalizeMetadata(raw) {
    const metadata = raw || {};
    const citations =
      metadata.cited_experiences ||
      metadata.citations ||
      metadata.sources ||
      [];
    const topics =
      metadata.active_topics ||
      metadata.topics ||
      metadata.topic_distribution ||
      [];
    return { citations, topics };
  }

  function formatTopic(topic) {
    if (typeof topic === "string") return { label: topic, score: null };
    return {
      label:
        topic.name || topic.topic || topic.label || topic.id || "Unnamed topic",
      score:
        topic.score ??
        topic.weight ??
        topic.activation ??
        topic.relevance ??
        null,
    };
  }

  function formatCitation(citation) {
    if (typeof citation === "string") return { label: citation, detail: "" };
    const label =
      citation.title ||
      citation.experience_title ||
      citation.id ||
      citation.source ||
      "Citation";
    const detail = citation.snippet || citation.chunk || citation.url || "";
    return { label, detail };
  }

  function renderChips(container, values, formatter) {
    if (!container) return;
    container.innerHTML = "";
    if (!values || values.length === 0) {
      container.append(createEl("p", "muted", "No metadata returned yet."));
      return;
    }
    values.forEach((value) => {
      const chip = createEl("button", "chip", "");
      chip.type = "button";
      const normalized = formatter(value);
      chip.textContent = normalized.label;
      if (normalized.score !== null && normalized.score !== undefined) {
        chip.textContent += ` (${Number(normalized.score).toFixed(2)})`;
      }
      if (normalized.detail) {
        chip.title = normalized.detail;
      }
      container.append(chip);
    });
  }

  async function parseChatResponse(response, onToken) {
    const contentType = response.headers.get("content-type") || "";
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `Request failed with status ${response.status}`);
    }

    if (contentType.includes("text/event-stream")) {
      return readEventStream(response, onToken);
    }
    if (response.body && !contentType.includes("application/json")) {
      return readEventStream(response, onToken, true);
    }

    const data = await response.json();
    const text =
      data.answer || data.response || data.text || data.message || "";
    if (text) onToken(text);
    return {
      text,
      metadata: data.metadata || data.final_metadata || data,
    };
  }

  async function readEventStream(response, onToken, isLooseStream) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalPayload = null;
    let assembledText = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() || "";

      for (const rawChunk of chunks) {
        const chunk = rawChunk.trim();
        if (!chunk) continue;
        const lines = chunk.split("\n");
        const dataLines = lines
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.replace(/^data:\s*/, ""));
        const payload = dataLines.join("\n");

        if (!payload && isLooseStream) {
          onToken(chunk);
          assembledText += chunk;
          continue;
        }
        if (!payload) continue;
        if (payload === "[DONE]") continue;

        try {
          const parsed = JSON.parse(payload);
          const delta =
            parsed.delta || parsed.token || parsed.text || parsed.content || "";
          if (delta) {
            onToken(delta);
            assembledText += delta;
          }
          if (parsed.final || parsed.metadata || parsed.active_topics) {
            finalPayload = parsed;
          }
        } catch (_error) {
          onToken(payload);
          assembledText += payload;
        }
      }
    }

    return {
      text: assembledText,
      metadata:
        (finalPayload && (finalPayload.metadata || finalPayload.final || finalPayload)) ||
        {},
    };
  }

  function initChatPage() {
    const form = document.getElementById("chatForm");
    if (!form) return;

    const input = document.getElementById("chatInput");
    const messages = document.getElementById("chatMessages");
    const status = document.getElementById("chatStatus");
    const submit = document.getElementById("chatSubmit");
    const topicsEl = document.getElementById("activeTopics");
    const citationsEl = document.getElementById("citationChips");

    function appendMessage(role, text, stream) {
      const item = createEl("article", `message message-${role}`, "");
      item.innerHTML = `<h3>${escapeHtml(role === "user" ? "You" : "Assistant")}</h3><p>${escapeHtml(
        text || ""
      )}</p>`;
      if (stream) item.dataset.stream = "true";
      messages.append(item);
      messages.scrollTop = messages.scrollHeight;
      return item.querySelector("p");
    }

    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      const question = input.value.trim();
      if (!question) return;

      appendMessage("user", question, false);
      input.value = "";
      submit.disabled = true;
      setStatus(status, "Sending request...");

      const assistantNode = appendMessage("assistant", "", true);

      try {
        const response = await fetch(endpoint("/chat"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: question }),
        });

        const result = await parseChatResponse(response, function (token) {
          assistantNode.textContent += token;
          messages.scrollTop = messages.scrollHeight;
        });
        assistantNode.innerHTML = formatAssistantHtml(result.text || assistantNode.textContent);

        const metadata = normalizeMetadata(result.metadata);
        renderChips(citationsEl, metadata.citations, formatCitation);
        renderChips(topicsEl, metadata.topics, formatTopic);
        setStatus(status, "Response received.");
      } catch (error) {
        assistantNode.textContent = "Request failed. Check backend URL and try again.";
        setStatus(status, `Error: ${error.message}`);
      } finally {
        submit.disabled = false;
      }
    });
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function normalizeGraphData(raw) {
    return {
      topics: asArray(raw.topics || raw.topic_nodes),
      experiences: asArray(raw.experiences || raw.experience_nodes || raw.nodes),
      edges: asArray(raw.edges || raw.relations || raw.links),
    };
  }

  function drawGraph(svg, data) {
    svg.innerHTML = "";
    const width = 900;
    const height = 520;
    const padding = 70;
    const cx = width / 2;
    const cy = height / 2;
    const topicRadius = Math.min(width, height) * 0.33;
    const topicPositions = new Map();

    data.topics.forEach((topic, index) => {
      const angle = (Math.PI * 2 * index) / Math.max(data.topics.length, 1);
      topicPositions.set(topic.id || topic.topic_id || topic.name || `t${index}`, {
        x: cx + topicRadius * Math.cos(angle),
        y: cy + topicRadius * Math.sin(angle),
        topic,
      });
    });

    const experiencePositions = new Map();
    data.experiences.forEach((exp, index) => {
      const id = exp.id || exp.experience_id || exp.title || `e${index}`;
      const related = data.edges.filter((edge) => {
        return (
          edge.source_experience_id ||
          edge.experience_id ||
          edge.source ||
          edge.from
        ) === id;
      });
      if (related.length === 0) {
        experiencePositions.set(id, {
          x: padding + ((index + 1) * (width - padding * 2)) / (data.experiences.length + 1),
          y: cy,
          exp,
        });
        return;
      }
      let sx = 0;
      let sy = 0;
      related.forEach((edge) => {
        const topicId =
          edge.target_topic_id || edge.topic_id || edge.target || edge.to;
        const pos = topicPositions.get(topicId);
        if (pos) {
          sx += pos.x;
          sy += pos.y;
        }
      });
      const count = Math.max(related.length, 1);
      experiencePositions.set(id, { x: sx / count, y: sy / count, exp });
    });

    const ns = "http://www.w3.org/2000/svg";
    data.edges.forEach((edge) => {
      const eId =
        edge.source_experience_id || edge.experience_id || edge.source || edge.from;
      const tId = edge.target_topic_id || edge.topic_id || edge.target || edge.to;
      const ePos = experiencePositions.get(eId);
      const tPos = topicPositions.get(tId);
      if (!ePos || !tPos) return;
      const line = document.createElementNS(ns, "line");
      line.setAttribute("x1", String(ePos.x));
      line.setAttribute("y1", String(ePos.y));
      line.setAttribute("x2", String(tPos.x));
      line.setAttribute("y2", String(tPos.y));
      line.setAttribute("stroke", "var(--edge)");
      const relevance = Number(edge.relevance || edge.weight || 0.2);
      line.setAttribute("stroke-width", String(Math.max(1, relevance * 7)));
      svg.append(line);
    });

    topicPositions.forEach((value) => {
      const g = document.createElementNS(ns, "g");
      const activation = Number(value.topic.activation || 0);
      const circle = document.createElementNS(ns, "circle");
      circle.setAttribute("cx", String(value.x));
      circle.setAttribute("cy", String(value.y));
      circle.setAttribute("r", String(16 + Math.min(activation * 3, 18)));
      circle.setAttribute("class", "topic-node");
      const label = document.createElementNS(ns, "text");
      label.setAttribute("x", String(value.x));
      label.setAttribute("y", String(value.y + 4));
      label.setAttribute("text-anchor", "middle");
      label.textContent =
        value.topic.label || value.topic.name || value.topic.id || "Topic";
      g.append(circle, label);
      svg.append(g);
    });

    experiencePositions.forEach((value) => {
      const g = document.createElementNS(ns, "g");
      const activation = Number(value.exp.activation || 0);
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("x", String(value.x - 36));
      rect.setAttribute("y", String(value.y - 12));
      rect.setAttribute("rx", "6");
      rect.setAttribute("ry", "6");
      rect.setAttribute("width", String(72 + Math.min(activation * 4, 32)));
      rect.setAttribute("height", "24");
      rect.setAttribute("class", "experience-node");
      const label = document.createElementNS(ns, "text");
      label.setAttribute("x", String(value.x));
      label.setAttribute("y", String(value.y + 4));
      label.setAttribute("text-anchor", "middle");
      label.textContent = value.exp.title || value.exp.id || "Exp";
      g.append(rect, label);
      svg.append(g);
    });
  }

  function renderInteractiveList(listEl, items, getTitle, getBody) {
    listEl.innerHTML = "";
    if (items.length === 0) {
      listEl.append(createEl("li", "muted", "No items returned."));
      return;
    }

    items.forEach((item) => {
      const li = createEl("li", "interactive-item", "");
      const button = createEl("button", "item-toggle", getTitle(item));
      button.type = "button";
      button.setAttribute("aria-expanded", "false");
      const details = createEl("div", "item-details", getBody(item));
      details.hidden = true;

      button.addEventListener("click", function () {
        const expanded = button.getAttribute("aria-expanded") === "true";
        button.setAttribute("aria-expanded", String(!expanded));
        details.hidden = expanded;
      });
      button.addEventListener("keydown", function (event) {
        if (event.key === " " || event.key === "Enter") {
          event.preventDefault();
          button.click();
        }
      });
      li.append(button, details);
      listEl.append(li);
    });
  }

  function initGraphPage() {
    const svg = document.getElementById("graphCanvas");
    if (!svg) return;
    const status = document.getElementById("graphStatus");
    const topicList = document.getElementById("topicList");
    const experienceList = document.getElementById("experienceList");
    const reloadBtn = document.getElementById("graphReload");

    async function loadGraph() {
      setStatus(status, "Loading graph...");
      try {
        const response = await fetch(endpoint("/graph"));
        if (!response.ok) throw new Error(`Status ${response.status}`);
        const raw = await response.json();
        const data = normalizeGraphData(raw);
        drawGraph(svg, data);

        renderInteractiveList(
          topicList,
          data.topics,
          (topic) => `${topic.label || topic.name || topic.id || "Topic"} | activation ${
            Number(topic.activation || 0).toFixed(2)
          }`,
          (topic) => `Description: ${topic.description || "No description"}`
        );

        renderInteractiveList(
          experienceList,
          data.experiences,
          (exp) => `${exp.title || exp.id || "Experience"} | activation ${
            Number(exp.activation || 0).toFixed(2)
          }`,
          (exp) => {
            const relEdges = data.edges
              .filter((edge) => {
                return (
                  edge.source_experience_id ||
                  edge.experience_id ||
                  edge.source ||
                  edge.from
                ) === (exp.id || exp.experience_id)
                  ? true
                  : false;
              })
              .map((edge) => {
                const label =
                  edge.target_topic_id || edge.topic_id || edge.target || edge.to || "topic";
                const score = Number(edge.relevance || edge.weight || 0).toFixed(2);
                return `${label} (${score})`;
              });
            const relations =
              relEdges.length > 0 ? relEdges.join(", ") : "No relevance data";
            return `Context: ${exp.raw_context || "No context"} | Relevance: ${relations}`;
          }
        );

        setStatus(status, "Graph loaded.");
      } catch (error) {
        setStatus(
          status,
          `Graph request failed. Confirm backend URL and /graph endpoint. (${error.message})`
        );
      }
    }

    reloadBtn.addEventListener("click", loadGraph);
    loadGraph();
  }

  initChatPage();
  initGraphPage();
})();
