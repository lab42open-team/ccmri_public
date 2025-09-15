#!/bin/csh
#!/usr/bin/perl


echo 'Now the studyid pmid file will be sorted in respect to publication frequency per study'

sort /_full_path_in_your_server_to_/studyid_pmid.tsv | cut -f2 | uniq -c | sort -nr


echo 'And now lines are sorted with their corresponding URL'

sort /_full_path_in_your_server_to_/studyid_pmid.tsv | uniq | cut -f2 | perl -pe 's/^/https:\/\/www.ebi.ac.uk\/metagenomics\/publications\//' | sort | uniq -c | sort -nr > /_full_path_in_your_server_to_/studyid_pmid_sorted.tsv


perl -e 'print "Still testing...";'

perl -i -pe '~ s/^\s+//; s/ /\t/g;' /_full_path_in_your_server_to_/studyid_pmid_sorted.tsv



echo 'script terminated'
