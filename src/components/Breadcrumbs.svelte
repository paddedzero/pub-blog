<script lang="ts">
  import { SITE } from '@/config';

  interface Props {
    items: { name: string; href: string }[];
  }

  let { items }: Props = $props();

  const base = SITE.base;

  const normalizeHref = (href: string) => {
    if (!href || href === '#') return href;
    if (/^(https?:)?\/\//.test(href) || href.startsWith('mailto:') || href.startsWith('tel:')) {
      return href;
    }
    if (href.startsWith(base)) return href;
    if (href.startsWith('/')) return `${base}${href.replace(/^\/+/, '')}`;
    return `${base}${href.replace(/^\/+/, '')}`;
  };
</script>

<nav
  class="flex items-center flex-wrap gap-x-2 gap-y-1 text-xs font-bold uppercase tracking-widest text-muted-foreground mb-8 sm:mb-12"
  aria-label="Breadcrumb"
>
  <a href={base} class="hover:text-primary transition-colors flex items-center shrink-0"> Home </a>

  {#each items as item (item.name)}
    <span class="text-border shrink-0">/</span>
    <a
      href={normalizeHref(item.href)}
      class="hover:text-primary transition-colors {item.href === '#'
        ? 'pointer-events-none'
        : ''} truncate max-w-[150px] sm:max-w-none"
    >
      {item.name}
    </a>
  {/each}
</nav>
