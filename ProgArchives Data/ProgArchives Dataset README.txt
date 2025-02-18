# ProgArchives Dataset README

Currently this dataset made up of HTML files contains a list of 250 albums from each respective subgenre, however this dataset is incomplete.
To use this data, we will need to develop an automated method of extracting all the data we need from the files.
To complete this data, we will need to develop a data scraping tool for https://www.progarchives.com/

There are two possible methods of completing this dataset:
1. Using the search feature to find all albums of each subgenre by restricting search fields (such as county) until the list is < 250 albums, at which point the complement of the search would provide a complete list.
https://www.progarchives.com/top-prog-albums.asp?
However, this cannot find albums that do not have any reviews, due to limitations of the search,

Therefore, it may be wiser to consider:
2. By using the list of all artists, it is possible to open the artist page for each, and collect data that way, but this will lead to a much larger amount of html files.
https://www.progarchives.com/bands-alpha.asp?letter=*


For our purposes, we only care about the following
recording type: Studio & Singles/EPs/Fan Club/Promo
Title
Artist
Genre
Record Type, Year	Ratings

It is also worth considering having individual artist names and instrumentation, as it is common within Progarchives to list them on the album page, however this will greatly increase our HTML download/extraction demand as we will need to reach each individual album. Depending on our output, it may be worthwhile to combine both strategies 1 & 2 for a comprehensive result.

ProgArchives does not have a genre tag system, so we will have to use their subgenre system as a complement to our existing tag system. This will be somewhat aided by the descriptions of the subgenres, which can be found in this directory. Their subgenre must be treated as a separate "parent" tag that can also have similarity relations with our other genre tags.
There is very likely to be significant overlap between ProgArchives album data and our Progressive Rock/Metal CSVs, this must be accounted for.
