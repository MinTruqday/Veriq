function escapeText(value) {
  return String(value || "").replace(/([\\`*_{}[\]<>#+.!|])/g, "\\$1");
}

function renderInline(node) {
  if (!node) return "";
  if (node.type === "text") {
    let value = escapeText(node.text);
    for (const mark of node.marks || []) {
      if (mark.type === "bold") value = `**${value}**`;
      if (mark.type === "italic") value = `*${value}*`;
      if (mark.type === "strike") value = `~~${value}~~`;
      if (mark.type === "code") value = `\`${String(node.text || "").replaceAll("`", "\\`")}\``;
      if (mark.type === "underline") value = `<u>${value}</u>`;
      if (mark.type === "link") {
        const href = String(mark.attrs?.href || "").replace(/[()\\]/g, "\\$&");
        value = href ? `[${value}](${href})` : value;
      }
      if (mark.type === "highlight") value = `==${value}==`;
    }
    return value;
  }
  if (node.type === "hardBreak") return "  \n";
  if (node.type === "image") return escapeText(node.attrs?.alt || "");
  if (node.type === "mention") return escapeText(node.attrs?.label || node.attrs?.id || "");
  return (node.content || []).map(renderInline).join("");
}

function renderBlocks(nodes, depth = 0) {
  return (nodes || [])
    .map((node) => {
      if (node.type === "paragraph") return renderInline(node).trimEnd();
      if (node.type === "heading") {
        const level = Math.max(1, Math.min(6, Number(node.attrs?.level) || 1));
        return `${"#".repeat(level)} ${renderInline(node).trim()}`;
      }
      if (node.type === "bulletList" || node.type === "orderedList") {
        const start = Number(node.attrs?.start) || 1;
        return (node.content || [])
          .map((item, index) => {
            const marker = node.type === "bulletList" ? "-" : `${start + index}.`;
            const blocks = renderBlocks(item.content, depth + 1).split("\n");
            const indent = "  ".repeat(depth);
            return blocks
              .map((line, lineIndex) => `${indent}${lineIndex ? "  " : `${marker} `}${line}`)
              .join("\n");
          })
          .join("\n");
      }
      if (node.type === "blockquote") {
        return renderBlocks(node.content, depth)
          .split("\n")
          .map((line) => `> ${line}`)
          .join("\n");
      }
      if (node.type === "codeBlock") {
        const language = String(node.attrs?.language || "").replace(/[^a-zA-Z0-9_-]/g, "");
        const code = (node.content || []).map((item) => item.text || "").join("");
        return `\`\`\`${language}\n${code}\n\`\`\``;
      }
      if (node.type === "horizontalRule") return "---";
      if (node.type === "table") {
        const rows = (node.content || []).map((row) =>
          (row.content || []).map((cell) => renderBlocks(cell.content).replace(/\n/g, " ").trim()),
        );
        if (!rows.length) return "";
        const width = Math.max(...rows.map((row) => row.length));
        const cells = rows.map(
          (row) =>
            `| ${Array.from({ length: width }, (_, index) => row[index] || "").join(" | ")} |`,
        );
        const separator = `| ${Array.from({ length: width }, () => "---").join(" | ")} |`;
        return [cells[0], separator, ...cells.slice(1)].join("\n");
      }
      return renderBlocks(node.content, depth) || renderInline(node);
    })
    .filter(Boolean)
    .join("\n\n");
}

export function documentToMarkdown(document) {
  if (typeof document === "string") return document.trim();
  return renderBlocks(document?.content).trim();
}

export function emptyRichDocument() {
  return { type: "doc", content: [{ type: "paragraph" }] };
}
