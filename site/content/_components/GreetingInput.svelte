<script lang="ts">
  let name = $state('');
</script>

<div
  class="my-10 sm:my-16 p-6 sm:p-10 lg:p-12 border border-border rounded-2xl bg-card shadow-lg sm:shadow-xl transition-all duration-500"
>
  <div class="flex flex-col gap-6">
    <div class="space-y-3">
      <input
        type="text"
        bind:value={name}
        placeholder="What's your name?"
        class="flex h-12 sm:h-14 w-full rounded-xl border border-input bg-background px-4 py-2 text-base sm:text-lg ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-all font-sans"
      />
    </div>

    <div class="h-10 sm:h-12 flex items-center">
      {#if name}
        <p
          class="text-lg sm:text-xl lg:text-2xl font-bold text-foreground animate-in fade-in slide-in-from-left-2 zoom-in-95 duration-500 leading-tight"
        >
          Hello, <span
            class="text-primary font-black underline underline-offset-4 decoration-2 decoration-primary/40"
            >{name}</span
          >! 👋
        </p>
      {/if}
    </div>
  </div>
</div>
