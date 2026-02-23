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

      // Load voices
      availableVoices = await getAvailableVoices();
      // Prefer English voices
      selectedVoice =
        availableVoices.find((v) => v.lang.startsWith('en-')) || availableVoices[0] || null;
    }
  });

  onDestroy(() => {
    stop();
  });

  function prepareUtterances() {
    if (!synth) return;

    const chunks = splitIntoChunks(cleanedText);
    totalChunks = chunks.length;
    utterances = [];

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
        }
      };

      utterance.onerror = (event) => {
        console.error('Speech synthesis error:', event);
        isPlaying = false;
        isPaused = false;
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

  function play() {
    if (!synth || !cleanedText) return;

    if (isPaused) {
      // Resume
      synth.resume();
      isPlaying = true;
      isPaused = false;
    } else {
      // Start fresh
      prepareUtterances();
      isPlaying = true;
      isPaused = false;

      // Speak all utterances in sequence
      utterances.forEach((utterance) => {
        synth.speak(utterance);
      });
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
  }

  function togglePlayPause() {
    if (isPlaying) {
      pause();
    } else {
      play();
    }
  }

  function changeSpeed(newRate: number) {
    const wasPlaying = isPlaying;
    stop();
    playbackRate = newRate;
    if (wasPlaying) {
      play();
    }
  }
</script>

{#if isSupported && content}
  <div
    class="audio-player sticky top-16 z-40 mb-6 rounded-xl border border-border bg-background/95 backdrop-blur-sm shadow-lg p-4"
  >
    <div class="flex items-center gap-4">
      <!-- Play/Pause Button -->
      <button
        on:click={togglePlayPause}
        class="shrink-0 flex items-center justify-center w-12 h-12 rounded-full bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-md"
        aria-label={isPlaying ? 'Pause' : 'Play'}
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
        <div class="relative h-2 bg-secondary rounded-full overflow-hidden">
          <div
            class="absolute top-0 left-0 h-full bg-primary transition-all duration-300"
            style="width: {progress}%"
          />
        </div>

        <div class="flex items-center justify-between mt-2">
          <span class="text-xs text-muted-foreground">
            ~{estimatedMinutes} min read
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
              >
                {speed.label}
              </button>
            {/each}
          </div>
        </div>
      </div>

      <!-- Stop Button -->
      {#if isPlaying || isPaused}
        <button
          on:click={stop}
          class="shrink-0 flex items-center justify-center w-10 h-10 rounded-full bg-secondary text-foreground hover:bg-secondary/80 transition-colors"
          aria-label="Stop"
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
