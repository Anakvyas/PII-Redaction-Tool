import type { PreviewHighlight } from "@/components/preview/types";

interface Needle {
  text: string;
  id: string;
  color: string;
  label: string;
}

function isWordChar(ch: string | undefined): boolean {
  return !!ch && /[\p{L}\p{N}_]/u.test(ch);
}

/**
 * Text-based approximation of the backend's span-based highlighting, for the
 * DOCX preview (which has no bbox/offset mapping back to the rendered HTML).
 * Wraps every whole-word occurrence of each detection's raw value in a <mark>,
 * longest needles first so e.g. "Jane Doe" wins over a bare "Jane".
 */
export function applyTextHighlights(root: HTMLElement, highlights: PreviewHighlight[]): void {
  const seen = new Set<string>();
  const needles: Needle[] = [];
  for (const h of highlights) {
    const text = h.rawValue.trim();
    if (!text || seen.has(text)) continue;
    seen.add(text);
    needles.push({ text, id: h.id, color: h.color, label: h.label });
  }
  needles.sort((a, b) => b.text.length - a.text.length);
  if (needles.length === 0) return;

  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const textNodes: Text[] = [];
  let node: Node | null;
  while ((node = walker.nextNode())) {
    if (node.textContent && node.textContent.trim()) textNodes.push(node as Text);
  }

  for (const textNode of textNodes) {
    const value = textNode.textContent ?? "";
    const fragment = buildFragment(value, needles);
    if (fragment) textNode.parentNode?.replaceChild(fragment, textNode);
  }
}

function buildFragment(value: string, needles: Needle[]): DocumentFragment | null {
  let matched = false;
  const fragment = document.createDocumentFragment();
  let cursor = 0;
  let plainStart = 0;

  while (cursor < value.length) {
    const needle = needles.find((n) => {
      if (!value.startsWith(n.text, cursor)) return false;
      const before = cursor > 0 ? value[cursor - 1] : undefined;
      const after = value[cursor + n.text.length];
      return !isWordChar(before) && !isWordChar(after);
    });

    if (needle) {
      if (cursor > plainStart) fragment.appendChild(document.createTextNode(value.slice(plainStart, cursor)));
      const mark = document.createElement("mark");
      mark.textContent = value.slice(cursor, cursor + needle.text.length);
      mark.dataset.highlightId = needle.id;
      mark.title = needle.label;
      mark.style.backgroundColor = `${needle.color}2e`;
      mark.style.borderBottom = `2px solid ${needle.color}`;
      mark.style.color = "inherit";
      mark.style.borderRadius = "2px";
      mark.style.padding = "0 1px";
      mark.style.transition = "background-color 120ms ease";
      fragment.appendChild(mark);
      matched = true;
      cursor += needle.text.length;
      plainStart = cursor;
    } else {
      cursor += 1;
    }
  }

  if (!matched) return null;
  if (plainStart < value.length) fragment.appendChild(document.createTextNode(value.slice(plainStart)));
  return fragment;
}
