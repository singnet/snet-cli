for f in test/functional_tests/*.sh
do
   bash -ex test/utils/reset_environment.sh --i-no-what-i-am-doing
   bash -ex -c "cd test/functional_tests; bash -ex `basename $f`"
done
