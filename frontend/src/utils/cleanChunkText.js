/**
 * Preprocess chunk text before passing to ReactMarkdown.
 * Removes common chunker artifacts: orphaned fragments, duplicate lines,
 * empty list items, and excessive blank lines.
 */
export function cleanChunkText(text) {
  if (!text) return '';

  let cleaned = text;

  // Remove orphaned sentence fragments at the start
  // (start with a lowercase letter, less than 50 chars before the first period)
  cleaned = cleaned.replace(/^[a-z][^.]{0,50}\.\s*/m, '');

  // Remove duplicate lines — if the same line appears twice within 3 lines, drop the dupe
  const lines = cleaned.split('\n');
  const deduped = [lines[0]];
  for (let i = 1; i < lines.length; i++) {
    const trimmed = lines[i].trim();
    if (trimmed === '') {
      deduped.push(lines[i]);
      continue;
    }
    const prevLines = deduped.slice(-3).map(l => l.trim());
    if (!prevLines.includes(trimmed)) {
      deduped.push(lines[i]);
    }
  }
  cleaned = deduped.join('\n');

  // Remove orphaned list numbers with no content
  cleaned = cleaned.replace(/^\s*\d+\.\s*$/gm, '');

  // Collapse excessive blank lines
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');

  return cleaned.trim();
}
