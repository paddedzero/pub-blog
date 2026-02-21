export const uiState = $state({
  isSearchOpen: false,
  toggleSearch() {
    this.isSearchOpen = !this.isSearchOpen;
  },
  openSearch() {
    this.isSearchOpen = true;
  },
  closeSearch() {
    this.isSearchOpen = false;
  },
});
