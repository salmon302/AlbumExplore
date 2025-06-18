# ProgArchives Data Acquisition and Integration Plan

This document outlines the plan to acquire data from downloaded ProgArchives HTML files and integrate it with an existing album database.

## Phase 1: Understanding the Data and Structure (Completed)

**Objective:** Analyze the downloaded files to understand their structure and locate all necessary data points as per `ProgArchives Data/ProgArchives Dataset README.txt`.

**Key Findings & File Locations:**
*   **Album Data:**
    *   **Files:** `ProgArchives Data/Website/ProgArchives/www.progarchives.com/albumXXXX.html`
    *   **Key Info Source:** `<meta name="description">` tag (Album Title, Artist, Year, Recording Type, Subgenre(s)). Confirmed by `<h1>`, `<h2>` tags.
    *   **Other Info:**
        *   Cover Image URL: `<meta property="og:image">`
        *   Tracklist, Line-up/Musicians, Release Info: Main body of HTML.
        *   Ratings (Overall & Individual Reviews): Main body, potentially with a link to `album-reviewsXXXX.html` for all reviews.
        *   Artist Page Link: Within album page, e.g., `artistYYYY.html?id=ZZZ`.
*   **Artist Data:**
    *   **Files:** `ProgArchives Data/Website/ProgArchives/www.progarchives.com/artistYYYY.html`
    *   **Key Info Source:** `<meta name="description">` tag (Artist Name, Genre, Country). Confirmed in page body.
    *   **Other Info:**
        *   Artist Biography: Main body (e.g., `div id="artist-biography"`), potentially expandable (check `span id="shortBio"` and `span id="moreBio"`).
        *   Official Website Link: Present on artist page.
*   **Subgenre Definitions:**
    *   **File:** `ProgArchives Data/ProgSubgenres` (text file)
    *   **Content:** Contains names and detailed text definitions for each ProgArchives subgenre.
*   **Other Subgenre Files:** Files like `ProgArchives Data/Canterbury Scene.html` are top album lists for those subgenres, not the definitions themselves.
*   **README File:** `ProgArchives Data/ProgArchives Dataset README.txt` (initial requirements).

**Status:** All data points required by the README have been successfully located.

## Phase 2: Data Extraction

**Objective:** Systematically parse all relevant HTML and text files to extract the raw data.

**Process:**
1.  **Identify Album Files:** Scan `ProgArchives Data/Website/ProgArchives/www.progarchives.com/` for all `albumXXXX.html` files.
2.  **Parse Each Album File:**
    *   Extract metadata (Artist, Album Title, Year, Raw Recording Type, Raw Subgenre(s) string, Cover Image URL) from `<meta>` tags.
    *   Parse main body for Tracklist (including durations, sub-tracks, total time, bonus tracks), Line-up/Musicians (members, instruments, guests), Ratings (average, counts), and individual Reviews (reviewer, rating, text, date).
    *   Handle links to "Show all reviews/ratings" (e.g., `album-reviewsXXXX.html`) by potentially queuing these pages for parsing if they contain additional reviews.
    *   Extract and store the relative link to the artist's page.
3.  **Process Artist Information:**
    *   Compile a unique list of artist page URLs from album data.
    *   For each unique `artistYYYY.html` file:
        *   Extract metadata (Artist Name, Genre, Country).
        *   Parse and extract the full artist biography (handling "read more" functionality).
        *   Extract official website URL.
4.  **Process Subgenre Definitions:**
    *   Parse `ProgArchives Data/ProgSubgenres` file.
    *   For each subgenre, extract its Name and full Definition text.
5.  **Initial Data Storage:** Store all extracted raw data in a structured intermediate format (e.g., JSON files or multiple CSVs: one for albums, one for artists, one for subgenre definitions).

## Phase 3: Data Cleaning and Transformation (Completed)

**Objective:** Clean the raw extracted data and transform it into a consistent, usable format ready for database loading.

