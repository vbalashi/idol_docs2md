#!/usr/bin/env python3
"""
Test script for the pipeline functionality (without TUI).
Tests site scanning and parsing capabilities.
"""

import sys
from pathlib import Path

# Import the pipeline module
sys.path.insert(0, str(Path(__file__).parent))

# Import function from 04_pipeline.py
import importlib.util
_pipeline_path = Path(__file__).parent / "04_pipeline.py"
_spec = importlib.util.spec_from_file_location("pipeline_module", str(_pipeline_path))
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load pipeline module from {_pipeline_path}")
_pipeline = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pipeline)
scan_documentation_site = _pipeline.scan_documentation_site

def test_scan():
    """Test scanning the documentation site."""
    test_url = "https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/"
    
    print("Testing documentation site scanning...")
    print(f"URL: {test_url}\n")
    
    items = scan_documentation_site(test_url)
    
    if not items:
        print("⚠ No items found")
        return False
    
    print(f"\n✓ Found {len(items)} documentation items:\n")
    
    # Group by category
    by_category = {}
    for item in items:
        cat = item.category or "Uncategorized"
        by_category.setdefault(cat, []).append(item)
    
    for category in sorted(by_category.keys()):
        print(f"\n{category}:")
        for item in by_category[category]:
            print(f"  • {item.name}")
            print(f"    {item.zip_url}")
    
    return True

if __name__ == "__main__":
    try:
        success = test_scan()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n✗ Interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

