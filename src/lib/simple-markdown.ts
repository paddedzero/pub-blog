export function parseMarkdown(markdown: string): string {
  return markdown
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2">$1</a>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*?<\/li>\s*)+/gs, '<ul>$&</ul>')
    .replace(/\n\n+/g, '</p><p>')
    .replace(/^(?!<[hula])/gm, '<p>')
    .replace(/(?!>)$/gm, '</p>')
    .replace(/<p><\/p>/g, '')
    .replace(/<p>(<[hula])/g, '$1')
    .replace(/(<\/[hula][^>]*>)<\/p>/g, '$1');
}
