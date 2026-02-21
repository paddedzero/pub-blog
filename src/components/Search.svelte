<script lang="ts">
  import { onMount } from 'svelte';
  import { uiState } from '@/lib/ui.svelte';

  function handleKeydown(e: KeyboardEvent) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      uiState.openSearch();
    }
  }

  onMount(() => {
    window.addEventListener('keydown', handleKeydown);
    return () => window.removeEventListener('keydown', handleKeydown);
  });
</script>

<button
  onclick={() => uiState.openSearch()}
  class="group flex items-center gap-2 px-3 py-2 rounded-md bg-secondary/50 hover:bg-secondary text-muted-foreground hover:text-foreground transition-all duration-200 border border-transparent hover:border-border/50"
  aria-label="Search"
>
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
    class="opacity-70 group-hover:opacity-100 transition-opacity"
  >
    <circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />
  </svg>
  <span class="hidden sm:inline-block text-xs font-semibold opacity-80 group-hover:opacity-100"
    >Search</span
  >
  <kbd
    class="hidden lg:inline-flex h-5 items-center gap-1 rounded border border-border bg-muted px-1.5 font-mono text-xs font-medium text-muted-foreground ml-2"
  >
    <span class="text-xs">⌘</span>K
  </kbd>
</button>
