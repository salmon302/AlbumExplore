# ProgArchives Dataset README

Currently this dataset made up of HTML files contains a list of 250 albums from each respective subgenre, however this dataset is incomplete.
To use this data, we will need to develop an automated method of extracting all the data we need from the files.
To complete this data, we will need to develop an ETHICAL (with considerate rate limiting) data scraping tool for https://www.progarchives.com/

For our purposes, we only care about the following
recording type: Studio & Singles/EPs/Fan Club/Promo
Title
Artist
Genre
Record Type, Year, Ratings

More data we can obtain is:
individual artist names and instrumentation, as it is common within Progarchives to list them on the album page, however this will greatly increase our HTML download/extraction demand as we will need to reach each individual album. Depending on our output, it may be worthwhile to combine both strategies 1 & 2 for a comprehensive result.
Reviews by progarchives members
Descriptions of artists/bands

ProgArchives does not have a genre tag system, so we will have to use their subgenre system as a complement to our existing tag system. This will be somewhat aided by the descriptions of the subgenres, which can be found in this directory. Their subgenre must be treated as a separate "parent" tag that can also have similarity relations with our other genre tags.
There is very likely to be significant overlap between ProgArchives album data and our Progressive Rock/Metal CSVs, this must be accounted for.
