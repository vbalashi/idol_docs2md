# TUI Interface Guide

Visual guide to using the interactive documentation selector.

## Interface Layout

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                    IDOL Documentation Selector                        ┃
┃                                                                       ┃
┃  Selected: 3/45 | Showing: 45                                        ┃
┃  No filter (press '/' to search)                                     ┃
┃                                                                       ┃
┃  > [X] Getting Started: Getting Started Guide                        ┃  ← Current item (highlighted)
┃    [ ] Text: Category                                                ┃
┃    [X] Text: Community                                               ┃
┃    [X] Text: Content                                                 ┃
┃    [ ] Text: Proxy                                                   ┃
┃    [ ] Text: View                                                    ┃
┃    [ ] Text: Document Security Administration Guide                 ┃
┃    [ ] Text: OmniGroupServer                                         ┃
┃    [ ] Text: Answer Server                                           ┃
┃    [ ] Text: Query Manipulation Server (QMS)                         ┃
┃    [ ] Connectors: Box Connector                                     ┃
┃    [ ] Connectors: Confluence Connector                              ┃
┃    ...                                                                ┃
┃                                                                       ┃
┃━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┃
┃  Press '/' to search, SPACE to toggle, 'a' to select all, 'n' to    ┃
┃  select none, ENTER to confirm, 'q' to quit                          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

## Interface Elements

### Header Section
```
┌─────────────────────────────────────┐
│  Selected: 3/45 | Showing: 45       │  ← Statistics
│  Filter: connector                   │  ← Current filter (if any)
└─────────────────────────────────────┘
```

- **Selected**: Number of items marked for processing / Total items
- **Showing**: Number of items visible after filtering
- **Filter**: Current search/filter term (if active)

### Item List
```
  > [X] Category: Component Name
  │ │└─ Selected checkbox
  │ └── Current item marker
  └──── Category prefix
```

- `>` : Current cursor position (highlighted in reverse video)
- `[X]` : Selected for processing
- `[ ]` : Not selected
- `Category:` : Grouping/category from documentation site
- `Component Name` : Documentation package name

### Footer Section
```
┌─────────────────────────────────────────────────────┐
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │  ← Separator
│  Press '/' to search, SPACE to toggle...           │  ← Help text
└─────────────────────────────────────────────────────┘
```

Shows context-sensitive help and keyboard shortcuts.

## Modes

### 1. Normal Mode (Default)

Navigate and select items.

```
┌──────────────────────────────────────┐
│  Selected: 5/45 | Showing: 45        │
│  No filter (press '/' to search)     │
└──────────────────────────────────────┘
        ↓
    Normal mode - navigate freely
```

**Available actions**:
- ↑/↓ : Move cursor
- Space : Toggle selection
- a : Select all (filtered)
- n : Deselect all (filtered)
- Enter : Confirm and process
- q : Quit

### 2. Search Mode

Filter items by typing.

```
┌──────────────────────────────────────┐
│  Selected: 5/45 | Showing: 12        │
│  Search: connector_                  │  ← Cursor shown
└──────────────────────────────────────┘
        ↓
    Search mode - type to filter
```

**Available actions**:
- Type : Add to search term
- Backspace : Remove last character
- Enter : Apply filter and return to normal mode
- Esc : Clear filter and return to normal mode

## Common Workflows

### Workflow 1: Select Specific Items

```
Start in normal mode
     ↓
Navigate with ↑↓
     ↓
Press Space on desired items
     ↓
Press Enter to confirm
```

**Example**:
```
> [ ] Item A          > [X] Item A          > [X] Item A
  [ ] Item B    →       [ ] Item B    →       [X] Item B
  [ ] Item C            [ ] Item C            [ ] Item C
  
  ↓ Navigate            Space                 ↓ Navigate
                        to select             Space to select
```

### Workflow 2: Filter and Select All

```
Press / to enter search mode
     ↓
Type search term (e.g., "connector")
     ↓
Press Enter to apply filter
     ↓
Press 'a' to select all filtered items
     ↓
Press / then Esc to clear filter (optional)
     ↓
Press Enter to confirm
```

