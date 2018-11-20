if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

for f in test/functional_tests/*.sh
do
   bash -ex test/utils/reset_environment.sh
   bash -ex -c "cd test/functional_tests; bash -ex `basename $f`"
done
