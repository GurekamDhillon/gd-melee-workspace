#!/bin/bash
# guest entry: run /work/job.sh (chrooted Ubuntu rootfs, kernel 6.12). Output to the serial log and /work/job.out
echo "GUEST $(uname -r) THP=$(cat /sys/kernel/mm/transparent_hugepage/enabled)"
bash /work/job.sh > /work/job.out 2>&1
echo "GUEST job rc=$?"
