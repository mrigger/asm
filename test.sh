RET_VAL=`./grep.sh grep-tests/ | wc -l`
EXPECTED_MATCHES=9
if [ ${RET_VAL} != ${EXPECTED_MATCHES} ];
then
    echo ${RET_VAL} is an unexpected return value
    exit -1
fi
