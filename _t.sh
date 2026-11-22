export PATH=$HOME/.cargo/bin:$PATH
B=$HOME/melee-target/release/melee
ls -la $B; ldd $B | head -20
$B version; echo rc=$?
cd /tmp; rm -rf crashlogs
$B crash-test panic; echo rc=$?; ls crashlogs; head -12 crashlogs/*
rm -rf crashlogs; $B crash-test fault; echo rc=$?; ls crashlogs; head -12 crashlogs/* 
