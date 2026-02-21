<script lang="ts">
  import { getLangFlag } from '@/lib/utils/lang';

  export let translations: Record<string, string>;
</script>

<div
  class="flex flex-wrap items-center gap-2 mb-6 p-3 bg-secondary/30 rounded-lg border border-border/50"
>
  <span class="text-xs font-bold uppercase tracking-widest text-muted-foreground mr-1">
    Available in:
  </span>
  {#each Object.entries(translations) as [lang, slug] (lang)}
    <a
      href={`/posts/${slug}`}
      class="inline-flex items-center gap-1.5 px-2 py-1 round text-xs font-bold uppercase tracking-wide bg-background text-foreground hover:text-primary border border-border transition-colors no-underline"
    >
      <span class="text-sm leading-none">{getLangFlag(lang)}</span>
      {lang.toUpperCase()}
    </a>
  {/each}
</div>
