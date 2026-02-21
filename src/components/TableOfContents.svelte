<script lang="ts">
  import { onMount } from 'svelte';

  interface Heading {
    depth: number;
    text: string;
    slug: string;
  }

  interface Props {
    headings: Heading[];
  }

  let { headings }: Props = $props();
  let activeId = $state('');

  onMount(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            activeId = entry.target.id;
          }
        });
      },
      { rootMargin: '-100px 0px -66%' }
    );

    headings.forEach((heading) => {
      const element = document.getElementById(heading.slug);
      if (element) observer.observe(element);
    });

    return () => observer.disconnect();
  });

  const handleClick = (e: MouseEvent, slug: string) => {
    e.preventDefault();
    const element = document.getElementById(slug);
    if (element) {
      const offset = 100;
      const elementPosition = element.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - offset;

      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth',
      });

      history.pushState(null, '', `#${slug}`);
    }
  };
</script>

{#if headings.length > 0}
  <nav
    class="sticky top-32 lg:top-40 max-h-[calc(100vh-160px)] overflow-y-auto pl-2 pr-4 scrollbar-hide"
  >
    <h2 class="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground mb-6 opacity-80">
      On this page
    </h2>
    <div class="flex flex-col gap-3 relative">
      <!-- Background Vertical Line -->
      <div class="absolute left-0 top-0 bottom-0 w-px bg-border/20"></div>

      {#each headings as heading (heading.slug)}
        <a
          href={`#${heading.slug}`}
          onclick={(e) => handleClick(e, heading.slug)}
          class="group relative text-xs sm:text-sm transition-all duration-300 hover:text-primary py-1"
          style="padding-left: {Math.max(0, heading.depth - 2) * 0.75 + 1.25}rem"
        >
          <!-- Active Line Indicator -->
          <div
            class="absolute left-0 top-0 bottom-0 w-0.5 transition-all duration-300 {activeId ===
            heading.slug
              ? 'bg-primary opacity-100 scale-y-100'
              : 'bg-transparent scale-y-0'}"
          ></div>

          <span
            class={activeId === heading.slug
              ? 'text-primary font-bold'
              : 'text-muted-foreground/80'}
          >
            {heading.text}
          </span>
        </a>
      {/each}
    </div>
  </nav>
{/if}

<style>
  .scrollbar-hide::-webkit-scrollbar {
    display: none;
  }
  .scrollbar-hide {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
</style>
