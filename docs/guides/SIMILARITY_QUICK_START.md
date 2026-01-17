# 🔗 Album Similarity Feature - Quick Start

## Overview
The Album Similarity feature helps you discover albums similar to ones you like, based on shared tags, genre, year, and country. It uses a multi-factor scoring system to find the most relevant matches.

## How to Access

### Method 1: Right-Click Context Menu (Recommended)
1. Open Album Explorer and load your data (File > Load Data)
2. In the **Table View**, browse your albums
3. **Right-click** on any album row
4. Select **"Show Similar Albums"**
5. The Similarity View opens with that album as the focus

### Method 2: Menu Bar
1. Select an album in Table View (single click to highlight)
2. Go to **View > Similarity View** in the menu
3. The similarity view will show albums similar to your selection

## Using the Similarity View

### Controls
- **Show top**: Choose how many results to display (10, 20, 50, or 100)
- **Min similarity**: Adjust the threshold slider to filter results
  - 0.30 = Show loosely related albums
  - 0.50 = Show moderately similar albums
  - 0.70+ = Show only very similar albums

### Reading Results
Each result shows:
- **Album name** and artist
- **Visual similarity bar** (█████) - length indicates strength
- **Similarity score** (0.000 to 1.000)
- **Color coding**:
  - 🟢 Green (>0.8) = Highly similar
  - 🟡 Yellow (0.6-0.8) = Moderately similar
  - ⚪ Gray (<0.6) = Somewhat similar

### Tooltips
Hover over any result to see detailed breakdown:
- Number of shared tags
- List of shared tag names
- Genre match (✓ if same)
- Year and time difference
- Country match (✓ if same)

### Navigation
- **Double-click** any result to explore that album's similarities
- This lets you "hop" through the collection discovering related albums

## Similarity Scoring

The system calculates similarity using multiple factors:

1. **Composite Tags** (40% weight)
   - Looks at all tags assigned to the album
   - Uses Jaccard similarity (shared tags / total unique tags)

2. **Atomic Tags** (30% weight)
   - More granular tag components
   - Provides finer similarity matching

3. **Genre** (15% weight)
   - Exact match = full score
   - Different genre = no score

4. **Year Proximity** (10% weight)
   - Albums within 5 years = full score
   - Decays linearly to 0 at 20 years apart

5. **Country** (5% weight)
   - Same country = full score
   - Different country = no score

## Tips for Best Results

### Finding Close Matches
- Set threshold to **0.60 or higher**
- Use **top 20** to see quality over quantity
- Look for green-colored results

### Discovering New Albums
- Lower threshold to **0.30-0.40**
- Increase to **top 50 or 100**
- Explore yellow and gray results

### Genre-Specific Searches
- Similarity automatically prioritizes same-genre albums
- Use a progressive rock album to find more prog rock

### Era-Specific Searches
- Albums from similar years get higher scores
- Great for finding contemporaries

## Performance

- **Fast**: Results typically appear in under 200ms
- **Scalable**: Works efficiently with 17,000+ albums
- **Smart**: Only compares albums with at least one shared tag

## Examples

### Example 1: Classic Prog Rock
Starting with: **Pink Floyd - The Dark Side of the Moon**

You might find:
- Genesis - Selling England by the Pound (0.87)
- Yes - Close to the Edge (0.84)
- King Crimson - Red (0.82)

### Example 2: Jazz Fusion
Starting with: **Mahavishnu Orchestra - Birds of Fire**

You might find:
- Return to Forever - Romantic Warrior (0.81)
- Weather Report - Heavy Weather (0.78)
- Brand X - Unorthodox Behaviour (0.74)

## Troubleshooting

### "No similar albums found"
- **Lower the threshold** - Try 0.20 or 0.30
- **Check the album has tags** - Albums need tags to find matches
- **Load more data** - More albums = more potential matches

### Results seem off
- **Check tooltip** - See why the album matched
- **Adjust threshold** - Higher = stricter matches
- **Different starting album** - Some albums are more unique

### View is empty
- **Select an album first** - Use table view to pick one
- **Use right-click menu** - Easiest way to get started
- **Check data is loaded** - Need albums in the database

## Advanced Usage

### Exploring Similarity Networks
1. Start with a known album
2. Double-click the top result
3. Repeat to "walk" through similar albums
4. Discover albums you've never heard of!

### Finding Genre Boundaries
- Start with a genre-defining album
- Lower the threshold to 0.30
- See how the algorithm bridges styles

### Building Playlists
- Find similar albums to one you love
- Note the top 10-20 results
- Create a listening queue of similar albums

## Future Enhancements

Coming soon:
- Back/forward navigation history
- Grid view with album artwork
- Export similar albums to CSV
- Adjustable similarity weights
- "Anti-similar" albums (find opposites)

---

**Need Help?** Check the full design document: `ALBUM_SIMILARITY_VISUALIZATION.md`

**Implementation Details**: See `SIMILARITY_IMPLEMENTATION_COMPLETE.md`

**Have Feedback?** We'd love to hear how you use this feature!
