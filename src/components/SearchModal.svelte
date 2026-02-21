<script lang="ts">
  import { uiState } from '@/lib/ui.svelte';

  let SearchDialog = $state<any>(null);

  $effect(() => {
    if (uiState.isSearchOpen && !SearchDialog) {
      import('./SearchDialog.svelte').then((m) => (SearchDialog = m.default));
    }
  });
</script>

{#if uiState.isSearchOpen && SearchDialog}
  <SearchDialog />
{/if}
