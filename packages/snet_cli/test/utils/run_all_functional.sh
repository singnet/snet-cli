for f in packages/snet_cli/test/functional_tests/*.sh
do
   bash -ex packages/snet_cli/test/utils/reset_environment.sh --i-no-what-i-am-doing
   bash -ex -c "cd packages/snet_cli/test/functional_tests; bash -ex `basename $f`"
done