**Example**:
```
All items visible             Only connectors visible        All visible, connectors selected
─────────────────────────────────────────────────────────────────────────────────
[ ] Category                  [X] Box Connector              [ ] Category
[ ] Content                   [X] Confluence Connector       [ ] Content
[ ] Box Connector       →     [X] Database Connector    →    [X] Box Connector
[ ] Confluence Connector      [X] SharePoint Connector       [X] Confluence Connector
[ ] Database Connector                                       [X] Database Connector
[ ] SharePoint Connector                                     [X] SharePoint Connector

    Search: "connector"           Press 'a'                      Clear filter
```

### Workflow 3: Select All Except

```
Press 'A' (Shift+A) to select all globally
     ↓
Press / and type exclusion term
     ↓
Press Enter to apply filter
     ↓
Press 'n' to deselect filtered items
     ↓
Press / then Esc to clear filter
     ↓
Press Enter to confirm
```

**Example**: Select everything except connectors
```
All selected                  Filter connectors             Connectors deselected
─────────────────────────────────────────────────────────────────────────────────
[X] Category                  [X] Box Connector             [X] Category
[X] Content                   [X] Confluence Connector      [X] Content
[X] Box Connector       →     [X] Database Connector   →    [ ] Box Connector
[X] Confluence Connector      [X] SharePoint Connector      [ ] Confluence Connector
[X] Database Connector                                      [ ] Database Connector
[X] SharePoint Connector                                    [ ] SharePoint Connector

    Press 'A'                     Search: "connector"           Press 'n'
                                  Shows only connectors         Deselects filtered items
```

## Keyboard Reference

### Navigation Keys

| Key | Action | Description |
|-----|--------|-------------|
| `↑` | Move up | Move cursor to previous item |
| `↓` | Move down | Move cursor to next item |
| `PgUp` | Page up | Jump up one screen |
| `PgDn` | Page down | Jump down one screen |
| `Home` | Go to top | Jump to first item |
| `End` | Go to bottom | Jump to last item |

### Selection Keys

| Key | Action | Description |
|-----|--------|-------------|
| `Space` | Toggle | Toggle selection on current item |
| `a` | Select filtered | Select all currently visible (filtered) items |
| `n` | Deselect filtered | Deselect all currently visible (filtered) items |
| `A` | Select all | Select ALL items (ignoring filter) |
| `N` | Deselect all | Deselect ALL items (ignoring filter) |

### Search/Filter Keys

| Key | Action | Description |
|-----|--------|-------------|
| `/` | Enter search | Enter search mode to filter items |
| `Esc` | Clear filter | Clear current filter and return to normal mode |
| `Enter` | Apply/Confirm | In search: apply filter; In normal: confirm selection |

### Control Keys

| Key | Action | Description |
|-----|--------|-------------|
| `Enter` | Confirm | Start processing selected items |
| `q` | Quit | Exit without processing |

## Tips and Tricks

### Tip 1: Quick Select
```
/keyword → Enter → a → / → Esc → Enter
```
Filter, select all filtered, clear filter, confirm. Fast!

### Tip 2: Preview Selection
After selecting items, press `/` then immediately `Esc` to see:
- Total selected count
- All items with selection state
- No filter applied

### Tip 3: Category-Based Selection
Search by category to group related items:
- `/Text` - Text processing components
- `/Connectors` - All connectors
- `/Administration` - Admin tools

### Tip 4: Progressive Selection
Build complex selections incrementally:
1. `/category1` → `a` (select all in category 1)
2. `/category2` → `a` (add category 2)
3. `/unwanted` → `n` (remove unwanted items)
4. `/` → `Esc` → `Enter` (clear filter and confirm)

### Tip 5: Case-Insensitive Search
All searches are case-insensitive:
- `/connector` = `/Connector` = `/CONNECTOR`

### Tip 6: Partial Matching
Search matches anywhere in name or category:
- `/share` matches "SharePoint Connector"
- `/admin` matches "Administration Guide"

## Visual States

### Unselected Item
```
  [ ] Text: Content
```
- Regular text
- Empty checkbox

### Selected Item
```
  [X] Text: Content
```
- Regular text
- Checked checkbox

