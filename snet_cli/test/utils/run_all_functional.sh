for f in snet_cli/test/functional_tests/*.sh
do
   bash -ex snet_cli/test/utils/reset_environment.sh --i-no-what-i-am-doing
   bash -ex -c "cd snet_cli/test/functional_tests; bash -ex `basename $f`"
done
