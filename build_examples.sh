#!/bin/bash

for file in examples/*.tsv
do
  ./multigloss.py "$file" "${file/.tsv/.html}"
done
