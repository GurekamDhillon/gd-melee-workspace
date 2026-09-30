SECTIONS {
  gwfix : ALIGN(4) {
    __start_gwfix = .;
    KEEP(*(gwfix))
    __stop_gwfix = .;
  }
}
INSERT AFTER .data;
