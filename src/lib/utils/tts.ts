/**
 * Text-to-Speech utilities using Web Speech API
 */

export interface TTSOptions {
  rate?: number; // 0.1 to 10 (default: 1)
  pitch?: number; // 0 to 2 (default: 1)
  volume?: number; // 0 to 1 (default: 1)
  lang?: string; // BCP 47 language tag (default: 'en-US')
  voice?: SpeechSynthesisVoice | null;
}

/**
 * Check if browser supports Web Speech API
 */
export function isTTSSupported(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window;
}

/**
 * Get available voices from the browser
 */
export function getAvailableVoices(): Promise<SpeechSynthesisVoice[]> {
  return new Promise((resolve) => {
    if (!isTTSSupported()) {
      resolve([]);
      return;
    }

    const synth = window.speechSynthesis;
    let voices = synth.getVoices();

    if (voices.length > 0) {
      resolve(voices);
    } else {
      // Some browsers load voices asynchronously
      synth.onvoiceschanged = () => {
        voices = synth.getVoices();
        resolve(voices);
      };
    }
  });
}

/**
 * Clean markdown text for TTS reading
 * Removes markdown syntax, HTML tags, and URLs for better speech output
 */
export function cleanTextForSpeech(markdown: string): string {
  let text = markdown;

  // Remove frontmatter
  text = text.replace(/^---[\s\S]*?---\n/m, '');

  // Remove HTML tags
  text = text.replace(/<[^>]*>/g, '');

  // Remove markdown links but keep the text: [text](url) -> text
  text = text.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');

  // Remove markdown images: ![alt](url)
  text = text.replace(/!\[([^\]]*)\]\([^)]+\)/g, '');

  // Remove markdown headers (# ## ###) but keep the text
  text = text.replace(/^#{1,6}\s+/gm, '');

  // Remove markdown bold/italic: **text** or *text* -> text
  text = text.replace(/\*\*([^*]+)\*\*/g, '$1');
  text = text.replace(/\*([^*]+)\*/g, '$1');

  // Remove markdown code blocks
  text = text.replace(/```[\s\S]*?```/g, '');
  text = text.replace(/`([^`]+)`/g, '$1');

  // Remove horizontal rules
  text = text.replace(/^---+$/gm, '');

  // Remove blockquotes >
  text = text.replace(/^>\s*/gm, '');

  // Remove list markers (- * +)
  text = text.replace(/^[\s]*[-*+]\s+/gm, '');

  // Remove numbered list markers
  text = text.replace(/^[\s]*\d+\.\s+/gm, '');

  // Clean up URLs that weren't in markdown format
  text = text.replace(/https?:\/\/[^\s]+/g, '');

  // Replace multiple newlines with a single one
  text = text.replace(/\n{3,}/g, '\n\n');

  // Replace special characters/emojis with readable text
  text = text.replace(/🚨/g, 'Alert: ');
  text = text.replace(/🛠️/g, 'Tools: ');
  text = text.replace(/📊/g, 'Data: ');
  text = text.replace(/⚠️/g, 'Warning: ');
  text = text.replace(/✅/g, 'Check: ');
  text = text.replace(/❌/g, 'Issue: ');

  // Clean up excessive whitespace
  text = text.replace(/[ \t]+/g, ' ');
  text = text.trim();

  return text;
}

/**
 * Calculate estimated reading time in minutes
 */
export function estimateReadingTime(text: string, wordsPerMinute: number = 150): number {
  const words = text.trim().split(/\s+/).length;
  return Math.ceil(words / wordsPerMinute);
}

/**
 * Split long text into chunks for better TTS handling
 * Prevents browser from cutting off long speeches
 */
export function splitIntoChunks(text: string, maxChunkSize: number = 4000): string[] {
  const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];
  const chunks: string[] = [];
  let currentChunk = '';

  for (const sentence of sentences) {
    if (currentChunk.length + sentence.length > maxChunkSize) {
      if (currentChunk) {
        chunks.push(currentChunk.trim());
        currentChunk = '';
      }
      // If a single sentence is too long, split it anyway
      if (sentence.length > maxChunkSize) {
        const words = sentence.split(' ');
        let wordChunk = '';
        for (const word of words) {
          if (wordChunk.length + word.length > maxChunkSize) {
            chunks.push(wordChunk.trim());
            wordChunk = '';
          }
          wordChunk += word + ' ';
        }
        if (wordChunk) chunks.push(wordChunk.trim());
      } else {
        currentChunk = sentence;
      }
    } else {
      currentChunk += sentence;
    }
  }

  if (currentChunk) {
    chunks.push(currentChunk.trim());
  }

  return chunks;
}

/**
 * Format time in MM:SS format
 */
export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}
