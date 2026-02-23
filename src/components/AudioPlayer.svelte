<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import {
    isTTSSupported,
    cleanTextForSpeech,
    estimateReadingTime,
    splitIntoChunks,
    formatTime,
    getAvailableVoices,
    type TTSOptions,
  } from '@/lib/utils/tts';

  export let content: string = '';
  export let title: string = 'Audio Playback';
  export let scrollTargetSelector: string = 'article'; // CSS selector for scroll target
  export let headings: any[] = []; // Array of {depth, slug, text} from Astro

  let isSupported = false;
  let isPlaying = false;
  let isPaused = false;
  let isLoading = false;
  let currentChunkIndex = 0;
  let totalChunks = 0;
  let progress = 0;
  let currentTime = 0;
  let totalTime = 0;
  let playbackRate = 1.0;
  let utterances: SpeechSynthesisUtterance[] = [];
  let cleanedText = '';
  let estimatedMinutes = 0;
  let synth: SpeechSynthesis | null = null;
  let availableVoices: SpeechSynthesisVoice[] = [];
  let selectedVoice: SpeechSynthesisVoice | null = null;
  let showVoiceSelector = false;
  let showShareMenu = false;
  let currentSentence = '';
  let textChunks: string[] = [];
  let shareSuccess = false;
  let progressBarElement: HTMLElement | null = null;
  let currentUtteranceIndex = 0;
  let needsUtteranceRecreation = true; // Start as true for first play
  let chunkToHeadingMap: (string | null)[] = []; // Maps chunk index to heading slug

  // Speed options
  const speedOptions = [
    { label: '0.75x', value: 0.75 },
    { label: '1x', value: 1.0 },
    { label: '1.25x', value: 1.25 },
    { label: '1.5x', value: 1.5 },
    { label: '1.75x', value: 1.75 },
    { label: '2x', value: 2.0 },
  ];

  onMount(async () => {
    isSupported = isTTSSupported();
    if (isSupported && content) {
      synth = window.speechSynthesis;
      cleanedText = cleanTextForSpeech(content);
      estimatedMinutes = estimateReadingTime(cleanedText);
      totalTime = estimatedMinutes * 60;
      textChunks = splitIntoChunks(cleanedText);

      // Load voices
      availableVoices = await getAvailableVoices();
      // Prefer English voices
      selectedVoice =
        availableVoices.find((v) => v.lang.startsWith('en-')) || availableVoices[0] || null;

      // Check URL for timestamp
      const urlParams = new URLSearchParams(window.location.search);
      const timestamp = urlParams.get('audiotime');
      if (timestamp) {
        const time = parseInt(timestamp, 10);
        if (!isNaN(time)) {
          currentTime = time;
          progress = (time / totalTime) * 100;
        }
      }

      // Keyboard shortcuts
      window.addEventListener('keydown', handleKeyPress);
    }
  });

  onDestroy(() => {
    stop();
    if (typeof window !== 'undefined') {
      window.removeEventListener('keydown', handleKeyPress);
    }
  });

  function handleKeyPress(e: KeyboardEvent) {
    // Ignore if user is typing in an input
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
      return;
    }

    switch (e.key) {
      case ' ':
        e.preventDefault();
        togglePlayPause();
        break;
      case 'ArrowLeft':
        e.preventDefault();
        changeSpeed(Math.max(0.5, playbackRate - 0.25));
        break;
      case 'ArrowRight':
        e.preventDefault();
        changeSpeed(Math.min(2.0, playbackRate + 0.25));
        break;
      case 'Escape':
        if (isPlaying || isPaused) {
          e.preventDefault();
          stop();
        }
        break;
    }
  }

  function prepareUtterances() {
    if (!synth) return;

    const chunks = splitIntoChunks(cleanedText);
    totalChunks = chunks.length;
    utterances = [];

    console.log('Preparing utterances with voice:', selectedVoice?.name || 'default'); // Debug

    chunks.forEach((chunk, index) => {
      const utterance = new SpeechSynthesisUtterance(chunk);
      utterance.rate = playbackRate;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;
      if (selectedVoice) {
        utterance.voice = selectedVoice;
      }

      utterance.onstart = () => {
        currentChunkIndex = index;
        currentUtteranceIndex = index;
        isPlaying = true; // Ensure state is updated
        // Extract first sentence for display (up to 200 chars)
        const sentences = chunk.split(/[.!?]+/).filter(s => s.trim().length > 0);
        const firstSentence = sentences[0]?.trim() || chunk.substring(0, 200);
        currentSentence = firstSentence.substring(0, 200) + (firstSentence.length > 200 ? '...' : '');
        console.log('Speaking:', currentSentence); // Debug log

        updateProgress();
      };

      utterance.onend = () => {
        if (index === chunks.length - 1) {
          // All chunks finished
          isPlaying = false;
          isPaused = false;
          currentChunkIndex = 0;
          progress = 0;
          currentTime = 0;
          currentSentence = '';
        } else {
          // Move to next chunk
          currentUtteranceIndex = index + 1;
        }
      };

      utterance.onerror = (event) => {
        console.error('Speech synthesis error:', event);
        isPlaying = false;
        isPaused = false;
        currentSentence = '';
      };

      utterances.push(utterance);
    });
  }

  function updateProgress() {
    if (totalChunks > 0) {
      progress = ((currentChunkIndex + 1) / totalChunks) * 100;
      currentTime = (progress / 100) * totalTime;
    }
  }

  function play(fromIndex: number = 0) {
    if (!synth || !cleanedText) return;

    // Resume if just paused and no changes needed
    if (isPaused && !needsUtteranceRecreation && fromIndex === currentUtteranceIndex) {
      synth.resume();
      isPlaying = true;
      isPaused = false;
      console.log('Resuming playback');
      return;
    }

    // Otherwise recreate utterances
    prepareUtterances();
    needsUtteranceRecreation = false;
    
    isPlaying = true;
    isPaused = false;
    currentChunkIndex = fromIndex;
    currentUtteranceIndex = fromIndex;

    console.log('Playing from index', fromIndex, 'with voice:', selectedVoice?.name); // Debug
    
    // Speak utterances from the specified index
    for (let i = fromIndex; i < utterances.length; i++) {
      synth.speak(utterances[i]);
    }
  }

  function pause() {
    if (!synth) return;
    synth.pause();
    isPlaying = false;
    isPaused = true;
  }

  function stop() {
    if (!synth) return;
    synth.cancel();
    isPlaying = false;
    isPaused = false;
    currentChunkIndex = 0;
    progress = 0;
    currentTime = 0;
    currentSentence = ''; // Clear transcript
  }

  function togglePlayPause() {
    if (isPlaying) {
      pause();
    } else {
      play();
    }
  }

  function changeSpeed(newRate: number) {
    playbackRate = newRate;
    needsUtteranceRecreation = true;
    
    const wasPlaying = isPlaying;
    const wasPaused = isPaused;
    const savedIndex = currentUtteranceIndex;
    
    if (wasPlaying || wasPaused) {
      stop();
      setTimeout(() => {
        play(savedIndex);
      }, 50);
    }
  }

  function selectVoice(voice: SpeechSynthesisVoice) {
    selectedVoice = voice;
    showVoiceSelector = false;
    needsUtteranceRecreation = true;
    console.log('Voice selected:', voice.name, voice.lang); // Debug log
    
    const wasPlaying = isPlaying;
    const wasPaused = isPaused;
    const savedIndex = currentUtteranceIndex;
    
    // Always stop and recreate utterances with new voice
    stop();
    
    if (wasPlaying || wasPaused) {
      setTimeout(() => {
        play(savedIndex);
      }, 100);
    }
  }

  function seekTo(percentage: number) {
    if (!synth || totalChunks === 0) return;

    // Calculate which chunk corresponds to this percentage
    const targetIndex = Math.floor((percentage / 100) * totalChunks);
    const wasPlaying = isPlaying;

    // Stop current playback
    stop();
    needsUtteranceRecreation = true;

    // Update progress indicators
    currentChunkIndex = targetIndex;
    currentUtteranceIndex = targetIndex;
    progress = (targetIndex / totalChunks) * 100;
    currentTime = (progress / 100) * totalTime;

    // Start playing from this position if we were playing
    if (wasPlaying) {
      setTimeout(() => {
        play(targetIndex);
      }, 100);
    } else {
      // Just update the position
      isPaused = true;
    }
  }

  function handleProgressBarClick(e: MouseEvent) {
    if (!progressBarElement) return;

    const rect = progressBarElement.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = (x / rect.width) * 100;

    seekTo(Math.max(0, Math.min(100, percentage)));
  }

  function mapChunksToHeadings() {
    if (headings.length === 0 || textChunks.length === 0) {
      return textChunks.map(() => null);
    }

    // Sort headings by their position in text (using text content matching)
    const sortedHeadings = headings
      .map((h) => ({
        ...h,
        textLower: h.text.toLowerCase(),
        position: cleanedText.toLowerCase().indexOf(h.text.toLowerCase()),
      }))
      .filter((h) => h.position !== -1)
      .sort((a, b) => a.position - b.position);

    console.log('Available headings:', sortedHeadings.map((h) => h.text));

    // For each chunk, find which heading section it belongs to
    return textChunks.map((chunk, chunkIdx) => {
      let cumulativeLength = 0;
      let chunkPosition = 0;

      // Calculate this chunk's approximate position in the text
      for (let i = 0; i < chunkIdx; i++) {
        cumulativeLength += textChunks[i].length;
      }
      chunkPosition = cumulativeLength;

      // Find the heading that precedes this chunk
      let currentHeading = null;
      for (const heading of sortedHeadings) {
        if (heading.position <= chunkPosition) {
          currentHeading = heading.slug;
        } else {
          break;
        }
      }

      console.log(`Chunk ${chunkIdx}: position ~${chunkPosition}, heading: ${currentHeading}`);
      return currentHeading;
    });
  }

  function manualScrollToHeading() {
    // Simply scroll to the article
    console.log('[AudioPlayer] manualScrollToHeading button clicked');
    scrollToArticle();
  }

  function scrollToArticle() {
    const selector = scrollTargetSelector || '#article-content';
    console.log('[AudioPlayer] scrollToArticle called with selector:', selector);
    const element = document.querySelector(selector);
    console.log('[AudioPlayer] Found element:', element);
    if (element) {
      console.log('[AudioPlayer] Scrolling to element');
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      console.error(`[AudioPlayer] Element not found with selector: ${selector}`);
      // Try alternate selectors for debugging
      console.log('[AudioPlayer] Trying alternate selectors:');
      console.log('  - [#article-content]:', document.querySelector('#article-content'));
      console.log('  - [article]:', document.querySelector('article'));
      console.log('  - All articles:', document.querySelectorAll('article'));
    }
  }

  async function sharePosition() {
    const url = new URL(window.location.href);
    url.searchParams.set('audiotime', Math.floor(currentTime).toString());
    const shareUrl = url.toString();

    try {
      await navigator.clipboard.writeText(shareUrl);
      shareSuccess = true;
      setTimeout(() => {
        shareSuccess = false;
        showShareMenu = false;
      }, 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
      // Fallback: show URL in alert
      alert(`Share this link:\n${shareUrl}`);
    }
  }

  function getVoiceLabel(voice: SpeechSynthesisVoice): string {
    // Format: "English (US) - Samantha"
    const langPart = voice.lang.replace('-', ' (').replace(/([A-Z]{2})$/, '$1)');
    return `${voice.name} (${langPart})`;
  }

</script>

{#if isSupported && content}
  <div
    class="audio-player sticky top-16 z-40 mb-6 rounded-xl border border-border bg-background/95 backdrop-blur-sm shadow-lg"
  >
    <!-- Main Player Controls -->
    <div class="p-4">
      <div class="flex items-center gap-4">
        <!-- Play/Pause Button -->
        <button
          on:click={togglePlayPause}
          class="shrink-0 flex items-center justify-center w-12 h-12 rounded-full bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-md"
          aria-label={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
          title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
        >
          {#if isPlaying}
            <!-- Pause Icon -->
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="currentColor"
              stroke="none"
            >
              <rect x="6" y="4" width="4" height="16" rx="1" />
              <rect x="14" y="4" width="4" height="16" rx="1" />
            </svg>
          {:else}
            <!-- Play Icon -->
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="currentColor"
              stroke="none"
            >
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
          {/if}
        </button>

        <!-- Info & Progress -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                class="text-muted-foreground"
              >
                <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" x2="12" y1="19" y2="22" />
              </svg>
              <span class="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Listen to Article
              </span>
            </div>
            <span class="text-xs text-muted-foreground tabular-nums">
              {formatTime(currentTime)} / ~{formatTime(totalTime)}
            </span>
          </div>

          <!-- Progress Bar -->
          <div
            bind:this={progressBarElement}
            on:click={handleProgressBarClick}
            class="relative h-2 bg-secondary rounded-full overflow-hidden cursor-pointer hover:h-3 transition-all"
            role="slider"
            aria-label="Audio progress"
            aria-valuemin="0"
            aria-valuemax="100"
            aria-valuenow={progress}
            tabindex="0"
            on:keydown={(e) => {
              if (e.key === 'ArrowLeft') {
                seekTo(Math.max(0, progress - 5));
              } else if (e.key === 'ArrowRight') {
                seekTo(Math.min(100, progress + 5));
              }
            }}
          >
            <div
              class="absolute top-0 left-0 h-full bg-primary transition-all duration-300"
              style="width: {progress}%"
            />
          </div>

          <div class="flex items-center justify-between mt-2">
            <span class="text-xs text-muted-foreground">
              ~{estimatedMinutes} min read • Click bar to seek • Use ← → for speed
            </span>

            <!-- Speed Controls -->
            <div class="flex items-center gap-1">
              {#each speedOptions as speed}
                <button
                  on:click={() => changeSpeed(speed.value)}
                  class="px-2 py-1 text-xs font-medium rounded transition-colors {playbackRate ===
                  speed.value
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-secondary'}"
                  title="Speed {speed.label}"
                >
                  {speed.label}
                </button>
              {/each}
            </div>
          </div>
        </div>

        <!-- Additional Controls -->
        <div class="flex items-center gap-2">
          <!-- Voice Selector -->
          <div class="relative">
            <button
              on:click={() => (showVoiceSelector = !showVoiceSelector)}
              class="shrink-0 flex items-center justify-center w-10 h-10 rounded-full bg-secondary text-foreground hover:bg-secondary/80 transition-colors"
              aria-label="Select Voice"
              title="Select Voice"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path
                  d="M17 14h.01M7 7h12a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14"
                />
                <path d="m16 10-4 4-4-4" />
              </svg>
            </button>

            {#if showVoiceSelector}
              <div
                class="absolute right-0 mt-2 w-64 max-h-64 overflow-y-auto rounded-lg border border-border bg-background shadow-xl z-50"
              >
                <div class="p-2">
                  <div class="text-xs font-bold uppercase tracking-wider text-muted-foreground px-2 py-1">
                    Select Voice
                  </div>
                  {#each availableVoices as voice}
                    <button
                      on:click={() => selectVoice(voice)}
                      class="w-full text-left px-2 py-2 text-sm rounded hover:bg-secondary transition-colors {selectedVoice?.name ===
                      voice.name
                        ? 'bg-primary/10 text-primary font-medium'
                        : 'text-foreground'}"
                    >
                      {voice.name}
                      <span class="text-xs text-muted-foreground block">{voice.lang}</span>
                    </button>
                  {/each}
                </div>
              </div>
            {/if}
          </div>

          <!-- Share Position -->
          <div class="relative">
            <button
              on:click={sharePosition}
              class="shrink-0 flex items-center justify-center w-10 h-10 rounded-full bg-secondary text-foreground hover:bg-secondary/80 transition-colors"
              aria-label="Share Position"
              title="Share Position"
              disabled={!isPlaying && !isPaused}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <circle cx="18" cy="5" r="3" />
                <circle cx="6" cy="12" r="3" />
                <circle cx="18" cy="19" r="3" />
                <line x1="8.59" x2="15.42" y1="13.51" y2="17.49" />
                <line x1="15.41" x2="8.59" y1="6.51" y2="10.49" />
              </svg>
            </button>

            {#if shareSuccess}
              <div
                class="absolute right-0 mt-2 px-3 py-2 rounded-lg border border-border bg-background shadow-xl text-xs font-medium text-primary whitespace-nowrap"
              >
                ✓ Link copied!
              </div>
            {/if}
          </div>

          <!-- Stop Button -->
          {#if isPlaying || isPaused}
            <button
              on:click={stop}
              class="shrink-0 flex items-center justify-center w-10 h-10 rounded-full bg-secondary text-foreground hover:bg-secondary/80 transition-colors"
              aria-label="Stop (Esc)"
              title="Stop (Esc)"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="currentColor"
                stroke="none"
              >
                <rect x="6" y="6" width="12" height="12" rx="2" />
              </svg>
            </button>
          {/if}
        </div>
      </div>
    </div>

    <!-- Current Sentence Display -->
    {#if isPlaying || isPaused}
      <div
        class="border-t border-border bg-secondary/30 px-4 py-3 text-sm text-foreground/80 italic"
      >
        <div class="flex items-start gap-2">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="text-primary shrink-0 mt-0.5"
          >
            <path d="m3 16 4 4 4-4" />
            <path d="M7 20V4" />
            <path d="m21 8-4-4-4 4" />
            <path d="M17 4v16" />
          </svg>
          <div class="flex-1">
            <p class="mb-2">
              {#if currentSentence}
                {currentSentence}
              {:else}
                <span class="text-muted-foreground">Starting...</span>
              {/if}
            </p>
            <button
              type="button"
              on:click={manualScrollToHeading}
              class="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:text-primary/80 hover:underline transition-colors cursor-pointer bg-none border-none p-0"
              aria-label="Scroll to article content"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              Scroll to Article
            </button>
          </div>
        </div>
      </div>
    {/if}
  </div>
{:else if !isSupported}
  <div
    class="mb-6 p-4 rounded-xl border border-border bg-secondary/30 text-muted-foreground text-sm"
  >
    <p>
      ⚠️ Audio playback is not supported in your browser. Please try Chrome, Edge, or Safari for the
      best experience.
    </p>
  </div>
{/if}

<style>
  .audio-player {
    animation: slideDown 0.3s ease-out;
  }

  @keyframes slideDown {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
