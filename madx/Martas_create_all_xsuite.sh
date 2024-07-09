#!/bin/bash

if ! python -c 'import xtrack' 2> /dev/null
then
  echo "Xsuite environment not found. Did you activate the correct environment?"
  exit 1
fi


function DoCreateXsuite {
  year=$1
  bp=$2
  tempdir=temp_${year}_${bp/\//_}
  tempdir=${tempdir/\//_}
  tempdir=${tempdir/\//_}
  tempdir=${tempdir/\//_}
  mkdir $tempdir

  echo "created tempdir $tempdir"

  for beam in 1 2
  do
    f=$( ls ${bp}Martas_track_levelling.20_b${beam}.madx )
    fjson=${f%.madx}.json

    echo "fjson $fjson"

    g=$(basename $fjson)
    fout=${year}/xsuite/${g/track_/}
    echo fout $fout
    if [ ! -f $fout ]
    then
      cd $tempdir || (echo "Failed creating "$tempdir ; exit 1)
      ../Martas_madx_to_xsuite_sequence.py ../$f $beam 2>&1 > ../${fjson}.out
      mv ../${fjson} ../$fout 2> /dev/null && echo "Created "$fout || echo "Failed creating "$fout
      mv *.tfs ../$bp 2> /dev/null
      cd ..
    else
      echo "File "$fout" already exists. Skipping..."
    fi
  done
  rm -r $tempdir
  kinit -R
  aklog
}


for year in 2023
do
  for bp in ${year}/
  do
    echo "we are in the loop $year $bp"
    DoCreateXsuite $year $bp
  done
done
