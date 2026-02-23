#!/usr/bin/env python3
"""
Quick test to verify highlight deduplication logic
"""

def test_extract_highlight_urls():
    """Test that highlight URL extraction works correctly"""
    # Mock highlights data
    highlights = [
        ({"title": "Article 1", "link": "https://example.com/article1"}, 5),
        ({"title": "Article 2", "link": "https://example.com/article2"}, 3),
        ({"title": "Article 3", "link": "HTTPS://EXAMPLE.COM/ARTICLE3"}, 2),
    ]
    
    # Import the function from fetch_news
    import sys
    sys.path.insert(0, '.')
    from fetch_news import extract_highlight_urls
    
    # Extract URLs
    urls = extract_highlight_urls(highlights)
    
    # Verify
    assert len(urls) == 3, f"Expected 3 URLs, got {len(urls)}"
    assert "https://example.com/article1" in urls
    assert "https://example.com/article2" in urls
    assert "https://example.com/article3" in urls  # Should be normalized to lowercase
    
    print("✓ extract_highlight_urls test passed")
    print(f"  Extracted URLs: {urls}")


def test_filtering():
    """Test that format_entries_for_category filters correctly"""
    import sys
    sys.path.insert(0, '.')
    from fetch_news import format_entries_for_category
    
    # Mock entries with some that should be excluded
    entries = [
        {"title": "Article 1", "link": "https://example.com/article1", "summary": "Summary 1"},
        {"title": "Article 2", "link": "https://example.com/article2", "summary": "Summary 2"},
        {"title": "Article 3", "link": "https://example.com/unique", "summary": "Summary 3"},
    ]
    
    # URLs to exclude (first two articles)
    exclude_urls = {"https://example.com/article1", "https://example.com/article2"}
    
    # Format with exclusion
    result = format_entries_for_category(entries, exclude_urls=exclude_urls)
    
    # Verify only Article 3 is in the result
    assert "Article 1" not in result, "Article 1 should be excluded"
    assert "Article 2" not in result, "Article 2 should be excluded"
    assert "Article 3" in result or "unique" in result, "Article 3 should be included"
    
    print("✓ format_entries_for_category filtering test passed")
    print(f"  Result contains {result.count('<details')} articles (expected 1)")


if __name__ == "__main__":
    print("Testing deduplication logic...\n")
    
    try:
        test_extract_highlight_urls()
        print()
        test_filtering()
        print("\n✅ All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