**Process:**
1.  **Clean Extracted Data:**
    *   Remove any residual HTML tags or entities from text fields.
    *   Normalize text: Trim whitespace, ensure consistent capitalization for key fields, handle special characters/encoding issues.
    *   Convert data types: Years to integers, ratings to floats, track durations to a numerical format (e.g., seconds).
2.  **Transform Data for Database Schema:**
    *   Map extracted field names to the target database column names.
    *   **Recording Type Standardization:** Convert raw recording type strings (e.g., "studio album") to standardized values as per README (e.g., "Studio", "Singles/EPs/Fan Club/Promo"). Define handling for other types.
    *   **ProgArchives Subgenre Integration:** Prepare subgenre names and their definitions for storage, ensuring they can be linked as "parent tags" to albums.
    *   **Line-up/Musicians:** Structure into a list of entries per album, each with musician name and a list of their instruments/roles.
    *   **Reviews:** Ensure each review is linked to its album and includes reviewer name, their given rating, full review text, and posting date.

**Implementation:**
* Created a comprehensive data transformation module (`transform_progarchives_data.py`) that:
  * Reads the raw CSV files from Phase 2
  * Performs all cleaning and normalization tasks
  * Converts data types appropriately (years to int, ratings to float, durations to seconds)
  * Maps ProgArchives recording types to standardized values
  * Processes artist data and creates proper Artist entities
  * Stores formatted lineup information in the Album model
  * Creates a dedicated TagCategory for ProgArchives genres
  * Processes all tracks and reviews with proper album associations
* Added VS Code tasks for easy execution of the transformation process
* Implemented logging, error handling, and transaction support
* Supports dry-run mode for testing without modifying the database

## Phase 4: Data Staging and Database Structure

**Objective:** Load the cleaned and transformed data into a well-defined database structure that accommodates the different lifecycles of the data sources (ProgArchives, historical CSVs, current year's CSV).

**Process:**
1.  **ProgArchives Dataset Storage:**
    *   Load all cleaned and transformed data from ProgArchives into a dedicated set of tables within the main database system (e.g., `pa_Albums`, `pa_Artists`, `pa_Tracks`, `pa_Lineups`, `pa_Reviews`, `pa_Subgenres`).
    *   This dataset is considered static after the initial load.
2.  **Historical Subreddit Dataset Storage:**
    *   Load all existing subreddit-organized CSVs (EXCEPT for the current year's CSV, e.g., 2025) into another set of tables (e.g., `hist_subreddit_Albums`, `hist_subreddit_Tracks`).
    *   This dataset is also considered relatively static.
3.  **Current Year Subreddit Data Handling:**
    *   The current year's CSV (e.g., 2025) will be loaded into its own dedicated table(s) (e.g., `current_year_subreddit_Albums`).
    *   This data will be replaced entirely when the CSV is updated.
4.  **Linking and Deduplication Strategy (Focus on Manual Review):**
    *   **Initial Linking:** After loading both the ProgArchives Dataset and the Historical Subreddit Dataset, perform a deduplication/linking process primarily between `pa_Albums` and `hist_subreddit_Albums`.
    *   **Matching Criteria:** Use Artist Name, Album Title, and Year (with normalization and potentially fuzzy matching).
    *   **Flagging for Manual Review:**
        *   If a potential match is found, create a link/reference in a mapping table (e.g., `Album_Link_Review_Flags`) and flag the pair of records for manual review.
        *   This table should store the IDs of the potentially matched albums from both datasets and the status of the review (e.g., pending, reviewed_linked, reviewed_not_duplicate).
        *   The manual review will determine true duplicates and the preferred data representation.
    *   **No Direct Merge with Dynamic Data:** Avoid direct merging of the static ProgArchives data with the dynamic current year's subreddit data tables.
5.  **Querying and Presentation Layer:**
    *   The application or system used to query and view the data will be responsible for accessing all three datasets (ProgArchives, Historical Subreddit, Current Year Subreddit).
    *   It will use the information from the `Album_Link_Review_Flags` table (and subsequent manual review decisions) to present a unified or comparative view of albums found in multiple sources.

This plan aims for a robust data pipeline, ensuring data integrity, clear provenance, and flexibility in handling updates and data consolidation. 