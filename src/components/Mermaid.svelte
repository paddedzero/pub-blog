<script lang="ts">
  import { onMount } from 'svelte';

  interface Props {
    chart: string;
  }

  let { chart }: Props = $props();
  let svgContent = $state('');
  let error = $state('');
  let mermaidModule: typeof import('mermaid') | null = null;

  async function renderDiagram() {
    if (!mermaidModule) return;

    const mermaid = mermaidModule.default;
    const isDark = document.documentElement.classList.contains('dark');

    mermaid.initialize({
      startOnLoad: false,
      theme: isDark ? 'base' : 'default',
      securityLevel: 'loose',
      fontFamily: 'Outfit, sans-serif',
      themeVariables: isDark
        ? {
            primaryColor: '#c4b5fd',
            primaryTextColor: '#18181b',
            primaryBorderColor: '#a78bfa',
            lineColor: '#D1D5DC',
            secondaryColor: '#c4b5fd',
            tertiaryColor: '#c4b5fd',
            mainBkg: '#c4b5fd',
            nodeBorder: '#a78bfa',
            titleColor: '#18181b',
            edgeLabelBackground: 'transparent',
          }
        : {
            lineColor: '#94a3b8',
            edgeLabelBackground: '#ffffff',
          },
      themeCSS: `
        .node rect, .node circle, .node polygon, .node path { stroke-width: 1px; }

        /* 1. Artifact Fix: Hide ONLY the specific phantom labels */
        g.edgeLabel g.label[data-id="L_D_F_0"],
        g.edgeLabel g.label[data-id="L_D_G_0"] {
          display: none !important;
        }

        /* 2. Edge Label Styling - transparent background for dark theme */
        .edgeLabel .labelBkg {
          fill: ${isDark ? 'transparent' : '#ffffff'} !important;
          opacity: 1 !important;
        }

        .edgeLabel rect {
          fill: ${isDark ? 'transparent' : '#ffffff'} !important;
          stroke: none !important;
        }

        /* Handle ALL edge label elements (foreignObject content) */
        .edgeLabel foreignObject,
        .edgeLabel foreignObject * {
          background: ${isDark ? 'transparent' : '#ffffff'} !important;
          background-color: ${isDark ? 'transparent' : '#ffffff'} !important;
        }

        .edgeLabel .nodeLabel,
        .edgeLabel span,
        .edgeLabel p,
        .edgeLabel div {
          background: ${isDark ? 'transparent' : '#ffffff'} !important;
          background-color: ${isDark ? 'transparent' : '#ffffff'} !important;
          color: ${isDark ? '#EAEDF3' : '#18181b'} !important;
          border: none !important;
          box-shadow: none !important;
        }

        /* 3. Node text - dark text on light backgrounds */
        .node .label,
        .node .label *,
        .node .nodeLabel,
        .node foreignObject *,
        .node text {
          fill: #18181b !important;
          color: #18181b !important;
        }

        /* 4. Connection Fix: Ensure paths are visible */
        .edgePath .path {
          stroke: ${isDark ? '#D1D5DC' : '#94a3b8'} !important;
          stroke-width: 1.5px !important;
          opacity: 1 !important;
        }

        #L_D_F_0, [id*="L_D_F"] {
          stroke: ${isDark ? '#D1D5DC' : '#94a3b8'} !important;
          stroke-width: 2px !important;
          display: block !important;
        }
      `,
    });

    try {
      const { svg } = await mermaid.render('mermaid-' + Math.random().toString(36).slice(2), chart);
      svgContent = svg;
      error = '';
    } catch (err) {
      console.error('Mermaid rendering error:', err);
      error = String(err);
    }
  }

  onMount(() => {
    let observer: MutationObserver | undefined;

    (async () => {
      try {
        mermaidModule = await import('mermaid');
        await renderDiagram();

        // Watch for theme changes
        observer = new MutationObserver((mutations) => {
          for (const mutation of mutations) {
            if (mutation.attributeName === 'class') {
              renderDiagram();
              break;
            }
          }
        });

        observer.observe(document.documentElement, { attributes: true });
      } catch (err) {
        console.error('Mermaid loading error:', err);
        error = String(err);
      }
    })();

    return () => {
      if (observer) observer.disconnect();
    };
  });
</script>

{#if error}
  <div class="my-6 p-4 rounded-lg bg-destructive/10 text-destructive border border-destructive/20">
    <pre class="text-xs whitespace-pre-wrap">{error}</pre>
  </div>
{:else if !svgContent}
  <div
    class="flex items-center justify-center p-16 bg-muted/20 rounded-xl border border-dashed border-border/50 animate-pulse transition-all"
  >
    <div class="flex flex-col items-center gap-3">
      <div
        class="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin"
      ></div>
      <div class="text-xs text-muted-foreground font-medium uppercase tracking-wider">
        Generating Diagram
      </div>
    </div>
  </div>
{:else}
  <div
    class="mermaid-container my-10 flex justify-center bg-card p-10 rounded-2xl border border-border/60 shadow-lg overflow-hidden transition-all duration-500 ease-in-out"
  >
    {@html svgContent}
  </div>
{/if}

<style>
  .mermaid-container :global(svg) {
    max-width: 100%;
    height: auto;
  }
</style>
