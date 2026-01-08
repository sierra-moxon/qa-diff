#!/bin/bash

# Generate infores edge reports for all specified sources
# Usage: ./generate_all_infores_reports.sh <dev_csv> <ci_csv>

set -e

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <dev_csv> <ci_csv>"
    echo "Example: $0 'dev_refactor_tests_ 2026_01_07_05_00.csv' 'sprint_6_tests_ 2026_01_04_05_00.csv'"
    exit 1
fi

DEV_CSV="$1"
CI_CSV="$2"

INFORES_LIST=(
    "infores:agrkb"
    "infores:bgee"
    "infores:bindingdb"
    "infores:chembl"
    "infores:cohd"
    "infores:ctd"
    "infores:dgidb"
    "infores:diseases"
    "infores:drug-repurposing-hub"
    "infores:ebi-gene2phenotype"
    "infores:genetics-data-provider"
    "infores:go-cam"
    "infores:goa"
    "infores:gtopdb"
    "infores:hpo-annotations"
    "infores:icees-kg"
    "infores:intact"
    "infores:multiomics-clinicaltrials"
    "infores:multiomics-drugapprovals"
    "infores:ncbi-gene"
    "infores:panther"
    "infores:pathbank"
    "infores:semmeddb"
    "infores:sider"
    "infores:text-mining-provider-targeted"
    "infores:ttd"
    "infores:ubergraph"
)

echo "Generating infores reports for ${#INFORES_LIST[@]} sources..."
echo ""

for infores in "${INFORES_LIST[@]}"; do
    echo "Processing $infores..."
    make infores DEV="$DEV_CSV" CI="$CI_CSV" FILTER="$infores"
    echo ""
done

echo "Combining all TSV reports into single file..."
cd test_diffs

head -1 infores_edges_only_in_ci_detailed_infores_ctd.tsv > all_infores_edges_only_in_ci.tsv

for file in infores_edges_only_in_ci_detailed_*.tsv; do
    tail -n +2 "$file" >> all_infores_edges_only_in_ci.tsv
done

cd ..

echo ""
echo "Complete!"
echo "Individual reports: test_diffs/infores_edges_only_in_ci_detailed_*.tsv"
echo "Combined report: test_diffs/all_infores_edges_only_in_ci.tsv"
echo ""
wc -l test_diffs/all_infores_edges_only_in_ci.tsv
ls -lh test_diffs/all_infores_edges_only_in_ci.tsv
