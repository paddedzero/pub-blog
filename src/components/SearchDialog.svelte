<script lang="ts">
  import { onMount } from 'svelte';
  import { uiState } from '@/lib/ui.svelte';

  interface Post {
    id: string;
    data: {
      title: string;
      description: string;
    };
  }

  let posts = $state<Post[]>([]);
  let query = $state('');

  let filteredPosts = $derived(
    query.length > 0
      ? posts.filter(
          (post) =>
            post.data.title.toLowerCase().includes(query.toLowerCase()) ||
            post.data.description.toLowerCase().includes(query.toLowerCase())
        )
      : []
  );

  let searchInput = $state<HTMLInputElement>();

  $effect(() => {
    if (uiState.isSearchOpen && searchInput) {
      setTimeout(() => searchInput?.focus(), 10);
    }
  });

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      uiState.closeSearch();
    }
  }

  onMount(() => {
    window.addEventListener('keydown', handleKeydown);

    (async () => {
      try {
        const res = await fetch('/api/search.json');
        if (res.ok) {
          posts = await res.json();
        }
      } catch (err) {
        console.error('Failed to load search index:', err);
      }
    })();

    return () => window.removeEventListener('keydown', handleKeydown);
  });
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="fixed inset-0 z-[100] flex items-start justify-center pt-8 sm:pt-24 px-4 bg-black/40 backdrop-blur-[4px] transition-all"
  onclick={() => uiState.closeSearch()}
>
  <div
    class="w-full max-w-2xl bg-card border border-border rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200"
    onclick={(e) => e.stopPropagation()}
  >
    <div class="flex items-center gap-3 p-4 sm:p-6 border-b border-border bg-background/50">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="w-5 h-5 sm:w-6 sm:h-6 text-muted-foreground"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />
      </svg>
      <input
        bind:this={searchInput}
        bind:value={query}
        type="text"
        placeholder="Search post titles or descriptions..."
        class="flex-1 bg-transparent border-none outline-none text-base sm:text-lg text-foreground placeholder:text-muted-foreground/40 font-medium"
      />
      <button
        onclick={() => uiState.closeSearch()}
        class="sm:hidden text-xs font-bold uppercase tracking-widest text-muted-foreground"
      >
        Cancel
      </button>
    </div>

    <div class="max-h-[60vh] sm:max-h-[400px] 3xl:max-h-[600px] overflow-y-auto p-2 sm:p-4">
      {#if query.length === 0}
        <div class="p-12 text-center">
          <p class="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
            Start typing to search...
          </p>
        </div>
      {:else if filteredPosts.length === 0}
        <div class="p-12 text-center">
          <p class="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
            No results found for "{query}"
          </p>
        </div>
      {:else}
        <div class="space-y-1">
          {#each filteredPosts as post (post.id)}
            <a
              href={`/posts/${post.id}`}
              class="block p-4 sm:p-5 rounded-xl hover:bg-accent transition-all no-underline group"
              onclick={() => uiState.closeSearch()}
            >
              <h3
                class="text-sm sm:text-base font-bold text-foreground group-hover:text-primary transition-colors mb-1"
              >
                {post.data.title}
              </h3>
              <p class="text-xs sm:text-sm text-muted-foreground line-clamp-1 opacity-80">
                {post.data.description}
              </p>
            </a>
          {/each}
        </div>
      {/if}
    </div>

    <div
      class="hidden sm:flex items-center justify-between px-6 py-3 border-t border-border bg-secondary/30"
    >
      <div class="flex items-center gap-6">
        <div class="flex items-center gap-2">
          <kbd
            class="px-1.5 py-0.5 text-xs font-bold bg-background border border-border rounded shadow-sm"
            >⏎</kbd
          >
          <span class="text-xs font-bold uppercase tracking-widest text-muted-foreground"
            >to select</span
          >
        </div>
        <div class="flex items-center gap-2">
          <kbd
            class="px-1.5 py-0.5 text-xs font-bold bg-background border border-border rounded shadow-sm"
            >↑↓</kbd
          >
          <span class="text-xs font-bold uppercase tracking-widest text-muted-foreground"
            >to navigate</span
          >
        </div>
      </div>
      <div class="flex items-center gap-2">
        <kbd
          class="px-1.5 py-0.5 text-xs font-bold bg-background border border-border rounded shadow-sm"
          >esc</kbd
        >
        <span class="text-xs font-bold uppercase tracking-widest text-muted-foreground"
          >to close</span
        >
      </div>
    </div>
  </div>
</div>
