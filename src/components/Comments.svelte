<script lang="ts">
  import { onMount } from 'svelte';
  import { SITE } from '@/config';
  import { theme } from '@/lib/theme.svelte';

  const config = SITE.comments;

  let giscusContainer = $state<HTMLDivElement | null>(null);
  let mounted = $state(false);

  // Map our theme to Giscus theme
  $effect(() => {
    if (!mounted || !giscusContainer) return;

    const currentTheme = theme.current;
    const resolvedTheme =
      currentTheme === 'system'
        ? window.matchMedia('(prefers-color-scheme: dark)').matches
          ? 'dark'
          : 'light'
        : currentTheme;

    const giscusTheme =
      config.theme === 'preferred_color_scheme'
        ? resolvedTheme === 'dark'
          ? 'transparent_dark'
          : 'light'
        : config.theme;

    // Update Giscus theme if already loaded
    const iframe = giscusContainer.querySelector<HTMLIFrameElement>('iframe.giscus-frame');
    if (iframe) {
      iframe.contentWindow?.postMessage(
        {
          giscus: {
            setConfig: {
              theme: giscusTheme,
            },
          },
        },
        'https://giscus.app'
      );
    }
  });

  onMount(() => {
    if (!config.enabled || !giscusContainer) return;

    const currentTheme = theme.current;
    const resolvedTheme =
      currentTheme === 'system'
        ? window.matchMedia('(prefers-color-scheme: dark)').matches
          ? 'dark'
          : 'light'
        : currentTheme;

    const giscusTheme =
      config.theme === 'preferred_color_scheme'
        ? resolvedTheme === 'dark'
          ? 'transparent_dark'
          : 'light'
        : config.theme;

    const script = document.createElement('script');
    script.src = 'https://giscus.app/client.js';
    script.setAttribute('data-repo', config.repo);
    script.setAttribute('data-repo-id', config.repoId);
    script.setAttribute('data-category', config.category);
    script.setAttribute('data-category-id', config.categoryId);
    script.setAttribute('data-mapping', config.mapping);
    script.setAttribute('data-strict', '0');
    script.setAttribute('data-reactions-enabled', config.reactionsEnabled ? '1' : '0');
    script.setAttribute('data-emit-metadata', config.emitMetadata ? '1' : '0');
    script.setAttribute('data-input-position', config.inputPosition);
    script.setAttribute('data-theme', giscusTheme);
    script.setAttribute('data-lang', config.lang);
    script.setAttribute('data-loading', 'lazy');
    script.crossOrigin = 'anonymous';
    script.async = true;

    // eslint-disable-next-line svelte/no-dom-manipulating
    giscusContainer.appendChild(script);
    mounted = true;
  });
</script>

{#if config.enabled}
  <section class="mt-16 pt-12 border-t border-border">
    <h2 class="text-2xl font-bold text-foreground mb-6">Comments</h2>
    <div bind:this={giscusContainer} class="giscus"></div>
  </section>
{/if}

<style>
  :global(.giscus) {
    width: 100%;
  }

  :global(.giscus-frame) {
    width: 100%;
    border: none;
  }
</style>
