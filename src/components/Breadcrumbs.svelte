<script lang="ts">
  interface Props {
    items: { name: string; href: string }[];
  }

  let { items }: Props = $props();
</script>

<nav
  class="flex items-center flex-wrap gap-x-2 gap-y-1 text-xs font-bold uppercase tracking-widest text-muted-foreground mb-8 sm:mb-12"
  aria-label="Breadcrumb"
>
  <a href="/" class="hover:text-primary transition-colors flex items-center shrink-0"> Home </a>

  {#each items as item (item.name)}
    <span class="text-border shrink-0">/</span>
    <a
      href={item.href}
      class="hover:text-primary transition-colors {item.href === '#'
        ? 'pointer-events-none'
        : ''} truncate max-w-[150px] sm:max-w-none"
    >
      {item.name}
    </a>
  {/each}
</nav>
