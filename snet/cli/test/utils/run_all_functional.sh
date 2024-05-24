for f in snet/cli/test/functional_tests/*.sh
do
   bash -ex ./snet/cli/test/utils/reset_environment.sh --i-no-what-i-am-doing
   bash -ex -c "cd snet/cli/test/functional_tests; bash -ex `basename $f`"
done