### Current Item (Cursor)
```
> [X] Text: Content
```
- Reverse video (highlighted)
- Cursor marker `>`

### Filtered Out
```
(Item is not displayed at all when filtered)
```

## Error Messages

### No Items Selected
```
┌─────────────────────────────────────────────────┐
│  ⚠ No items selected! Press 'a' to select all │
│     or 'q' to quit                             │
└─────────────────────────────────────────────────┘
```
**Action**: Select at least one item before pressing Enter.

### No Items After Filter
```
┌─────────────────────────────────────────────────┐
│  Selected: 0/45 | Showing: 0                   │
│  Filter: nonexistent                            │
│                                                 │
│  (No items match your filter)                  │
└─────────────────────────────────────────────────┘
```
**Action**: Modify search term or press Esc to clear filter.

## Troubleshooting

### Terminal Too Small
If terminal is too small, items may overlap. Resize terminal:
```bash
# Check current size
echo $COLUMNS x $LINES

# Minimum recommended: 80x24
# Recommended: 120x40
```

### Colors Not Showing
If using reverse video but no colors, your terminal may not support ANSI:
```bash
# Test terminal capabilities
echo -e "\033[7mReverse Video\033[0m"

# If blank, terminal may need configuration
```

### Keyboard Not Working
Some terminals may not support all keys. Try:
- Use `j`/`k` if ↑/↓ don't work (vi-style, if implemented)
- Use `Ctrl+U`/`Ctrl+D` for page up/down
- Check terminal emulator settings

## Examples

### Example 1: Select Three Specific Connectors

**Goal**: Select Box, SharePoint, and Database connectors

**Steps**:
```
1. Launch TUI
2. Press / and type "box"
3. Press Enter
4. Press Space to select Box Connector
5. Press / and type "sharepoint"
6. Press Enter
7. Press Space to select SharePoint Connector
8. Press / and type "database"
9. Press Enter
10. Press Space to select Database Connector
11. Press / then Esc to clear filter
12. Verify all three are selected [X]
13. Press Enter to confirm
```

### Example 2: Select Everything in "Text" Category

**Goal**: Select all text processing components

**Steps**:
```
1. Launch TUI
2. Press / and type "text"
3. Press Enter (only Text items visible)
4. Press 'a' to select all filtered
5. Press / then Esc to clear filter
6. Verify Text items are selected [X]
7. Press Enter to confirm
```

### Example 3: Select All Except Media Server

**Goal**: Select all documentation except Media Server

**Steps**:
```
1. Launch TUI
2. Press 'A' (Shift+A) to select all
3. Press / and type "media"
4. Press Enter (only Media Server visible)
5. Press 'n' to deselect filtered
6. Press / then Esc to clear filter
7. Verify Media Server is not selected [ ]
8. Press Enter to confirm
```

## Advanced Usage

### Combining Filters Mentally

Since only one filter is active at a time, combine mentally:

**Goal**: Select Database and File connectors

**Approach**:
1. `/database` → `a` (select database items)
2. `/file` → `a` (also select file items)
3. `/` → `Esc` (clear filter, see combined selection)

### Regex-Style Thinking

Think in terms of substring matching:
- `/server` matches "Content Server", "Media Server", "Answer Server"
- `/admin` matches "Administration", "Admin Guide", "Admin User Guide"
- Use specific terms to narrow results

### Bulk Operations

- `A` then `Enter` : Process everything (dangerous!)
- `A` then `/unwanted` → `n` : Process everything except unwanted
- `/category` → `a` : Process specific category

## Summary

The TUI provides a powerful, keyboard-driven interface for selecting documentation:

- **Visual feedback**: See selections in real-time
- **Fast filtering**: Find items instantly with `/`
- **Bulk operations**: Select/deselect many items at once
- **Flexible workflow**: Navigate, filter, select in any order

Master the basics (↑↓, Space, Enter) and gradually adopt advanced techniques (filtering, bulk selection) as needed.

For questions or issues, see [PIPELINE_README.md](PIPELINE_README.md) or [EXAMPLES.md](EXAMPLES.md).


