# Generate Activities from iCal Feed

This script automatically updates the Activities page with schedules from the Groups.io calendar feed using a **sliding window** that shows current and upcoming events.

## How It Works

1. **Fetches** the public iCal feed from Groups.io (no authentication needed!)
2. **Uses sliding window** - Shows events from the beginning of current month through end of next year
3. **Expands** recurring events into individual instances
4. **Filters** out regular nets and cancelled events
5. **Categorizes** events (meetings, field days, VE sessions, etc.)
6. **Updates** `content/200-activities.md` between comment markers

### Sliding Window Behavior

The script automatically adjusts what events to show based on the current date:

**December 2025** → Shows: December 2025 + all of 2026
**January 2026** → Shows: January 2026 + all of 2027
**July 2026** → Shows: July-December 2026 + all of 2027

This ensures:
- ✅ Events later in the current month are still visible
- ✅ Past events are automatically hidden
- ✅ Always shows ~13-18 months of upcoming events
- ✅ No manual intervention needed as months/years change

## Usage

### Basic - Update with Sliding Window

```bash
cd tools
python generate_from_ics.py
```

This automatically:
- Starts from the beginning of the current month
- Extends through the end of next year
- Generates dynamic year headers (e.g., `## 2025 Schedule`, `## 2026 Schedule`)
- Updates `content/200-activities.md` between `<!-- GENERATED-START/END -->`

**Examples:**
- Run in December 2025 → Shows Dec 2025 + all 2026
- Run in January 2026 → Shows Jan-Dec 2026 + all 2027
- Run in July 2026 → Shows Jul-Dec 2026 + all 2027

### Dry Run - Preview Changes

```bash
python generate_from_ics.py --dry-run
```

Shows what would be generated without modifying any files.

### Custom Years

```bash
python generate_from_ics.py --current-year 2025 --next-year 2026
```

### Custom File or URL

```bash
python generate_from_ics.py \
  --ical-url "https://groups.io/g/bcars/ics/.../feed.ics" \
  --activities-file "content/200-activities.md"
```

## How to Set Up Activities.md

The markdown file needs a single set of comment markers to indicate where schedules should be inserted:

```markdown
## Regular Activities

- Daily High Noon Round table net at 12:00PM on 145.490-, PL123
- Tuesday Evening ARES net at 8PM, 145.490-, PL 123

<!-- GENERATED-START -->

(both current year and next year schedules will be inserted here)

<!-- GENERATED-END -->
```

The script will:
1. Detect the current year (e.g., 2025)
2. Generate schedules for current year AND next year (2025 + 2026)
3. Include the `## 2025 Schedule` and `## 2026 Schedule` headers automatically
4. Replace everything between the START/END markers

**No year hardcoding needed!** The script automatically determines current and next year.

### Why Sliding Window?

The sliding window approach provides several benefits:

1. **Always Relevant**: Shows only upcoming events (current month onwards)
2. **Auto-Cleanup**: Past events disappear automatically
3. **Consistent Coverage**: Always shows 13-18 months of events
4. **Zero Maintenance**: Works year after year without updates

| Run Date | Date Range Shown | Result |
|----------|------------------|--------|
| Dec 20, 2025 | Dec 2025 - Dec 2026 | Shows end-of-year meeting + all 2026 events |
| Jan 5, 2026 | Jan 2026 - Dec 2027 | Automatically shows 2026 + 2027, drops 2025 |
| Jul 15, 2026 | Jul 2026 - Dec 2027 | Mid-year, shows rest of 2026 + all 2027 |

## Event Categorization

Events are automatically categorized and formatted based on their names:

- **Member Meetings**: `bcars member meeting` → No location shown
- **Field Day**: `field day` → Bolded with location
- **VE/Workshop**: `ve`, `workshop` → Special format with times
- **Holiday Dinner**: `dinner`, `holiday meeting` → Full location shown
- **Picnic**: `picnic` → With location
- **SET Exercise**: `set exercise` → Bolded
- **Nets**: Automatically filtered out (ARES, RACES, High Noon)

## Features

✅ **No Authentication** - Uses public iCal feed
✅ **Recurring Events** - Automatically expands recurring events
✅ **Multi-day Events** - Displays date ranges (e.g., "June 28-30")
✅ **Timezone Aware** - Converts times to Eastern (America/New_York)
✅ **Smart Filtering** - Excludes weekly nets and cancelled events
✅ **Conditional Formatting** - Shows/hides location based on event type

## Comparison with API Tools

| Feature | `generate_from_ics.py` | `generate_activities.py` (API) |
|---------|------------------------|--------------------------------|
| Authentication | ❌ Not needed | ✅ Required (API key) |
| Recurring Events | ✅ Auto-expanded | ❌ Manual handling |
| Public Access | ✅ Yes | ❌ No |
| Event Editing | ❌ No | ✅ Yes (with other tools) |
| Speed | 🚀 Fast | ⚡ Fast |

**Recommendation**: Use `generate_from_ics.py` for generating schedules. Use the API tools (`add-event`, `update-event`, etc.) for managing events.

## Example Output

```markdown
## 2025 Schedule

- January 25 **[Winter Field Day 2025](/fieldday/)** – 441 State Park Rd, Schellsburg, PA 15559
- February 22 **[VE Session @9:30AM](/license/) and [Technician Workshop @ 11AM](/workshops/)**
- June 5 [BCARS Members Meeting @ 7:30PM](/meetings/)
- June 28-30 **[ARES Summer Field Day 2025](/fieldday/)**
- August 23-24 **BCARS Members Picnic**, 193 Flying Dutchman Rd, Bedford, PA 15522
- December 4 [BCARS Members Meeting @ 7:30PM](/meetings/)
```

## Automation

You can run this script:
- Manually when you update the calendar
- Via cron job to auto-update daily/weekly
- As part of your Hugo build process

### Example Cron

```bash
# Update activities page daily at 6am
0 6 * * * cd /path/to/bcars/tools && python generate_from_ics.py
```

## Dependencies

- `icalendar` - iCal file parsing
- `recurring-ical-events` - Expanding recurring events
- `requests` - HTTP requests
- `click` - CLI interface

Installed automatically via `uv pip install -e .` in the tools directory.

