for f in test/unit_tests/*.py
do
   bash -ex -c "cd test/unit_tests; python `basename $f`"
done
